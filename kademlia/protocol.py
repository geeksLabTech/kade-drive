import random
import asyncio
import logging

from rpcudp.protocol import RPCProtocol

from kademlia.node import Node
from kademlia.routing import RoutingTable
from kademlia.storage import IStorage
from kademlia.utils import digest

log = logging.getLogger(__name__)  # pylint: disable=invalid-name


class KademliaProtocol(RPCProtocol):
    def __init__(self, source_node: Node, storage: IStorage, ksize: int):
        """Instantiation class for the Protocol

        Args:
            source_node (Node): root node 
            storage (IStorage): values in node
            ksize (int): k-bucket size (nodes to keep as 'close')
        """
        RPCProtocol.__init__(self)
        self.router = RoutingTable(self, ksize, source_node)
        self.storage = storage
        self.source_node = source_node

    def get_refresh_ids(self):
        """
        Get ids to search for to keep old buckets up to date.
        """
        ids: list[bytes] = []
        for bucket in self.router.lonely_buckets():
            rid = random.randint(*bucket.range).to_bytes(20, byteorder='big')
            ids.append(rid)
        return ids

    def rpc_stun(self, sender):  # pylint: disable=no-self-use
        return sender

    def rpc_ping(self, sender, nodeid: bytes):
        """Porbe a Node to see if pc is online

        Args:
            sender : sender node
            nodeid (bytes): node to be probed

        Returns:
            bytes: node id if alive, None if not 
        """
        source = Node(nodeid, sender[0], sender[1])
        # if a new node is sending the request, give all data it should contain
        self.welcome_if_new(source)

        return self.source_node.id

    def rpc_store(self, sender, nodeid: bytes, key: bytes, value):
        """Instructs a node to store a value

        Args:
            sender : Sender Node  
            nodeid (bytes): Node to be told to store info
            key (bytes): key to the value to store
            value : value to store

        Returns:
            bool: True if operation successful
        """
        source = Node(nodeid, sender[0], sender[1])
        # if a new node is sending the request, give all data it should contain
        self.welcome_if_new(source)

        log.debug("got a store request from %s, storing '%s'='%s'",
                  sender, key.hex(), value)
        # store values and report success
        self.storage[key] = value
        return True

    def rpc_find_node(self, sender, nodeid: bytes, key: bytes):
        log.info("finding neighbors of %i in local table",
                 int(nodeid.hex(), 16))

        source = Node(nodeid, sender[0], sender[1])
        # if a new node is sending the request, give all data it should contain
        self.welcome_if_new(source)
        # create a fictional node to perform the search
        node = Node(key)
        # ask for the neighbors of the node
        neighbors = self.router.find_neighbors(node, exclude=source)
        return list(map(tuple, neighbors))

    def rpc_find_value(self, sender, nodeid: bytes, key: bytes):

        source = Node(nodeid, sender[0], sender[1])
        # if a new node is sending the request, give all data it should contain
        self.welcome_if_new(source)
        # get value from storage
        value = self.storage.get(key, None)
        # if not value found, ask the info for the value to the nodes
        if value is None:
            return self.rpc_find_node(sender, nodeid, key)
        return {'value': value}

    async def call_find_node(self, node_to_ask: Node, node_to_find: Node):
        # async function to call the find node method previously described
        address = (node_to_ask.ip, node_to_ask.port)
        result = await self.find_node(address, self.source_node.id,
                                      node_to_find.id)
        return self.handle_call_response(result, node_to_ask)

    async def call_find_value(self, node_to_ask: Node, node_to_find: Node):
        # async function to call the find value method previously described
        address = (node_to_ask.ip, node_to_ask.port)
        result = await self.find_value(address, self.source_node.id,
                                       node_to_find.id)
        return self.handle_call_response(result, node_to_ask)

    async def call_ping(self, node_to_ask: Node):
        # async function to call the ping method previously described
        address = (node_to_ask.ip, node_to_ask.port)
        result = await self.ping(address, self.source_node.id)
        return self.handle_call_response(result, node_to_ask)

    async def call_store(self, node_to_ask: Node, key: bytes, value):
        # async function to call the find store method previously described

        address = (node_to_ask.ip, node_to_ask.port)
        result = await self.store(address, self.source_node.id, key, value)
        return self.handle_call_response(result, node_to_ask)

    def welcome_if_new(self, node: Node):
        """
        Given a new node, send it all the keys/values it should be storing,
        then add it to the routing table.

        @param node: A new node that just joined (or that we just found out
        about).

        Process:
        For each key in storage, get k closest nodes.  If newnode is closer
        than the furtherst in that list, and the node for this server
        is closer than the closest in that list, then store the key/value
        on the new node (per section 2.5 of the paper)
        """
        # if the node is in teh table, do nothing
        if not self.router.is_new_node(node):
            return

        log.info("never seen %s before, adding to router", node)
        # iterate over storage
        for key, value in self.storage:
            # creqate fictional node to calculate distance
            keynode = Node(digest(key))
            neighbors = self.router.find_neighbors(keynode)
            new_node_close = False
            this_closest = False
            # if the node is closer tan the furtherst neighbor
            # the values should be then stored in that node
            if neighbors:
                last = neighbors[-1].distance_to(keynode)
                new_node_close = node.distance_to(keynode) < last
                first = neighbors[0].distance_to(keynode)
                this_closest = self.source_node.distance_to(keynode) < first
            # if not neighbors, store data in the node
            if not neighbors or (new_node_close and this_closest):
                asyncio.ensure_future(self.call_store(node, key, value))
        # add node to table
        self.router.add_contact(node)

    def handle_call_response(self, result, node: Node):
        """
        If we get a response, add the node to the routing table.  If
        we get no response, make sure it's removed from the routing table.
        """
        if not result[0]:
            log.warning("no response from %s, removing from router", node)
            self.router.remove_contact(node)
            return result

        log.info("got successful response from %s", node)
        self.welcome_if_new(node)
        return result
