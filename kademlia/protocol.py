import random
import asyncio
import logging

from rpc.protocol import RPCUDPProtocol, RPCTCPProtocol
from rpc.utils import rpc_tcp, rpc_udp

from kademlia.node import Node
from kademlia.routing import RoutingTable
from kademlia.storage import IStorage
from kademlia.utils import digest

log = logging.getLogger(__name__)  # pylint: disable=invalid-name



class KademliaUDPProtocol(RPCUDPProtocol):
    def __init__(self, filesystem_protocol):
        """Instantiation class for the Protocol

        Args:
            source_node (Node): root node 
            storage (IStorage): values in node
            ksize (int): k-bucket size (nodes to keep as 'close')
        """
        RPCUDPProtocol.__init__(self)
        self.filesystem_protocol = filesystem_protocol

    @rpc_udp(1)
    def rpc_stun(self, sender):  # pylint: disable=no-self-use
        return sender

    @rpc_udp(1)
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
        self.filesystem_protocol.welcome_if_new(source)

        return self.filesystem_protocol.source_node.id


    @rpc_udp(1)
    def rpc_find_node(self, sender, nodeid: bytes, key: bytes):
        log.info("finding neighbors of %i in local table",
                 int(nodeid.hex(), 16))

        source = Node(nodeid, sender[0], sender[1])
        # if a new node is sending the request, give all data it should contain
        self.filesystem_protocol.welcome_if_new(source)
        # create a fictional node to perform the search
        node = Node(key)
        # ask for the neighbors of the node
        neighbors = self.filesystem_protocol.router.find_neighbors(node, exclude=source)
        return list(map(tuple, neighbors))
    

    
class KademliaTCPProtocol(RPCTCPProtocol):
    def __init__(self, filesystem_protocol):
        """Instantiation class for the Protocol

        Args:
            source_node (Node): root node 
            storage (IStorage): values in node
            ksize (int): k-bucket size (nodes to keep as 'close')
        """
        RPCTCPProtocol.__init__(self)
        self.filesystem_protocol = filesystem_protocol

    @rpc_tcp
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
        self.filesystem_protocol.welcome_if_new(source)

        log.debug("got a store request from %s, storing '%s'='%s'",
                  sender, key.hex(), value)
        # store values and report success
        self.filesystem_protocol.storage[key] = value
        return True

    @rpc_tcp
    def rpc_find_value(self, sender: tuple[str, str], nodeid: bytes, key: bytes):
        source = Node(nodeid, sender[0], sender[1])
        # if a new node is sending the request, give all data it should contain
        self.filesystem_protocol.welcome_if_new(source)
        # get value from storage
        value = self.filesystem_protocol.storage.get(key, None)
        return value
        # if not value found, ask the info for the value to the nodes
        # if value is None:
        #     return self.rpc_find_node(sender, nodeid, key)
        # return {'value': value}

class FileSystemProtocol:
    def __init__(self, source_node: Node, storage: IStorage, ksize: int) -> None:
        self.source_node = source_node
        self.ksize = ksize
        self.storage = storage
        self.router = RoutingTable(self, ksize, source_node)
        self.tcp_protocol: KademliaTCPProtocol|None = None
        self.udp_protocol: KademliaUDPProtocol|None = None

    def create_tcp_protocol(self):
        self.tcp_protocol = KademliaTCPProtocol(self)
        return self.tcp_protocol
    
    def create_udp_protocol(self):
        self.udp_protocol = KademliaUDPProtocol(self)
        return self.udp_protocol
    
    def close_trasports(self):
        if self.tcp_protocol and self.tcp_protocol.transport:
            self.tcp_protocol.transport.close()

        if self.udp_protocol and self.udp_protocol.transport:
            self.udp_protocol.transport.close()

    def get_refresh_ids(self):
        """
        Get ids to search for to keep old buckets up to date.
        """
        ids: list[bytes] = []
        for bucket in self.router.lonely_buckets():
            rid = random.randint(*bucket.range).to_bytes(20, byteorder='big')
            ids.append(rid)
        return ids

    async def call_find_node(self, node_to_ask: Node, node_to_find: Node):
        """
        async function to call the find node rpc method
        """
        address = (node_to_ask.ip, node_to_ask.port)
        result = await self.udp_protocol.rpc_find_node(address, self.source_node.id,
                                      node_to_find.id)
        return self.handle_call_response(result, node_to_ask)

    async def call_find_value(self, node_to_ask: Node, node_to_find: Node):
        """
        async function to call the find value rpc method 
        """
        address = (node_to_ask.ip, node_to_ask.port)
        result = await self.tcp_protocol.rpc_find_value(address, self.source_node.id,
                                       node_to_find.id)
        if result is None:
            result = await self.udp_protocol.rpc_find_node(address, self.source_node.id,
                                       node_to_find.id)
        return self.handle_call_response(result, node_to_ask)

    async def call_ping(self, node_to_ask: Node):
        """
        async function to call the ping rpc method
        """
        address = (node_to_ask.ip, node_to_ask.port)
        result = await self.udp_protocol.rpc_ping(address, self.source_node.id)
        return self.handle_call_response(result, node_to_ask)

    async def call_store(self, node_to_ask: Node, key: bytes, value):
        """
        async function to call the find store rpc method
        """
        address = (node_to_ask.ip, node_to_ask.port)
        result = await self.tcp_protocol.rpc_store(address, self.source_node.id, key, value)
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
        # if the node is in the table, do nothing
        if not self.router.is_new_node(node):
            return

        log.info("never seen %s before, adding to router", node)
        # iterate over storage
        for key, value in self.storage:
            # Create fictional node to calculate distance
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
    
