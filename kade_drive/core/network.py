"""
Package for interacting on the network at a high level.
"""
import random
import logging
from rpyc import Service
import threading
from time import sleep
import rpyc
import pickle
from rpyc.utils.server import ThreadedServer
from kade_drive.core.config import Config
from kade_drive.core.protocol import FileSystemProtocol, ServerSession
from kade_drive.core.routing import RoutingTable
from kade_drive.core.utils import digest
from kade_drive.core.storage import PersistentStorage
from kade_drive.core.node import Node
from kade_drive.core.crawling import ChunkLocationSpiderCrawl, ValueSpiderCrawl
from kade_drive.core.crawling import NodeSpiderCrawl
from kade_drive.core.utils import is_port_in_use

# from models.file import File

# Create a file handler
# file_handler = logging.FileHandler("log_file.log")
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
# file_handler.setFormatter(formatter)
logger = logging.getLogger(__name__)
# logger.addHandler(file_handler)


class Server:
    ksize: int
    alpha: int
    storage: PersistentStorage
    node: Node
    routing: RoutingTable

    @staticmethod
    def init(
        config: Config,
        ksize=2,
        alpha=3,
        ip: str = "0.0.0.0",
        port: int = 8086,
        node_id: bytes | None = None,
        storage: PersistentStorage | None = None,
    ):
        """
        Args:
            ksize (int): Replication factor, determines to how many closest peers a record is replicated
            alpha (int): concurrency parameter, determines how many parallel asynchronous FIND_NODE RPC send
            node_id: The id for this node on the network.
            storage: An instance that implements the interface
                     :class:`~kademlia.storage.PersistenceStorage`
        """
        while is_port_in_use(ip, port):
            port += 1

        logging.getLogger(f"SERVER/{port}").setLevel(logging.CRITICAL + 1)
        Server.ksize = ksize
        Server.alpha = alpha
        Server.storage = storage or PersistentStorage(config.ttl)
        Server.node = Node(
            node_id or digest(random.getrandbits(255)), ip=ip, port=str(port)
        )
        logger.debug(f"NODE ID: {Server.node.id}")
        Server.routing = RoutingTable(Server.ksize, Server.node)
        FileSystemProtocol.init(Server.routing, Server.storage)
        logger.debug(f"{port}, {ip}")
        threading.Thread(target=Server.listen, args=(port, ip)).start()
        refresh_thread = threading.Thread(
            target=Server._refresh_table, args=(config.refresh_sleep,)
        )
        refresh_thread.start()

    @staticmethod
    def listen(port, interface="0.0.0.0"):
        """
        Start listening on the given port.

        Provide interface="::" to accept ipv6 address
        """
        while True:
            try:
                print(interface, port)
                Server.node.ip = interface
                Server.node.port = port
                t = ThreadedServer(
                    ServerService,
                    port=port,
                    hostname=interface,
                    protocol_config={
                        "allow_public_attrs": True, "allow_pickle": True},
                )
                t.start()
            except Exception as e:
                logger.critical(f"Server Listen failed: {e}")

    @staticmethod
    def bootstrap(addrs: list[tuple[str, str]]):
        """
        Bootstrap the server by connecting to other known nodes in the network.

        Args:
            addrs: A `list` of (ip, port) `tuple` pairs.  Note that only IP
                   addresses are acceptable - hostnames will cause an error.
        """

        logger.debug(
            f"Attempting to bootstrap node with {len(addrs)} initial contacts")
        cos = list(map(Server.bootstrap_node, addrs))
        nodes = [node for node in cos if node is not None]
        spider = NodeSpiderCrawl(
            Server.node, nodes, Server.ksize, Server.alpha)
        res = spider.find()
        logger.debug("results of spider find: %s", res)

        return res

    @staticmethod
    def bootstrap_node(addr: tuple[str, str]):
        response = None
        with ServerSession(addr[0], addr[1]) as conn:
            if conn:
                response = conn.rpc_ping(
                    (Server.node.ip, Server.node.port), Server.node.id
                )
                node = Node(response, addr[0], addr[1]) if response else None
                response = FileSystemProtocol.process_response(
                    conn, response, node)

                return node

    @staticmethod
    def split_data(data: bytes, chunk_size: int):
        """Split data into chunks of less than chunk_size, it must be less than 16mb"""
        if not isinstance(data, bytes):
            data = pickle.dumps(data)
        if not len(data) % chunk_size == 0:
            fixed_chunks = (len(data) // chunk_size) + 1
        else:
            fixed_chunks = len(data) // chunk_size

        chunks = []
        count = 0
        last_position = 0
        while not (fixed_chunks == count):
            if count == 0:
                chunks.append(data[0:chunk_size])
                last_position = chunk_size
            else:
                chunks.append(data[last_position: last_position + chunk_size])
                last_position = last_position + chunk_size
            count += 1
        return chunks

    @staticmethod
    def _handle_empty_neighbors(dkey, metadata, value, exclude_current):
        logger.debug("There are no known neighbors to set key %s", dkey.hex())

        if not exclude_current:
            logger.info("storing in current server")
            if metadata:
                Server.storage.set_metadata(dkey, value, False)
            else:
                Server.storage.set_value(dkey, value, False)

        return True

    @staticmethod
    def set_digest(
        dkey: bytes, value, metadata=True, exclude_current=False, local_last_write=None
    ):
        """
        Set the given SHA1 digest key (bytes) to the given value in the
        network.
        """

        node = Node(dkey)
        assert node is not None
        nearest = FileSystemProtocol.router.find_neighbors(node)
        logger.info(f"nearest in set_digest is {nearest}")

        if not nearest or len(nearest) == 0:
            return Server._handle_empty_neighbors(dkey, metadata, value, exclude_current)
        spider = NodeSpiderCrawl(node, nearest, Server.ksize, Server.alpha)
        nodes = spider.find()
        logger.debug("setting '%s' on %s", dkey, list(map(str, nodes)))

        if not nodes or len(nodes) == 0:
            return Server._handle_empty_neighbors(dkey, metadata, value, exclude_current)
        
        # if this node is close too, then store here as well
        biggest = max([n.distance_to(node) for n in nodes])
        if Server.node.distance_to(node) < biggest and not exclude_current:
            if metadata:
                Server.storage.set_metadata(dkey, value, False)
            else:
                Server.storage.set_value(dkey, value, False)

        any_result = False
        for n in nodes:
            address = (n.ip, n.port)
            with ServerSession(address[0], address[1]) as conn:
                response = FileSystemProtocol.call_check_if_new_value_exists(
                    conn, n, dkey
                )
                contains, date = None, None
                if response is not None:
                    contains, date = response
                if local_last_write is None or date is None or date < local_last_write:
                    result = FileSystemProtocol.call_store(
                        conn, n, dkey, value, metadata
                    )
                    if result:
                        any_result = True

                if contains:
                    any_result = True

        # return true only if at least one store call succeeded
        return any_result

    @staticmethod
    def find_replicas():
        nearest = FileSystemProtocol.router.find_neighbors(
            Server.node, Server.alpha, exclude=Server.node
        )
        spider = NodeSpiderCrawl(Server.node, nearest,
                                 Server.ksize, Server.alpha)

        nodes = spider.find()

        keys_to_find = Server.storage.keys()
        keys_dict = {}
        for n in nodes:
            with ServerSession(n.ip, n.port) as conn:
                for k, is_metadata in keys_to_find:
                    contains = FileSystemProtocol.call_contains(
                        conn, n, k, is_metadata)
                    if contains:
                        if (k, is_metadata) not in keys_dict:
                            keys_dict[(k, is_metadata)] = 0
                        keys_dict[(k, is_metadata)] += 1

        return_list = []
        for k in keys_dict:
            logger.debug(k)
            if keys_dict[k] < Server.ksize:
                return_list.append(k)
        return return_list

    @staticmethod
    def _refresh_table(refresh_sleep):
        while True:
            try:
                sleep(refresh_sleep)
                logger.info("Refreshing Table")

                results = []
                for node_id in FileSystemProtocol.get_refresh_ids():
                    node = Node(node_id)
                    nearest = FileSystemProtocol.router.find_neighbors(
                        node, Server.alpha
                    )
                    spider = NodeSpiderCrawl(
                        node, nearest, Server.ksize, Server.alpha)

                    results.append(spider.find())

                # Republishing keys to mantain the network updated

                logger.debug("Republishing old keys")
                for (
                    key,
                    value,
                    is_metadata,
                    last_write,
                ) in Server.storage.iter_older_than(5):
                    Server.set_digest(key, value, is_metadata,
                                      exclude_current=True)
                    Server.storage.update_republish(key)
                keys_to_replicate = Server.find_replicas()

                # Republishing keys that have less replicas than the replication factor

                if len(keys_to_replicate):
                    for key, is_metadata in keys_to_replicate:
                        _, local_last_write = Server.storage.check_if_new_value_exists(
                            key
                        )

                        Server.set_digest(
                            key,
                            Server.storage.get(
                                key, metadata=is_metadata, update_timestamp=False
                            ),
                            is_metadata,
                            exclude_current=True,
                            local_last_write=local_last_write,
                        )

            except Exception as e:
                logger.error("Thrown Exception %s", str(e))
                pass


@rpyc.service
class ServerService(Service):
    #
    # RPC accessed by clients
    #
    @rpyc.exposed
    def rpc_get_file_chunk_value(self, key):
        return Server.storage.get(key, metadata=False)

    @rpyc.exposed
    def get(self, key, apply_hash_to_key=True):
        """
        Get a key if the network has it.

        Returns:
            :class:`None` if not found, the value otherwise.
        """

        logger.debug(f"Looking up key {key}")
        if apply_hash_to_key:
            key = digest(key)

        node = Node(key)
        nearest = FileSystemProtocol.router.find_neighbors(node)
        if not nearest:
            logger.debug(f"There are no known neighbors to get key {key}")
            if Server.storage.contains(key):
                logger.debug("Getting key from this same node")
                return pickle.loads(Server.storage.get(key, True))
            return None
        spider = ValueSpiderCrawl(node, nearest, Server.ksize, Server.alpha)
        data = spider.find()
        if data is None:
            logger.debug("NONE DATA")
            return None
        logger.debug(f"DATA {data}")
        metadata_list = pickle.loads(data)
        return metadata_list

    @rpyc.exposed
    def upload_file(self, key, data: bytes, apply_hash_to_key=True):
        chunks = Server.split_data(data, 1000)
        logger.debug(f"chunks {len(chunks)}, {chunks}")
        digested_chunks = [digest(c) for c in chunks]
        metadata_list = pickle.dumps(digested_chunks)
        processed_chunks = ((digest(c), c) for c in chunks)

        for c in processed_chunks:
            Server.set_digest(c[0], c[1], metadata=False)

        logger.debug("Writting key metadata")
        if apply_hash_to_key:
            dkey = digest(key)
            Server.set_digest(dkey, metadata_list)
        else:
            Server.set_digest(key, metadata_list)

    @rpyc.exposed
    def get_file_chunk_location(self, chunk_key):
        logger.debug("looking file chunk location")
        node = Node(chunk_key)
        nearest = FileSystemProtocol.router.find_neighbors(node)
        if not nearest:
            logger.debug(
                f"There are no known neighbors to get file chunk location {chunk_key}"
            )
            if Server.storage.contains(chunk_key, False) is not None:
                logger.debug(
                    f"Found in this server, {Server.node.ip}, port, {Server.node.port}"
                )
                return [(Server.node.ip, Server.node.port)]
            return None

        logger.debug("Initiating ChunkLocationSpiderCrawl")
        spider = ChunkLocationSpiderCrawl(
            node, nearest, Server.ksize, Server.alpha)
        results = spider.find()
        logger.debug(f"results of ChunkLocationSpider {results}")
        return results

    @rpyc.exposed
    def rpc_find_chunk_location(
        self, sender: tuple[str, str], nodeid: bytes, key: bytes
    ):
        logger.debug("entry in rpc_find_chunk_location")

        source = Node(nodeid, sender[0], sender[1])
        # if a new node is sending the request, give all data it should contain
        address = (source.ip, source.port)
        with ServerSession(address[0], address[1]) as conn:
            FileSystemProtocol.wellcome_if_new(conn, source)
        # get value from storage
        if Server.storage.contains(key, False):
            return {"value": (Server.node.ip, Server.node.port)}
        return self.rpc_find_node(sender, nodeid, key)

    @rpyc.exposed
    def find_neighbors(self):
        nearest = FileSystemProtocol.router.find_neighbors(
            Server.node, exclude=Server.node
        )
        return [(i.ip, i.port) for i in nearest]

    #
    # RPCs only accessed by servers
    #
    @rpyc.exposed
    def rpc_store(self, sender, nodeid: bytes, key: bytes, value, metadata=True):
        """Instructs a node to store a value

        Args:
            sender : Sender Node
            nodeid (bytes): Node to be told to store info
            key (bytes): key to the value to store
            value : value to store

        Returns:
            bool: True if operation successful
        """

        logger.debug("Entry in rpc_store")
        source = Node(nodeid, sender[0], sender[1])
        # if a new node is sending the request, give all data it should contain

        address = (source.ip, source.port)
        with ServerSession(address[0], address[1]) as conn:
            logger.info(f"wellcome_If_new in rpc_store {address}")
            FileSystemProtocol.wellcome_if_new(conn, source)

        logger.debug(
            f"got a store request from %s, storing '%s'='%s' {sender}, {key}, {value}"
        )
        # store values and report success
        if metadata:
            FileSystemProtocol.storage.set_metadata(
                key, value, republish_data=False)
        else:
            FileSystemProtocol.storage.set_value(key, value, metadata=False)
        return True

    @rpyc.exposed
    def rpc_find_value(
        self, sender: tuple[str, str], nodeid: bytes, key: bytes, metadata=True
    ):
        source = Node(nodeid, sender[0], sender[1])
        # if a new node is sending the request, give all data it should contain
        address = (source.ip, source.port)
        with ServerSession(address[0], address[1]) as conn:
            logger.info(f"wellcome_If_new in find_value {address}")
            FileSystemProtocol.wellcome_if_new(conn, source)
        # get value from storage
        if not FileSystemProtocol.storage.contains(key, metadata):
            logger.debug(
                f"Value with key {key} not found, calling rpc_find_node")
            logger.debug(f"type of key is {type(key)}")

            return self.rpc_find_node(sender, nodeid, key)

        value = FileSystemProtocol.storage.get(key, None, metadata)
        logger.debug(f"returning value {value}")
        return {"value": value}

    @rpyc.exposed
    def rpc_ping(self, sender, nodeid: bytes):
        """Probe a Node to see if pc is online

        Args:
            sender : sender node
            nodeid (bytes): node to be probed

        Returns:
            bytes: node id if alive, None if not
        """
        logger.debug(
            f"rpc ping called from {nodeid}, {sender[0]}, {sender[1]}")
        source = Node(nodeid, sender[0], sender[1])
        # if a new node is sending the request, give all data it should contain
        address = (source.ip, source.port)
        with ServerSession(address[0], address[1]) as conn:
            logger.info(f"wellcome_If_new in ping {address}")
            FileSystemProtocol.wellcome_if_new(conn, source)
        logger.debug("return ping")
        return FileSystemProtocol.source_node.id

    @rpyc.exposed
    def rpc_find_node(self, sender, nodeid: bytes, key: bytes):
        logger.debug(
            f"finding neighbors of {int(nodeid.hex(), 16)} in local table")

        source = Node(nodeid, sender[0], sender[1])

        logger.debug(f"node id {nodeid}")
        # if a new node is sending the request, give all data it should contain
        address = (source.ip, source.port)
        with ServerSession(address[0], address[1]) as conn:
            logger.info(f"wellcome_If_new in find_node {address}")
            FileSystemProtocol.wellcome_if_new(conn, source)
        # create a fictional node to perform the search
        logger.debug(f"fictional key {key}")
        logger.debug(f"SEnder [0] Sender [1] {source.ip}, {source.port}")
        node = Node(key)
        # ask for the neighbors of the node
        neighbors = FileSystemProtocol.router.find_neighbors(
            node, exclude=source)
        logger.debug(f"neighbors of find_node: { neighbors}")
        return list(map(tuple, neighbors))

    @rpyc.exposed
    def rpc_contains(self, sender, nodeid: bytes, key: bytes, is_metadata=True):
        source = Node(nodeid, sender[0], sender[1])
        # if a new node is sending the request, givemsg all data it should contain
        address = (source.ip, source.port)
        with ServerSession(address[0], address[1]) as conn:
            logger.info(f"wellcome_If_new in contains {address}")
            FileSystemProtocol.wellcome_if_new(conn, source)
        # get value from storage
        return FileSystemProtocol.storage.contains(key, is_metadata)

    @rpyc.exposed
    def rpc_check_if_new_value_exists(
        self, sender, nodeid: bytes, key: bytes, is_metadata=True
    ):
        source = Node(nodeid, sender[0], sender[1])
        # if a new node is sending the request, give all data it should contain
        address = (source.ip, source.port)
        with ServerSession(address[0], address[1]) as conn:
            logger.info(f"wellcome_If_new in check_if_new_value {address}")
            FileSystemProtocol.wellcome_if_new(conn, source)
        # get value from storage
        return FileSystemProtocol.storage.check_if_new_value_exists(key)

    @rpyc.exposed
    def set_key(self, key, value, apply_hash_to_key=True):
        """
        Set the given string key to the given value in the network.
        """

        if not check_dht_value_type(value):
            logger.critical(f"TypeError::el valor es: P{value}")
            raise TypeError(
                f"Value must be of type int, float, bool, str, or bytes, received {value}"
            )
        if apply_hash_to_key:
            key = digest(key)
        return Server.set_digest(key, value)


def check_dht_value_type(value):
    """
    Checks to see if the type of the value is a valid type for
    placing in the dht.
    """
    typeset = [int, float, bool, str, bytes]
    return type(value) in typeset
