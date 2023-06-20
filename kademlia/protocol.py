import random
import logging
import rpyc

from kademlia.node import Node
# from kademlia.routing import RoutingTable
from kademlia.storage import PersistentStorage
from kademlia.utils import digest

log = logging.getLogger(__name__)  # pylint: disable=invalid-name


# class KademliaUDPProtocol(RPCUDPProtocol):
#     def __init__(self, filesystem_protocol):
#         """Instantiation class for the Protocol

#         Args:
#             source_node (Node): root node
#             storage (IStorage): values in node
#             ksize (int): k-bucket size (nodes to keep as 'close')
#         """
#         RPCUDPProtocol.__init__(self)
#         self.filesystem_protocol = filesystem_protocol


# class KademliaTCPProtocol(RPCTCPProtocol):
#     def __init__(self, filesystem_protocol):
#         """Instantiation class for the Protocol

#         Args:
#             source_node (Node): root node
#             storage (IStorage): values in node
#             ksize (int): k-bucket size (nodes to keep as 'close')
#         """
#         RPCTCPProtocol.__init__(self)
#         self.filesystem_protocol = filesystem_protocol


class FileSystemProtocol:
    source_node: Node
    ksize: int
    storage: PersistentStorage
    router: None = None
    last_response = None

    @staticmethod
    def init(routing_table, storage: PersistentStorage):
        FileSystemProtocol.source_node = routing_table.node
        FileSystemProtocol.ksize = routing_table.ksize
        FileSystemProtocol.storage = storage
        FileSystemProtocol.router = routing_table

    @staticmethod
    def get_refresh_ids():
        """
        Get ids to search for to keep old buckets up to date.
        """
        ids: list[bytes] = []
        for bucket in FileSystemProtocol.router.lonely_buckets():
            rid = random.randint(*bucket.range).to_bytes(20, byteorder='big')
            ids.append(rid)
        return ids

    @staticmethod
    def call_store(conn, node_to_ask: Node, key: bytes, value):
        """
        async function to call the find store rpc method
        """
        response = None
        address = (node_to_ask.ip, node_to_ask.port)
        response = None
        if conn:
            response = conn.rpc_store(
            address, FileSystemProtocol.source_node.id, key, value)

        return FileSystemProtocol.process_response(conn, response, node_to_ask)

    @staticmethod
    def call_find_node(conn, node_to_ask: Node, node_to_find: Node):
        """
        async function to call the find node rpc method
        """
        print("inside call find Node")
        response = None
        address = (node_to_ask.ip, node_to_ask.port)
        print(address)
        print(node_to_find.ip)
        response = None
        if conn:
            response = conn.rpc_find_node((FileSystemProtocol.source_node.ip, FileSystemProtocol.source_node.port), FileSystemProtocol.source_node.id,
                                      node_to_ask.id)
        
        return FileSystemProtocol.process_response(conn, response, node_to_ask)

    @staticmethod
    def call_find_value(conn, node_to_ask: Node, node_to_find: Node):
        """
        async function to call the find value rpc method 
        """
        response = None
        address = (node_to_ask.ip, node_to_ask.port)
        response = None
        if conn:
            response = conn.rpc_find_value(address, FileSystemProtocol.source_node.id,
                                       node_to_find.id)
        print(response)
        return FileSystemProtocol.process_response(conn, response, node_to_ask)

    @staticmethod
    def call_ping(conn, node_to_ask: Node):
        """
        async function to call the ping rpc method
        """
        response = None
        address = (node_to_ask.ip, node_to_ask.port)
        response = None
        if conn:
            response = conn.rpc_ping(
                address, FileSystemProtocol.source_node.id)

        print("Got Response {response}")

        return FileSystemProtocol.process_response(conn, response, node_to_ask)

    @staticmethod
    def welcome_if_new(conn, node: Node):
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
        if not FileSystemProtocol.router.is_new_node(node):
            return

        # add node to table
        print('Adding new node to contacts')
        FileSystemProtocol.router.add_contact(node)

        print("never seen %s before, adding to router", node)
        # iterate over storage
        for key, value in FileSystemProtocol.storage:
            print('entry for')
            # Create fictional node to calculate distance
            keynode = Node(digest(key))
            neighbors = FileSystemProtocol.router.find_neighbors(keynode)

            new_node_close = False
            this_closest = False
            # if the node is closer tan the furtherst neighbor
            # the values should be then stored in that node
            if len(neighbors) > 2:
                last = neighbors[-1].distance_to(keynode)
                new_node_close = node.distance_to(keynode) < last
                first = neighbors[0].distance_to(keynode)
                this_closest = FileSystemProtocol.source_node.distance_to(
                    keynode) < first
            # if not neighbors, store data in the node
            print(f'neighbors in for {neighbors}')
            if not neighbors or (new_node_close and this_closest) or len(neighbors) <= 1:
                print('calling call_store in welcome_if_new')
                with ServerSession(node.ip, node.port) as conn:
                    FileSystemProtocol.call_store(conn, node, key, value)

    @staticmethod
    def process_response(conn, response, node: Node):
        """
        If we get a response, add the node to the routing table.  If
        we get no response, make sure it's removed from the routing table.
        """
        print(response)
        if not response:
            print("no response from %s, removing from router", node)
            FileSystemProtocol.router.remove_contact(node)
            return response
        
        FileSystemProtocol.welcome_if_new(conn, node)
        print("got successful response from %s", node)
        print(response)
        return response


class ServerSession:
    """Server session context manager."""

    def __init__(self, server_ip: str, port: str):
        self.server_ip = server_ip
        self.port = port
        self.server_session: rpyc.Connection | None = None

    def __enter__(self):
        try:
            self.server_session = rpyc.connect(self.server_ip, port=self.port)
            return self.server_session.root
        except ConnectionRefusedError:
            return None

    def __exit__(self, exc_type, exc_value, traceback):
        if self.server_session is not None:
            self.server_session.close()
