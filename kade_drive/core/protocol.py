import random
import logging
import rpyc

from kade_drive.core.node import Node
from kade_drive.core.storage import logger, PersistentStorage
from kade_drive.core.utils import digest


# Create a file handler
# file_handler = logging.FileHandler("log_file.log")
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
# file_handler.setFormatter(formatter)
logger = logging.getLogger(__name__)
# logger.addHandler(file_handler)


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
            rid = random.randint(*bucket.range).to_bytes(20, byteorder="big")
            ids.append(rid)
        return ids

    @staticmethod
    def call_store(conn, node_to_ask: Node, key: bytes, value, is_metadata=True):
        """
        async function to call the find store rpc method
        """
        response = None
        address = (node_to_ask.ip, node_to_ask.port)
        response = None
        if conn:
            response = conn.rpc_store(
                address, FileSystemProtocol.source_node.id, key, value, is_metadata
            )

        return FileSystemProtocol.process_response(conn, response, node_to_ask)

    @staticmethod
    def call_contains(conn, node_to_ask, key: bytes, is_metadata=True):
        response = None
        if conn:
            address = (node_to_ask.ip, node_to_ask.port)
            response = conn.rpc_contains(
                address, FileSystemProtocol.source_node.id, key, is_metadata
            )

        return FileSystemProtocol.process_response(conn, response, node_to_ask)

    @staticmethod
    def call_check_if_new_value_exists(conn, node_to_ask, key: bytes, is_metadata=True):
        response = None
        if conn:
            address = (node_to_ask.ip, node_to_ask.port)
            response = conn.rpc_check_if_new_value_exists(
                address, FileSystemProtocol.source_node.id, key)

        return FileSystemProtocol.process_response(conn, response, node_to_ask)

    @staticmethod
    def call_find_node(conn, node_to_ask: Node, node_to_find: Node):
        """
        async function to call the find node rpc method
        """

        logger.debug("inside call find Node")
        response = None
        address = (node_to_ask.ip, node_to_ask.port)
        logger.debug("address" + str(address))
        logger.debug("Node to find" + str(node_to_find.ip))

        logger.debug(
            f"Now conn is {conn is not None} and node {node_to_find is not None}"
        )
        response = None
        if conn:
            response = conn.rpc_find_node(
                address, FileSystemProtocol.source_node.id, node_to_find.id
            )

        return FileSystemProtocol.process_response(conn, response, node_to_ask)

    @staticmethod
    def call_find_value(conn, node_to_ask: Node, node_to_find: Node, is_metadata=True):
        """
        async function to call the find value rpc method
        """
        response = None
        address = (node_to_ask.ip, node_to_ask.port)
        response = None
        if conn:
            response = conn.rpc_find_value(
                address, FileSystemProtocol.source_node.id, node_to_find.id, is_metadata
            )

        logger.debug(str(response))
        return FileSystemProtocol.process_response(conn, response, node_to_ask)

    @staticmethod
    def call_find_chunk_location(conn, node_to_ask: Node, node_to_find: Node):
        address = (node_to_ask.ip, node_to_ask.port)
        response = None

        if conn:
            logger.debug("calling rpc_find_chunk_location")
            response = conn.rpc_find_chunk_location(
                address, FileSystemProtocol.source_node.id, node_to_find.id
            )
        logger.debug(str(response))
        return FileSystemProtocol.process_response(conn, response, node_to_ask)

    @staticmethod
    def call_ping(conn, node_to_ask: Node):
        """
        async function to call the ping rpc method
        """
        response = None
        address = (node_to_ask.ip, node_to_ask.port)
        logge.info(f"calling ping {address}")
        response = None

        if conn:
            response = conn.rpc_ping(
                address, FileSystemProtocol.source_node.id)

        logger.debug(f"Got Response {response}")

        return FileSystemProtocol.process_response(conn, response, node_to_ask)

    @staticmethod
    def wellcome_if_new(conn, node: Node):
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

        # TODO uncomment this
        if (node.ip, node.port) == (FileSystemProtocol.source_node.ip, FileSystemProtocol.source_node.port):
            logger.critical("called wellcome if new in self")
            return
        # add node to table

        logger.debug("Adding new node to contacts")
        FileSystemProtocol.router.add_contact(node)

        logger.info(f"never seen {node} before, adding to router")
        # iterate over storage

        logger.info(f"Adding new Node to contacts {FileSystemProtocol.source_node}")

        for key, value, is_metadata in FileSystemProtocol.storage:
            logger.debug("entry for")
            # Create fictional node to calculate distance
            keynode = Node(digest(key))
            neighbors = FileSystemProtocol.router.find_neighbors(keynode)

            new_node_close = False
            this_closest = False
            # if the node is closer tan the furtherst neighbor
            # the values should be then stored in that node
            # if len(neighbors) > 2:
            logger.info(f"neighbors in for {neighbors}")

            if neighbors or len(neighbors) > 0:
                last = neighbors[-1].distance_to(keynode)
                new_node_close = node.distance_to(keynode) < last
                first = neighbors[0].distance_to(keynode)
                this_closest = (
                    FileSystemProtocol.source_node.distance_to(keynode) < first
                )
            # if not neighbors, store data in the node
            if not neighbors or (new_node_close and this_closest):
                logger.debug("calling call_store in wellcome_if_new")
                with ServerSession(node.ip, node.port) as conn:
                    FileSystemProtocol.call_store(
                        conn, node, key, value, is_metadata)

    @staticmethod
    def process_response(conn, response, node: Node):
        """
        If we get a response, add the node to the routing table.  If
        we get no response, make sure it's removed from the routing table.
        """

        logger.debug(f"response is {response}")
        if response is None:
            logger.info(f"no response from {node}, removing from router")
            FileSystemProtocol.router.remove_contact(node)
            return response

        FileSystemProtocol.wellcome_if_new(conn, node)
        logger.debug(f"got successful response from {node}")
        logger.debug(response)
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
