"""
Package for interacting on the network at a high level.
"""
import random
import logging
from rpyc import Service
import threading
from time import sleep
import rpyc
import socket
import pickle
from rpyc.utils.server import ThreadedServer
import logging

from core.protocol import FileSystemProtocol, ServerSession
from core.routing import RoutingTable
from core.utils import digest
from core.storage import PersistentStorage
from core.node import Node
from core.crawling import ChunkLocationSpiderCrawl, ValueSpiderCrawl
from core.crawling import NodeSpiderCrawl
# from models.file import File
logger = logging.getLogger(__name__)

class Server:
    ksize: int
    alpha: int
    storage: PersistentStorage
    node: Node
    routing: RoutingTable

    @staticmethod
    def init(ksize=2, alpha=3, ip: str = '0.0.0.0', port: int = 8086, node_id: bytes | None = None, storage: PersistentStorage | None = None):
        """
        Args:
            ksize (int): Replication factor, determines to how many closest peers a record is replicated
            alpha (int): concurrency parameter, determines how many parallel asynchronous FIND_NODE RPC send
            node_id: The id for this node on the network.
            storage: An instance that implements the interface
                     :class:`~kademlia.storage.PersistenceStorage`
        """
        
        Server.ksize = ksize
        Server.alpha = alpha
        Server.storage = storage or PersistentStorage()
        Server.node = Node(node_id or digest(
            random.getrandbits(255)), ip=ip, port=str(port))
        logger.debug("NODE ID", Server.node.id)
        Server.routing = RoutingTable(Server.ksize, Server.node)
        FileSystemProtocol.init(Server.routing, Server.storage)
        logger.debug(port, ip)
        threading.Thread(target=Server.listen, args=(port, ip)).start()
        refresh_thread = threading.Thread(target=Server._refresh_table)
        refresh_thread.start()

    @staticmethod
    def listen(port, interface='0.0.0.0'):
        """
        Start listening on the given port.

        Provide interface="::" to accept ipv6 address
        """
        print(interface, port)
        Server.node.ip = interface
        Server.node.port = port
        t = ThreadedServer(ServerService, port=port, hostname=interface, protocol_config={
            'allow_public_attrs': True,
            'allow_pickle': True
        })
        t.start()

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
        # gathered = await asyncio.gather(*cos)
        # print(cos)
        nodes = [node for node in cos if node is not None]
        # print(nodes)
        spider = NodeSpiderCrawl(Server.node, nodes,
                                 Server.ksize, Server.alpha)
        # print(spider)
        res = spider.find()
        logger.debug('results of spider find: %s', res)
        logger.debug(res)

        return res

    @staticmethod
    def bootstrap_node(addr: tuple[str, str]):
        response = None
        with ServerSession(addr[0], addr[1]) as conn:
            if conn:
                response = conn.rpc_ping(
                    (Server.node.ip, Server.node.port), Server.node.id)
            # print(bytes(response))
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
        while (not (fixed_chunks == count)):
            if count == 0:
                chunks.append(data[0:chunk_size])
                last_position = chunk_size
            else:
                chunks.append(data[last_position: last_position + chunk_size])
                last_position = last_position + chunk_size
            count += 1
        return chunks

    @staticmethod
    def set_digest(dkey: bytes, value, metadata=True):
        """
        Set the given SHA1 digest key (bytes) to the given value in the
        network.
        """
        
        node = Node(dkey)
        assert node is not None
        nearest = FileSystemProtocol.router.find_neighbors(node)
        if not nearest:
            logger.warning("There are no known neighbors to set key %s",
                  dkey.hex())

            if not Server.storage.contains(dkey):
                logger.info('storing in current server')
                if metadata:
                    Server.storage.set_metadata(dkey, value, False)
                else:
                    Server.storage.set_value(dkey, value, False)

            return True

        spider = NodeSpiderCrawl(node, nearest,
                                 Server.ksize, Server.alpha)
        nodes = spider.find()
        logger.debug("setting '%s' on %s", dkey, list(map(str, nodes)))

        # if this node is close too, then store here as well
        biggest = max([n.distance_to(node) for n in nodes])
        if Server.node.distance_to(node) < biggest:
            if Server.storage.contains(dkey):
                if metadata:
                    Server.storage.set_metadata(dkey, value, False)
                else:
                    Server.storage.set_value(dkey, value, False)

        any_result = False
        for n in nodes:
            address = (n.ip, n.port)
            with ServerSession(address[0], address[1]) as conn:
                contains = FileSystemProtocol.call_contains(conn, n, dkey)
                if not contains:
                    result = FileSystemProtocol.call_store(
                        conn, n, dkey, value, metadata)
                    if result:
                        any_result = True

                if contains:
                    any_result = True

        # return true only if at least one store call succeeded
        return any_result

    @staticmethod
    def find_replicas():
        nearest = FileSystemProtocol.router.find_neighbors(
            Server.node, Server.alpha, exclude=Server.node)
        spider = NodeSpiderCrawl(Server.node, nearest,
                                 Server.ksize, Server.alpha)

        nodes = spider.find()

        keys_to_find = Server.storage.keys()
        keys_dict = {}
        for n in nodes:
            with ServerSession(n.ip, n.port) as conn:
                # if len(keys_to_find) > 0:
                for k, is_metadata in keys_to_find:
                    contains = FileSystemProtocol.call_contains(conn, n, k)
                    if contains:
                        if not (k, is_metadata) in keys_dict:
                            keys_dict[(k, is_metadata)] = 0
                        keys_dict[(k, is_metadata)] += 1

        return_list = []
        for k in keys_dict:
            logger.debug(k)
            if keys_dict[k] < Server.ksize:
                return_list.append(k)
        return return_list

    @staticmethod
    def _refresh_table():
        """
        Refresh buckets that haven't had any lookups in the last hour
        (per section 2.3 of the paper).
        """
        
        while (True):
            try:
                sleep(5)
                logger.info("Refreshing Table")

                results = []
                for node_id in FileSystemProtocol.get_refresh_ids():
                    node = Node(node_id)
                    nearest = FileSystemProtocol.router.find_neighbors(
                        node, Server.alpha)
                    spider = NodeSpiderCrawl(node, nearest,
                                             Server.ksize, Server.alpha)

                    results.append(spider.find())

                # do our crawling
                logger.debug('Republishing old keys')
                for key, value, is_metadata in Server.storage.iter_older_than(5):
                    # print(f'key {key}, value {value}, is_metadata {is_metadata}')
                    Server.set_digest(key, value, is_metadata)
                    Server.storage.update_republish(key)
                keys_to_replicate = Server.find_replicas()

                if len(keys_to_replicate):
                    for key, is_metadata in keys_to_replicate:
                        Server.set_digest(key, Server.storage.get(
                            key, metadata=is_metadata, update_timestamp=False), is_metadata)

            except Exception as e:
                logger.error("Thrown Exception %s", str(e))
                pass


@rpyc.service
class ServerService(Service):

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
        

        logger.debug('Entry in rpc_store')
        source = Node(nodeid, sender[0], sender[1])
        # if a new node is sending the request, give all data it should contain

        address = (source.ip, source.port)
        with ServerSession(address[0], address[1]) as conn:
            FileSystemProtocol.welcome_if_new(conn, source)

        logger.debug(f"got a store request from %s, storing '%s'='%s' {sender}, {key}, {value}")
        # store values and report success
        if metadata:
            FileSystemProtocol.storage.set_metadata(
                key, value, republish_data=False)
        else:
            FileSystemProtocol.storage.set_value(key, value, metadata=False)
        return True

    @rpyc.exposed
    def rpc_find_value(self, sender: tuple[str, str], nodeid: bytes, key: bytes, metadata=True):
        source = Node(nodeid, sender[0], sender[1])
        # if a new node is sending the request, give all data it should contain
        address = (source.ip, source.port)
        with ServerSession(address[0], address[1]) as conn:
            FileSystemProtocol.welcome_if_new(conn, source)
        # get value from storage
        if not FileSystemProtocol.storage.contains(key):
            return self.rpc_find_node(sender, nodeid, key)

        value = FileSystemProtocol.storage.get(key, None, metadata)
        return {'value': value}

    @rpyc.exposed
    def rpc_find_chunk_location(self, sender: tuple[str, str], nodeid: bytes, key: bytes):
        
        logger.debug('entry in rpc_find_chunk_location')

        source = Node(nodeid, sender[0], sender[1])
        # if a new node is sending the request, give all data it should contain
        address = (source.ip, source.port)
        with ServerSession(address[0], address[1]) as conn:
            FileSystemProtocol.welcome_if_new(conn, source)
        # get value from storage
        if Server.storage.contains(key):
            return {'value': (Server.node.ip, Server.node.port)}
        return self.rpc_find_node(sender, nodeid, key)

    @rpyc.exposed
    def rpc_ping(self, sender, nodeid: bytes):
        """Probe a Node to see if pc is online

        Args:
            sender : sender node
            nodeid (bytes): node to be probed

        Returns:
            bytes: node id if alive, None if not 
        """
        

        logger.debug(f"rpc ping called from {nodeid}, {sender[0]}, {sender[1]}")
        source = Node(nodeid, sender[0], sender[1])
        # if a new node is sending the request, give all data it should contain
        address = (source.ip, source.port)
        with ServerSession(address[0], address[1]) as conn:
            FileSystemProtocol.welcome_if_new(conn, source)
        logger.debug("return ping")
        return FileSystemProtocol.source_node.id

    @rpyc.exposed
    def rpc_find_node(self, sender, nodeid: bytes, key: bytes):
        

        logger.debug(
            f"finding neighbors of {int(nodeid.hex(), 16)} in local table")

        source = Node(nodeid, sender[0], sender[1])

        logger.debug(f'node id {nodeid}')
        # if a new node is sending the request, give all data it should contain
        address = (source.ip, source.port)
        with ServerSession(address[0], address[1]) as conn:
            FileSystemProtocol.welcome_if_new(conn, source)
        # create a fictional node to perform the search
        logger.debug(f'fictional key {key}')
        logger.debug(f'SEnder [0] Sender [1] {source.ip}, {source.port}')
        node = Node(key)
        # ask for the neighbors of the node
        neighbors = FileSystemProtocol.router.find_neighbors(
            node, exclude=source)
        # if len(neighbors) == 0:
        #     neighbors = [Server.node]
        logger.debug(f'neighbors of find_node: { neighbors}')
        return list(map(tuple, neighbors))

    @rpyc.exposed
    def rpc_contains(self, sender, nodeid: bytes, key: bytes):
        source = Node(nodeid, sender[0], sender[1])
        # if a new node is sending the request, give all data it should contain
        address = (source.ip, source.port)
        with ServerSession(address[0], address[1]) as conn:
            FileSystemProtocol.welcome_if_new(conn, source)
        # get value from storage
        return FileSystemProtocol.storage.contains(key)

    @rpyc.exposed
    def get_file_chunk_value(self, key):
        return Server.storage.get(key, metadata=False)

    @rpyc.exposed
    def bootstrappable_neighbors(self):
        """
        Get a :class:`list` of (ip, port) :class:`tuple` pairs suitable for
        use as an argument to the bootstrap method.

        The server should have been bootstrapped
        already - this is just a utility for getting some neighbors and then
        storing them if this server is going down for a while.  When it comes
        back up, the list of nodes can be used to bootstrap.
        """
        neighbors = FileSystemProtocol.router.find_neighbors(Server.node)
        return [tuple(n)[-2:] for n in neighbors]

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
        # if this node has it, return it
        if Server.storage.get(key, True) is not None:
            return pickle.loads(Server.storage.get(key, True))
        node = Node(key)
        nearest = FileSystemProtocol.router.find_neighbors(node)
        if not nearest:
            logger.info(f"There are no known neighbors to get key {key}")
            return None
        spider = ValueSpiderCrawl(node, nearest,
                                  Server.ksize, Server.alpha)
        metadata_list = pickle.loads(spider.find())
        return metadata_list

    @rpyc.exposed
    def get_file_chunk_location(self, chunk_key):
        

        logger.debug('looking file chunk location')
        node = Node(chunk_key)
        nearest = FileSystemProtocol.router.find_neighbors(node)
        if not nearest:
            logger.debug(
                f"There are no known neighbors to get file chunk location {chunk_key}")
            if Server.storage.contains(chunk_key) is not None:
                logger.debug(f'Found in this server, {Server.node.ip}, port, {Server.node.port}')
                return [(Server.node.ip, Server.node.port)]
            return None

        logger.debug('Initiating ChunkLocationSpiderCrawl')
        spider = ChunkLocationSpiderCrawl(
            node, nearest, Server.ksize, Server.alpha)
        results = spider.find()
        logger.debug(f'results of ChunkLocationSpider {results}')
        return results

    @rpyc.exposed
    def upload_file(self, key, data: bytes, apply_hash_to_key=True):
        chunks = Server.split_data(data, 1000)
        logger.debug(f'chunks {len(chunks)}, {chunks}')
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
    def set_key(self, key, value, apply_hash_to_key=True):
        """
        Set the given string key to the given value in the network.
        """
        
        if not check_dht_value_type(value):
            logger.critical(f'TypeError::el valor es: P{value}')
            raise TypeError(
                f"Value must be of type int, float, bool, str, or bytes, received {value}"
            )
        # print("setting '%s' = '%s' on network", key, value)
        if apply_hash_to_key:
            key = digest(key)
        return Server.set_digest(key, value)

    @rpyc.exposed
    def find_neighbors(self):
        nearest = FileSystemProtocol.router.find_neighbors(
            Server.node, exclude=Server.node)
        return [(i.ip, i.port) for i in nearest]


def check_dht_value_type(value):
    """
    Checks to see if the type of the value is a valid type for
    placing in the dht.
    """
    typeset = [
        int,
        float,
        bool,
        str,
        bytes
    ]
    return type(value) in typeset  # pylint: disable=unidiomatic-typecheck
