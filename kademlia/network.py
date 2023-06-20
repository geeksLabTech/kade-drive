"""
Package for interacting on the network at a high level.
"""
import random
import pickle
import asyncio
import logging
from re import S

from kademlia.protocol import FileSystemProtocol, ServerSession
from kademlia.routing import RoutingTable
from kademlia.utils import digest
from kademlia.storage import ForgetfulStorage, IStorage, PersistentStorage
from kademlia.node import Node
from kademlia.crawling import ValueSpiderCrawl
from kademlia.crawling import NodeSpiderCrawl
# from models.file import File
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
        Server.node = Node(node_id or digest(
            random.getrandbits(255)), ip=ip, port=str(port))
        print("NODE ID", Server.node.id)
        Server.routing = RoutingTable(Server.ksize, Server.node)
        FileSystemProtocol.init(Server.routing, Server.storage)
        print(port, ip)
        threading.Thread(target=Server.listen, args=(port, ip)).start()

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
        print(
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
        print('results of spider find: ', res)
        print(res)

        return res

    @staticmethod
    def bootstrap_node(addr: tuple[str, str]):
        response = None
        with ServerSession(addr[0], addr[1]) as conn:
            response = conn.rpc_ping(
                (Server.node.ip, Server.node.port), Server.node.id)
        # print(bytes(response))
            return Node(response, addr[0], addr[1]) if response else None

    @staticmethod
    def split_data(data: bytes, chunk_size: int):
        """Split data into chunks of less than chunk_size, it must be less than 16mb"""
        fixed_chunks = len(data) // chunk_size
        last_chunk_size = len(data) - fixed_chunks * chunk_size
        start_of_last_chunk = len(data)-last_chunk_size
        last_chunk = data[start_of_last_chunk:start_of_last_chunk+chunk_size]
        # chunks = [data[i:i+chunk_size] for i in range(fixed_chunks)]
        chunks = []
        count = 0
        last_position = 0
        while(not (fixed_chunks == count)):
            if count == 0:
                chunks.append(data[0:chunk_size])
                last_position = chunk_size
            else:
                chunks.append(data[last_position: last_position + chunk_size])
                last_position = last_position + chunk_size
            count +=1
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
            print("There are no known neighbors to set key %s",
                  dkey.hex())
            print('storing in current server')
            Server.storage[dkey] = value
            return True

        spider = NodeSpiderCrawl(node, nearest,
                                 Server.ksize, Server.alpha)
        nodes = spider.find()
        print("setting '%s' on %s", dkey.hex(), list(map(str, nodes)))

        # if this node is close too, then store here as well
        biggest = max([n.distance_to(node) for n in nodes])
        if Server.node.distance_to(node) < biggest:
            Server.storage[dkey] = value

        any_result = False
        for n in nodes:
            address = (n.ip, n.port)
            with ServerSession(address[0], address[1]) as conn:
                result = FileSystemProtocol.call_store(conn, n, dkey, value)
                if result:
                    any_result = True

        # return true only if at least one store call succeeded
        return any_result

    # def refresh_table(self):
    #     print("Refreshing routing table")
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

    @rpyc.exposed
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
        print('Entry in rpc_store')
        source = Node(nodeid, sender[0], sender[1])
        # if a new node is sending the request, give all data it should contain

        address = (source.ip, source.port)
        with ServerSession(address[0], address[1]) as conn:
            FileSystemProtocol.welcome_if_new(conn, source)

        print("got a store request from %s, storing '%s'='%s'",
              sender, key.hex(), value)
        # store values and report success
        FileSystemProtocol.storage[key] = value
        return True

    @rpyc.exposed
    def rpc_find_value(self, sender: tuple[str, str], nodeid: bytes, key: bytes):
        source = Node(nodeid, sender[0], sender[1])
        # if a new node is sending the request, give all data it should contain
        address = (source.ip, source.port)
        with ServerSession(address[0], address[1]) as conn:
            FileSystemProtocol.welcome_if_new(conn, source)
        # get value from storage
        value = FileSystemProtocol.storage.get(key, None)
        return value
        # if not value found, ask the info for the value to the nodes
        # if value is None:
        #     return self.rpc_find_node(sender, nodeid, key)
        # return {'value': value}

    @rpyc.exposed
    def rpc_stun(self, sender):  # pylint: disable=no-self-use
        return sender

    @rpyc.exposed
    def rpc_ping(self, sender, nodeid: bytes):
        """Probe a Node to see if pc is online

        Args:
            sender : sender node
            nodeid (bytes): node to be probed

        Returns:
            bytes: node id if alive, None if not 
        """
        print(f"rpc ping called from {nodeid}, {sender[0]}, {sender[1]}")
        source = Node(nodeid, sender[0], sender[1])
        # if a new node is sending the request, give all data it should contain
        address = (source.ip, source.port)
        with ServerSession(address[0], address[1]) as conn:
            FileSystemProtocol.welcome_if_new(conn, source)
        print("return ping")
        return FileSystemProtocol.source_node.id

    @rpyc.exposed
    def rpc_find_node(self, sender, nodeid: bytes, key: bytes):
        print(f"finding neighbors of {int(nodeid.hex(), 16)} in local table")

        source = Node(nodeid, sender[0], sender[1])

        print('node id', nodeid)
        # if a new node is sending the request, give all data it should contain
        address = (source.ip, source.port)
        with ServerSession(address[0], address[1]) as conn:
            FileSystemProtocol.welcome_if_new(conn, source)
        # create a fictional node to perform the search
        print('fictional key ', key)
        node = Node(key)
        # ask for the neighbors of the node
        neighbors = FileSystemProtocol.router.find_neighbors(
            node, exclude=node)
        print('neighbors of find_node: ', neighbors)
        return list(map(tuple, neighbors))

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
        print("Looking up key %s", key)
        if apply_hash_to_key:
            key = digest(key)
        # if this node has it, return it
        if Server.storage.get(key) is not None:
            return Server.storage.get(key)
        node = Node(key)
        nearest = FileSystemProtocol.router.find_neighbors(node)
        if not nearest:
            print("There are no known neighbors to get key %s", key)
            return None
        spider = ValueSpiderCrawl(node, nearest,
                                  Server.ksize, Server.alpha)
        return spider.find()

    @rpyc.exposed
    def get_file_chunks(self, hashed_chunks):
        results = [self.get(chunk, False) for chunk in hashed_chunks]
        data_chunks = [f for f in results if f is File]

        if len(hashed_chunks) != len(data_chunks):
            print('Failed to retrieve all data for chunks')

        data = b''.join(data_chunks)
        return data

    @rpyc.exposed
    def upload_file(self, data: bytes):
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
        print("setting '%s' = '%s' on network", key, value)
        if apply_hash_to_key:
            key = digest(key)
        return Server.set_digest(key, value)

    # def save_state(self, fname: str):
    #     """
    #     Save the state of this node (the alpha/ksize/id/immediate neighbors)
    #     to a cache file with the given fname.
    #     """
    #     print("Saving state to %s", fname)
    #     data = {
    #         'ksize': self.ksize,
    #         'alpha': self.alpha,
    #         'id': self.node.id,
    #         'neighbors': self.bootstrappable_neighbors()
    #     }
    #     if not data['neighbors']:
    #         print("No known neighbors, so not writing to cache.")
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
    #     print("Loading state from %s", fname)
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
