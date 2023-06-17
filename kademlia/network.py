"""
Package for interacting on the network at a high level.
"""
import random
import pickle
import asyncio
import logging
from re import S

from kademlia.protocol import FileSystemProtocol, ServerSessionService, ServerSession
from kademlia.routing import RoutingTable
from kademlia.utils import digest
from kademlia.storage import ForgetfulStorage, IStorage, PersistentStorage
from kademlia.node import Node
from kademlia.crawling import ValueSpiderCrawl
from kademlia.crawling import NodeSpiderCrawl
from models.file import File
import socket
from rpyc import Service
from rpyc.utils.server import ThreadedServer
import rpyc
import threading
log = logging.getLogger(__name__)  # pylint: disable=invalid-name


class Server:
    ksize: int
    alpha: int
    storage: PersistentStorage
    node: Node 
    routing: RoutingTable

    @staticmethod
    def init(ksize=20, alpha=3, ip: str = '0.0.0.0', port: int = 8086, node_id: bytes | None = None, storage: PersistentStorage | None = None):
        """
        Args:
            ksize (int): Replication factor, determines to how many closest peers a record is replicated
            alpha (int): concurrency parameter, determines how many parallel asynchronous FIND_NODE RPC send
            node_id: The id for this node on the network.
            storage: An instance that implements the interface
                     :class:`~kademlia.storage.IStorage`
        """
        Server.ksize = ksize
        Server.alpha = alpha
        Server.storage = storage or PersistentStorage()
        Server.node = Node(node_id or digest(random.getrandbits(255)), ip=ip, port=str(port))
        Server.routing = RoutingTable(Server.ksize, Server.node)
        FileSystemProtocol.init(Server.routing, Server.storage)
        threading.Thread(target=Server.listen, args=(port, ip)).start()
        
    @staticmethod
    def listen(port, interface='0.0.0.0'):
        """
        Start listening on the given port.

        Provide interface="::" to accept ipv6 address
        """
        Server.node.ip = interface
        Server.node.port = port
        t = ThreadedServer(ServerService, port=port, hostname=interface, protocol_config={
        'allow_public_attrs': True,
        })
        t.start()
        # finally, schedule refreshing table
        # Server.refresh_table()

    @staticmethod
    def bootstrap(addrs: list[tuple[str, str]]):
        """
        Bootstrap the server by connecting to other known nodes in the network.

        Args:
            addrs: A `list` of (ip, port) `tuple` pairs.  Note that only IP
                   addresses are acceptable - hostnames will cause an error.
        """
        log.debug("Attempting to bootstrap node with %i initial contacts",
                  len(addrs))
        cos = list(map(Server.bootstrap_node, addrs))
        # gathered = await asyncio.gather(*cos)
        nodes = [node for node in cos if node is not None]
        spider = NodeSpiderCrawl(Server.node, nodes,
                                 Server.ksize, Server.alpha)
        return spider.find()

    @staticmethod
    def bootstrap_node(addr: tuple[str, str]):
        response = None
        with ServerSession(addr[0], addr[1]) as conn:
            response = conn.rpc_ping(addr, Server.node.id)
        
        return Node(response[1], addr[0], addr[1]) if response[0] else None
    
    @staticmethod
    def split_data(data: bytes, chunk_size: int):
        """Split data into chunks of less than chunk_size, it must be less than 16mb"""
        fixed_chunks = len(data) // chunk_size
        last_chunk_size = len(data) - fixed_chunks * chunk_size
        start_of_last_chunk = len(data)-last_chunk_size
        last_chunk = data[start_of_last_chunk:start_of_last_chunk+chunk_size]
        chunks = [data[i:i+chunk_size] for i in range(fixed_chunks)]
        if last_chunk_size > 0:
            chunks.append(last_chunk)

        return chunks

    @staticmethod
    def set_digest(dkey: bytes, value):
        """
        Set the given SHA1 digest key (bytes) to the given value in the
        network.
        """
        node = Node(dkey)

        nearest = FileSystemProtocol.router.find_neighbors(node)
        if not nearest:
            log.warning("There are no known neighbors to set key %s",
                        dkey.hex())
            return False

        spider = NodeSpiderCrawl(node, nearest,
                                 Server.ksize, Server.alpha)
        nodes = spider.find()
        log.info("setting '%s' on %s", dkey.hex(), list(map(str, nodes)))

        # if this node is close too, then store here as well
        biggest = max([n.distance_to(node) for n in nodes])
        if Server.node.distance_to(node) < biggest:
            Server.storage[dkey] = value
        results = [FileSystemProtocol.call_store(n, dkey, value) for n in nodes]
        # return true only if at least one store call succeeded
        return any(results)
    
    # def refresh_table(self):
    #     log.debug("Refreshing routing table")
    #     self._refresh_table()
    #     loop = asyncio.get_event_loop()
    #     self.refresh_loop = loop.call_later(3600, self.refresh_table)

    # def _refresh_table(self):
    #     """
    #     Refresh buckets that haven't had any lookups in the last hour
    #     (per section 2.3 of the paper).
    #     """
    #     results = []
    #     for node_id in FileSystemProtocol.get_refresh_ids():
    #         node = Node(node_id)
    #         nearest = FileSystemProtocol.router.find_neighbors(node, self.alpha)
    #         spider = NodeSpiderCrawl(FileSystemProtocol, node, nearest,
    #                                  self.ksize, self.alpha)
    #         results.append(spider.find())

# pylint: disable=too-many-instance-attributes
@rpyc.service
class ServerService(Service):
    
    # def stop(self):
    #     if self.thread:
    #         self.thread.join()

    #     if self.refresh_loop:
    #         self.refresh_loop.cancel()

    #     if self.save_state_loop:
    #         self.save_state_loop.cancel()

    # def _create_protocol(self):
    #     return self.protocol_class(self.node, self.storage, self.ksize)

    

    # 

        # do our crawling
        # await asyncio.gather(*results)

        # now republish keys older than one hour
        # for dkey, value in self.storage.iter_older_than(3600):
        #     self.set_digest(dkey, value)
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
        log.info("Looking up key %s", key)
        if apply_hash_to_key:
            key = digest(key)
        # if this node has it, return it
        if Server.storage.get(key) is not None:
            return Server.storage.get(key)
        node = Node(key)
        nearest = FileSystemProtocol.router.find_neighbors(node)
        if not nearest:
            log.warning("There are no known neighbors to get key %s", key)
            return None
        spider = ValueSpiderCrawl(node, nearest,
                                  Server.ksize, Server.alpha)
        return spider.find()

    @rpyc.exposed
    def get_file_chunks(self, hashed_chunks):
        results = [self.get(chunk, False) for chunk in hashed_chunks]
        data_chunks = [f for f in results if f is File]

        if len(hashed_chunks) != len(data_chunks):
            log.warning('Failed to retrieve all data for chunks')

        data = b''.join(data_chunks)
        return data

    @rpyc.exposed
    def upload_file(self, data: bytes):
        # 1000000 bytes is equivalent to 1mb
        chunks = Server.split_data(data, 1000000)
        processed_chunks = ((digest(c), c) for c in chunks)
        for c in processed_chunks:
            self.set_key(c[0], c[1], False)
    

    @rpyc.exposed
    def set_key(self, key, value, apply_hash_to_key=True):
        """
        Set the given string key to the given value in the network.
        """

        if not check_dht_value_type(value):
            print('eel valor es: ', value)
            raise TypeError(
                f"Value must be of type int, float, bool, str, or bytes, received {value}"
            )
        log.info("setting '%s' = '%s' on network", key, value)
        if apply_hash_to_key:
            key = digest(key)
        return Server.set_digest(key, value)

    

    # def save_state(self, fname: str):
    #     """
    #     Save the state of this node (the alpha/ksize/id/immediate neighbors)
    #     to a cache file with the given fname.
    #     """
    #     log.info("Saving state to %s", fname)
    #     data = {
    #         'ksize': self.ksize,
    #         'alpha': self.alpha,
    #         'id': self.node.id,
    #         'neighbors': self.bootstrappable_neighbors()
    #     }
    #     if not data['neighbors']:
    #         log.warning("No known neighbors, so not writing to cache.")
    #         return
    #     with open(fname, 'wb') as file:
    #         pickle.dump(data, file)

    # @classmethod
    # def load_state(cls, fname: str, port: str, interface='0.0.0.0'):
    #     """
    #     Load the state of this node (the alpha/ksize/id/immediate neighbors)
    #     from a cache file with the given fname and then bootstrap the node
    #     (using the given port/interface to start listening/bootstrapping).
    #     """
    #     log.info("Loading state from %s", fname)
    #     with open(fname, 'rb') as file:
    #         data = pickle.load(file)
    #     svr = cls(data['ksize'], data['alpha'], data['id'])
    #     await svr.listen(port, interface)
    #     if data['neighbors']:
    #         await svr.bootstrap(data['neighbors'])
    #     return svr

    # def save_state_regularly(self, fname: str, frequency=600):
    #     """
    #     Save the state of node with a given regularity to the given
    #     filename.

    #     Args:
    #         fname: File name to save retularly to
    #         frequency: Frequency in seconds that the state should be saved.
    #                     By default, 10 minutes.
    #     """
    #     self.save_state(fname)
    #     loop = asyncio.get_event_loop()
    #     self.save_state_loop = loop.call_later(frequency,
    #                                            self.save_state_regularly,
    #                                            fname,
    #                                            frequency)


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
