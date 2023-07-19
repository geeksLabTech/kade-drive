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
import datetime

from rpyc.utils.server import ThreadedServer
from kade_drive.core.config import Config
from kade_drive.core.protocol import FileSystemProtocol, ServerSession
from kade_drive.core.routing import RoutingTable
from kade_drive.core.utils import digest
from kade_drive.core.storage import PersistentStorage
from kade_drive.core.node import Node

from message_system.message_system import MessageSystem

from kade_drive.core.crawling import (
    ChunkLocationSpiderCrawl,
    ConfirmIntegritySpiderCrawl,
    DeleteSpiderCrawl,
    LsSpiderCrawl,
    ValueSpiderCrawl,
)

from kade_drive.core.crawling import NodeSpiderCrawl
from kade_drive.core.utils import is_port_in_use, it_is_necessary_to_write

# from models.file import File


logger = logging.getLogger(__name__)


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
        logger.info(f"NODE ID: {Server.node.id}")
        Server.routing = RoutingTable(Server.ksize, Server.node)
        FileSystemProtocol.init(Server.routing, Server.storage)
        logger.debug(f"{port}, {ip}")
        threading.Thread(target=Server.listen, args=(port, ip)).start()
        threading.Thread(target=Server._detect_alone).start()

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
                        "allow_public_attrs": True,
                        "allow_pickle": True,
                        "sync_request_timeout": None,
                    },
                )
                t.start()
            except Exception as e:
                logger.critical(f"Server Listen failed: {e}")
                while is_port_in_use(Server.node.ip, Server.node.port):
                    port += 1

    @staticmethod
    def bootstrap(addrs: list[tuple[str, str]]):
        """
        Bootstrap the server by connecting to other known nodes in the network.

        Args:
            addrs: A `list` of (ip, port) `tuple` pairs.  Note that only IP
                   addresses are acceptable - hostnames will cause an error.
        """

        logger.debug(f"Attempting to bootstrap node with {len(addrs)} initial contacts")
        cos = list(map(Server.bootstrap_node, addrs))
        nodes = [node for node in cos if node is not None]
        spider = NodeSpiderCrawl(Server.node, nodes, Server.ksize, Server.alpha)
        res = spider.find()
        # logger.debug("results of spider find: %s", res)

        return res

    @staticmethod
    def bootstrap_node(addr: tuple[str, str]):
        response = None
        with ServerSession(addr[0], addr[1]) as conn:
            if conn:
                response = conn.rpc_ping(
                    (Server.node.ip, Server.node.port), Server.node.id, None
                )
                node = Node(response, addr[0], addr[1]) if response else None
                response = FileSystemProtocol.process_response(conn, response, node)

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
                chunks.append(data[last_position : last_position + chunk_size])
                last_position = last_position + chunk_size
            count += 1
        return chunks

    @staticmethod
    def set_digest(
        dkey: bytes,
        value: bytes,
        metadata=True,
        exclude_current=False,
        local_last_write=None,
        key_name="NOT DEFINED",
        do_confirmation=False,
    ):
        """
        Set the given SHA1 digest key (bytes) to the given value in the
        network.
        """
        if value is None:
            return

        # logger.warning(f"Set diges with value {value}")
        node = Node(dkey)
        assert node is not None
        nearest = FileSystemProtocol.router.find_neighbors(node)
        # logger.info(f"nearest in set_digest is {nearest}")

        if not nearest or len(nearest) == 0:
            return Server._handle_empty_neighbors(
                dkey, metadata, value, exclude_current, local_last_write, key_name
            )
        spider = NodeSpiderCrawl(node, nearest, Server.ksize, Server.alpha)
        nodes = spider.find()
        # logger.debug("setting '%s' on %s", dkey, list(map(str, nodes)))

        if not nodes or len(nodes) == 0:
            return Server._handle_empty_neighbors(
                dkey, metadata, value, exclude_current, local_last_write, key_name
            )

        # if this node is close too, then store here as well
        biggest = max([n.distance_to(node) for n in nodes])
        responses = []
        if Server.node.distance_to(node) < biggest and not exclude_current:
            contains, date = Server.storage.check_if_new_value_exists(dkey, metadata)
            if it_is_necessary_to_write(local_last_write, contains, date):
                if metadata:
                    Server.storage.set_metadata(
                        dkey,
                        value,
                        False,
                        key_name=key_name,
                        last_write=local_last_write,
                    )
                else:
                    Server.storage.set_value(
                        dkey, value, False, last_write=local_last_write
                    )
                responses.append(True)

        for n in nodes:
            address = (n.ip, n.port)
            with ServerSession(address[0], address[1]) as conn:
                response = FileSystemProtocol.call_check_if_new_value_exists(
                    conn, n, node, metadata
                )
                contains, date = None, None
                if response is None:
                    responses.append(False)
                    continue

                if response is not None:
                    contains, date = response

                if it_is_necessary_to_write(local_last_write, contains, date):
                    result = FileSystemProtocol.call_store(
                        conn, n, node, value, metadata, key_name, local_last_write
                    )
                    if result:
                        if do_confirmation:
                            r = FileSystemProtocol.call_confirm_integrity(
                                conn, n, node, metadata
                            )
                            responses.append(r)
                        else:
                            responses.append(True)
                    else:
                        responses.append(False)
                else:
                    if response:
                        responses.append(True)
        # return true only if at least one store call succeeded
        return any(responses)

    @staticmethod
    def _handle_empty_neighbors(
        dkey, metadata, value, exclude_current, local_last_write, key_name
    ):
        logger.debug("There are no known neighbors to set key %s", dkey.hex())
        contains, date = Server.storage.check_if_new_value_exists(dkey, metadata)
        if not exclude_current and it_is_necessary_to_write(
            local_last_write, contains, date
        ):
            logger.info("storing in current server")
            if metadata:
                Server.storage.set_metadata(
                    dkey, value, False, key_name=key_name, last_write=local_last_write
                )
            else:
                Server.storage.set_value(
                    dkey, value, False, last_write=local_last_write
                )
        return True

    @staticmethod
    def delete_data_from_network(key: bytes, is_metadata=True):
        node = Node(key)
        nearest = FileSystemProtocol.router.find_neighbors(node)
        if not nearest or len(nearest) == 0:
            logger.debug(f"There are no known neighbors to get key {key}")
            if Server.storage.contains(key):
                logger.debug("Getting key from this same node")
                return Server.storage.delete(key, True)
            return True

        spider = DeleteSpiderCrawl(node, nearest, Server.ksize, Server.alpha)
        result = spider.find(is_metadata)
        logger.info(f"result of spider in delete was {result}")
        if result is not True:
            logger.warning("value was not deleted correctly")
        return result

    @staticmethod
    def confirm_integrity_of_data(key: bytes, is_metadata=True):
        node = Node(key)
        nearest = FileSystemProtocol.router.find_neighbors(node)

        if isinstance(nearest, list) and len(nearest) == 0:
            Server.storage.confirm_integrity(key, is_metadata)
            return True

        spider = ConfirmIntegritySpiderCrawl(node, nearest, Server.ksize, Server.alpha)
        result = spider.find(is_metadata)
        return result

    @staticmethod
    def find_replicas():
        keys_to_find = Server.storage.keys()
        keys_dict = {}
        for k, is_metadata in keys_to_find:
            node_created = Node(k)

            nearest = FileSystemProtocol.router.find_neighbors(
                node_created, 2 * Server.ksize
            )
            logger.error("Nearest in find replicas %s", nearest)
            spider = NodeSpiderCrawl(
                node_created, nearest, 2 * Server.ksize, Server.alpha
            )

            nodes = spider.find()

            logger.error("nodes %s", nodes)

            for n in nodes:
                with ServerSession(n.ip, n.port) as conn:
                    # logger.critical("looking for key %s in %s", k, n)
                    contains = FileSystemProtocol.call_contains(
                        conn, n, node_created, is_metadata
                    )
                    if contains:
                        # logger.critical("Found")
                        if (k, is_metadata) not in keys_dict:
                            keys_dict[(k, is_metadata)] = []
                        keys_dict[(k, is_metadata)].append(n)

        return_list = []
        delete_list = []
        logger.info("IDSSSSSS %s", keys_dict)
        for k, values in keys_dict.items():
            if len(keys_dict[k]) < Server.ksize:
                logger.critical(
                    "\n\n\n key %s len %s ksize %s", k, len(values), Server.ksize
                )
                return_list.append(k)
            elif len(keys_dict[k]) > Server.ksize:
                logger.critical("\n\n\n key %s replicas %s", k, len(values))
                delete_list.append((k, list(set(values))))

        for key, item in delete_list:
            key, is_metadata = key

            node = Node(key)
            sorted_list = sorted(item, key=node.distance_to)
            logger.info("ITEMS %s", sorted_list)

            if str(sorted_list[0].ip) == str(Server.node.ip) and str(
                sorted_list[0].port
            ) == str(Server.node.port):
                for node in sorted_list[Server.ksize :]:
                    logger.info("To many replicas of %s, removing on %s", key, node)
                    if node.ip == Server.node.ip and node.port == Server.node.port:
                        continue

                    with ServerSession(node.ip, node.port) as conn:
                        delete = FileSystemProtocol.call_delete(
                            conn, node, Node(key), is_metadata=is_metadata
                        )
                        if not delete:
                            logger.warning("Failed to delete replica")
        return return_list

    @staticmethod
    def _detect_alone():
        while True:
            try:
                node = Node(digest("test"))
                assert node is not None
                nearest = FileSystemProtocol.router.find_neighbors(node)
            except Exception as e:
                logger.error(f"Exception throwed in _detect_alone: {e}")
                sleep(15)
                continue
            if nearest is not None and len(nearest) > 0:
                # logger.info(f"nearest in _detect_alone is {nearest}")
                sleep(15)
                continue
            else:
                ms = MessageSystem()
                hosts = []

                while True:
                    try:
                        msg = ms.receive(service_name="dfs")
                    except OSError as e:
                        msg = None
                        logger.debug(f"Error in broadcasting new neighbors: {e}")
                    if (
                        msg is None
                        or not Server.node.ip + " " + str(Server.node.port) in msg
                    ):
                        break
                    sleep(16)

                logger.debug(msg)
                if msg:
                    bootstrap_nodes = msg
                    logger.debug(f"Found {msg}")
                    if bootstrap_nodes:
                        target_host, target_port = bootstrap_nodes.split(" ")
                        Server.bootstrap([(target_host, target_port)])

    @staticmethod
    def _refresh_table(refresh_sleep=60):
        while True:
            sleep(refresh_sleep)
            try:
                logger.info("Checking corrupted data")
                Server.storage.delete_corrupted_data()
                logger.info("Refreshing table")
                results = []
                for node_id in FileSystemProtocol.get_refresh_ids():
                    node = Node(node_id)
                    nearest = FileSystemProtocol.router.find_neighbors(node)
                    spider = NodeSpiderCrawl(node, nearest, Server.ksize, Server.alpha)

                    results.append(spider.find())

                # Republishing keys to mantain the network updated

                logger.info("Republishing old keys")
                for (
                    key,
                    value,
                    is_metadata,
                    last_write,
                    key_name,
                ) in Server.storage.iter_older_than(refresh_sleep):
                    digest_response = Server.set_digest(
                        key,
                        value,
                        is_metadata,
                        exclude_current=True,
                        local_last_write=last_write,
                        key_name=key_name,
                        do_confirmation=True,
                    )
                    if not digest_response:
                        logger.warning("Failed set_digest in iter_older than")

                    Server.storage.update_republish(key)
            
            except Exception as e:
                logger.error("Thrown Exception %s in republish old keys", str(e))
                pass
            
            logger.info("Deleting extra replicas")
            keys_to_replicate = Server.find_replicas()

            try:
                logger.info(
                    "Republishing keys that have less replicas than the replication factor"
                )

                if len(keys_to_replicate) > 0:
                    for key, is_metadata in keys_to_replicate:
                        _, local_last_write = Server.storage.check_if_new_value_exists(
                            key, is_metadata
                        )
                        logger.info("replicating key %s", key)
                        # check for value4 lock
                        response = Server.set_digest(
                            key,
                            Server.storage.get(
                                key, metadata=is_metadata, update_timestamp=False
                            ),
                            is_metadata,
                            exclude_current=True,
                            local_last_write=local_last_write,
                            key_name=Server.storage.get_key_name(
                                key, metadata=is_metadata, update_timestamp=False
                            ),
                            do_confirmation=True,
                        )
                        if not response:
                            logger.warning("Failed set keys_to_replicate in refresh")
                logger.info("Finishied replication")
            except Exception as e:
                logger.error("Thrown Exception %s in republish under replicated data", str(e))
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
    def get(self, key):
        """
        Get a key if the network has it.

        Returns:
            :class:`None` if not found, the value otherwise.
        """

        logger.debug(f"Looking up key {key}")

        dkey = digest(key)

        node = Node(dkey)
        nearest = FileSystemProtocol.router.find_neighbors(node)
        if not nearest or len(nearest) == 0:
            logger.debug(f"There are no known neighbors to get key {dkey}")
            if Server.storage.contains(dkey):
                logger.debug("Getting key from this same node")
                data = Server.storage.get(dkey, True)
                if data is None:
                    return None
                return pickle.loads(data)
            return None
        spider = ValueSpiderCrawl(node, nearest, Server.ksize, Server.alpha)
        data = spider.find()
        if data is None:
            logger.debug("NONE DATA")
            return None
        logger.debug(f"DATA {data}")
        try:
            metadata_list = pickle.loads(data)
        except pickle.UnpicklingError as e:
            logger.error(f"exception when returning metadata_list {e}")
            return None
        return metadata_list

    @rpyc.exposed
    def delete(self, key, is_metadata=True):
        key = digest(key)

        return Server.storage.delete(
            key, is_metadata
        ) and Server.delete_data_from_network(key, is_metadata)

    @rpyc.exposed
    def upload_file(self, key_name: str, key: str, data: bytes) -> bool:
        chunks = Server.split_data(data, 500)
        logger.debug(f"chunks {len(chunks)}, {chunks}")
        digested_chunks = [digest(c) for c in chunks]
        metadata_list = pickle.dumps(digested_chunks)
        processed_chunks = list((digest(c), c) for c in chunks)

        chunks_responses = []
        for c in processed_chunks:
            chunks_responses.append(Server.set_digest(c[0], c[1], metadata=False))

        if not all(chunks_responses):
            logger.info("Failed to set chunks, rolling back changes")
            responses = []
            for c in processed_chunks:
                responses.append(
                    Server.delete_data_from_network(key=c[0], is_metadata=False)
                )
            if not all(responses):
                logger.warning("Rolling back changes of chuncks was not completed")

        logger.info("Writting key metadata")

        dkey = digest(key)

        set_metadata_response = Server.set_digest(
            dkey, metadata_list, key_name=key_name
        )

        if not set_metadata_response:
            logger.warning("Failed set_digest of metadata, rolling back changes")
            responses = []
            for c in processed_chunks:
                responses.append(
                    Server.delete_data_from_network(key=c[0], is_metadata=False)
                )
            if not all(responses):
                logger.warning(
                    "Rolling back changes of chuncks with failed metadata was not completed"
                )
            return False

        results = []
        logger.critical("len pocessed chunks %d", len(list(processed_chunks)))
        for c in list(processed_chunks):
            logger.critical("confiming %s", c[0])
            results.append(Server.confirm_integrity_of_data(c[0], False))

        if not all(results):
            logger.warning("It was not possible to confirm integrity of all chunks")
            return False

        logger.info(f"Here key of metadata is {dkey}")
        result = Server.confirm_integrity_of_data(dkey, True)
        if not result:
            logger.warning("It was not possible to confirm integrity of metadata")

        logger.info("File uploaded successfully")
        return True

    @rpyc.exposed
    def get_all_file_names(self):
        logging.info("Getting all file names")
        nearest = FileSystemProtocol.router.find_neighbors(Server.node)
        initial_metadata = Server.storage.get_all_metadata_keys()
        spider = LsSpiderCrawl(Server.node, nearest, Server.ksize, Server.alpha)
        metadata_list = spider.find()
        logger.info(f"Metadata list in ls is {metadata_list}")
        if metadata_list is None:
            return list(initial_metadata)
        return list(metadata_list.union(initial_metadata))

    @rpyc.exposed
    def get_file_chunk_location(self, chunk_key):
        logger.info("looking file chunk location")
        node = Node(chunk_key)
        nearest = FileSystemProtocol.router.find_neighbors(node)
        if not nearest:
            logger.info(
                f"There are no known neighbors to get file chunk location {chunk_key}"
            )
            if Server.storage.contains(chunk_key, False) is not None:
                logger.info(
                    f"Found in this server, {Server.node.ip}, port, {Server.node.port}"
                )
                return [(Server.node.ip, Server.node.port)]
            return None

        logger.info("Initiating ChunkLocationSpiderCrawl")
        spider = ChunkLocationSpiderCrawl(node, nearest, Server.ksize, Server.alpha)
        results = spider.find()
        logger.info(f"results of ChunkLocationSpider {results}")
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
            logger.critical("find node contains 1")
            return {"value": (Server.node.ip, Server.node.port)}
        return self.rpc_find_node(sender, nodeid, key)

    @rpyc.exposed
    def find_neighbors(self):
        nearest = FileSystemProtocol.router.find_neighbors(
            Server.node, exclude=Server.node
        )
        return [(i.ip, i.port) for i in nearest]

    ############################################################################
    #                   RPCs only accessed by servers                          #
    ############################################################################

    @rpyc.exposed
    def rpc_store(
        self,
        sender,
        nodeid: bytes,
        key: bytes,
        value,
        metadata=True,
        key_name="NOT DEFINED",
        local_last_write=None,
    ):
        logger.debug("Entry in rpc_store")
        source = Node(nodeid, sender[0], sender[1])
        # if a new node is sending the request, give all data it should contain

        address = (source.ip, source.port)
        with ServerSession(address[0], address[1]) as conn:
            # logger.info(f"wellcome_If_new in rpc_store {address}")
            FileSystemProtocol.wellcome_if_new(conn, source)

        logger.debug(
            f"got a store request from %s, storing '%s'='%s' {sender}, {key}, {value}"
        )
        # store values and report success
        if metadata:
            Server.storage.set_metadata(
                key,
                value,
                republish_data=False,
                key_name=key_name,
                last_write=local_last_write,
            )
        else:
            Server.storage.set_value(
                key, value, metadata=False, last_write=local_last_write
            )
        return True

    @rpyc.exposed
    def rpc_find_value(
        self, sender: tuple[str, str], nodeid: bytes, key: bytes, metadata=True
    ):
        source = Node(nodeid, sender[0], sender[1])
        # if a new node is sending the request, give all data it should contain
        address = (source.ip, source.port)
        with ServerSession(address[0], address[1]) as conn:
            # logger.info(f"wellcome_If_new in find_value {address}")
            FileSystemProtocol.wellcome_if_new(conn, source)
        # get value from storage
        if not FileSystemProtocol.storage.contains(key, metadata):
            logger.debug(f"Value with key {key} not found, calling rpc_find_node")
            logger.debug(f"type of key is {type(key)}")

            return self.rpc_find_node(sender, nodeid, key)

        value = FileSystemProtocol.storage.get(key, metadata=metadata)
        logger.debug(f"returning value {value}")
        return {"value": value}

    @rpyc.exposed
    def rpc_ping(self, sender, nodeid: bytes, remote_id):
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
            logger.info(f"wellcome_If_new in ping {address}")
            FileSystemProtocol.wellcome_if_new(conn, source)
        logger.debug("return ping")
        if remote_id is not None and remote_id != FileSystemProtocol.source_node.id:
            return None
        return FileSystemProtocol.source_node.id

    @rpyc.exposed
    def rpc_find_node(self, sender, nodeid: bytes, key: bytes):
        logger.debug(f"finding neighbors of {int(nodeid.hex(), 16)} in local table")

        source = Node(nodeid, sender[0], sender[1])

        logger.debug(f"node id {nodeid}")
        # if a new node is sending the request, give all data it should contain
        address = (source.ip, source.port)
        with ServerSession(address[0], address[1]) as conn:
            # logger.info(f"wellcome_If_new in find_node {address}")
            FileSystemProtocol.wellcome_if_new(conn, source)
        # create a fictional node to perform the search
        logger.debug(f"fictional key {key}")
        logger.debug(f"SEnder [0] Sender [1] {source.ip}, {source.port}")
        node = Node(key)
        # ask for the neighbors of the node
        neighbors = FileSystemProtocol.router.find_neighbors(node, exclude=source)
        logger.debug(f"neighbors of find_node: { neighbors}")
        return list(map(tuple, neighbors))

    @rpyc.exposed
    def rpc_contains(self, sender, nodeid: bytes, key: bytes, is_metadata=True):
        source = Node(nodeid, sender[0], sender[1])
        # if a new node is sending the request, givemsg all data it should contain
        address = (source.ip, source.port)
        with ServerSession(address[0], address[1]) as conn:
            # logger.info(f"wellcome_If_new in contains {address}")
            FileSystemProtocol.wellcome_if_new(conn, source)
        # get value from storage
        return {"value": FileSystemProtocol.storage.contains(key, is_metadata)}

    @rpyc.exposed
    def rpc_check_if_new_value_exists(
        self, sender, nodeid: bytes, key: bytes, is_metadata=True
    ):
        source = Node(nodeid, sender[0], sender[1])
        # if a new node is sending the request, give all data it should contain
        address = (source.ip, source.port)
        with ServerSession(address[0], address[1]) as conn:
            # logger.info(f"wellcome_If_new in check_if_new_value {address}")
            FileSystemProtocol.wellcome_if_new(conn, source)
        # get value from storage
        return FileSystemProtocol.storage.check_if_new_value_exists(key, is_metadata)

    @rpyc.exposed
    def rpc_delete(self, sender, node_id: bytes, key: bytes, is_metadata: bool):
        source = Node(node_id, sender[0], sender[1])
        address = (source.ip, source.port)
        with ServerSession(address[0], address[1]) as conn:
            # logger.info(f"wellcome_If_new in rpc_delete {address}")
            FileSystemProtocol.wellcome_if_new(conn, source)

        return {"value": FileSystemProtocol.storage.delete(key, is_metadata)}

    @rpyc.exposed
    def rpc_confirm_integrity(
        self, sender, node_id: bytes, key: bytes, is_metadata: bool
    ):
        source = Node(node_id, sender[0], sender[1])
        address = (source.ip, source.port)
        with ServerSession(address[0], address[1]) as conn:
            # logger.info(f"wellcome_If_new in rpc_confirm_integrity {address}")
            FileSystemProtocol.wellcome_if_new(conn, source)

        try:
            logging.info(f"Trying to confirm integrity with key {key}")
            FileSystemProtocol.storage.confirm_integrity(key, is_metadata)
            return {"value": True}
        except Exception as e:
            logger.error(f"Error when doing rpc_confirm_integrity, {e}")
            return {"value": False}

    @rpyc.exposed
    def rpc_get_metadata_list(self, sender, node_id: bytes):
        source = Node(node_id, sender[0], sender[1])
        address = (source.ip, source.port)
        with ServerSession(address[0], address[1]) as conn:
            # logger.info(f"wellcome_If_new in rpc_confirm_integrity {address}")
            FileSystemProtocol.wellcome_if_new(conn, source)

        return {"value": Server.storage.get_all_metadata_keys()}

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
