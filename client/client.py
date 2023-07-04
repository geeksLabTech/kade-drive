
import pickle
import rpyc
from time import sleep
from rpyc.core.protocol import PingError
from message_system.message_system import Message_System

import logging

# rpyc.core.protocol.DEFAULT_CONFIG['allow_pickle'] = True


class ClientSession:
    """
    Class to handle connection to the distributed file system
    It is necessary to run ensure_connection or broadcast method before
    accessing to the other functionality
    """

    def __init__(self, bootstrap_nodes: list[tuple[str, int]]) -> None:
        self.connection: rpyc.Connection | None = None
        self.bootstrap_nodes: list[tuple[str, int]] = bootstrap_nodes

    def connect(self, time_to_reconnect=5, use_broadcast_if_needed: bool = False, update_boostrap_nodes: bool = True,  attempts_to_reconnect=2):
        self.connection, self.bootstrap_nodes = self._ensure_connection(
            self.bootstrap_nodes, self.connection, time_to_reconnect, use_broadcast_if_needed, update_boostrap_nodes, attempts_to_reconnect)
        return self.connection is not None

    def _ensure_connection(self, nodes_to_try: list[tuple[str, int]], connection: rpyc.Connection | None, time_to_reconnect=5, use_broadcast_if_needed: bool = False, update_boostrap_nodes: bool = True, attempts_to_reconnect=2) -> tuple[rpyc.Connection | None, list[tuple[str, int]]]:
        remaining_attempts_to_reconnect = attempts_to_reconnect
        while not connection or len(nodes_to_try) > 0 or use_broadcast_if_needed:
            if len(nodes_to_try) == 0 and use_broadcast_if_needed:
                print("Unable to connect to any server known server")
                if not self.broadcast():
                    break

            ip, port = nodes_to_try[0]
            try:
                if connection:
                    connection.ping()
                    break
                connection = rpyc.connect(ip, port, keepalive=True, config={
                                          'allow_pickle': True})
                print(f"Connected to {ip}:{port}")
                break
            except (PingError, EOFError) as e:
                connection = None
                nodes_to_try, remaining_attempts_to_reconnect = self._reconnect(
                    nodes_to_try, ip, e, time_to_reconnect, remaining_attempts_to_reconnect, attempts_to_reconnect)
            except (ConnectionRefusedError, ConnectionResetError, ConnectionError, ) as e:
                nodes_to_try, remaining_attempts_to_reconnect = self._reconnect(
                    nodes_to_try, ip, e, time_to_reconnect, remaining_attempts_to_reconnect, attempts_to_reconnect)

        if connection and update_boostrap_nodes:
            self._update_bootstrap_nodes(connection)
        if not connection:
            print("Unable to connect to any server known server")
        return connection, nodes_to_try

    def _reconnect(self, nodes_to_try: list[tuple[str, int]], ip: str, e: Exception, time_to_reconnect: int, remaining_attempts_to_reconnect: int, total_attempts_to_reconnect: int) -> tuple[list[tuple[str, int]], int]:
        print(f"Connection to {ip} failed by {e}.")
        if remaining_attempts_to_reconnect > 0:
            remaining_attempts_to_reconnect -= 1
            print(
                f"Trying to reconnect to {ip} in {time_to_reconnect} seconds... attempts left: {remaining_attempts_to_reconnect}")
            sleep(time_to_reconnect)
        else:
            print(
                f"Connection to {ip} failed, removing from bootstrap nodes list.")
            nodes_to_try.pop(0)
            return nodes_to_try, total_attempts_to_reconnect

        return nodes_to_try, remaining_attempts_to_reconnect

    def get(self, key):
        metadata_list = self.connection.root.get(key)
        logger = logging.getLogger(__name__)

        logger.debug(f'metadata_list received {str(len(metadata_list) > 0)}')
        data_received = []
        for chunk_key in metadata_list:
            # print('chunk key', chunk_key)
            locations: list[tuple[str, int]] = self.connection.root.get_file_chunk_location(
                chunk_key)
            logger.debug(
                f'locations for chunk_key {chunk_key} are {locations}')
            if self.bootstrap_nodes[0] in locations:
                logger.debug('Using primary connection to get chunk')
                data_received.append(
                    self.connection.root.get_file_chunk_value(chunk_key))
            else:
                conn = self._ensure_connection(
                    locations, None, use_broadcast_if_needed=False, update_boostrap_nodes=False)
                if conn:
                    data_received.append(
                        conn.root.get_file_chunk_value(chunk_key))
                else:
                    logger.warning('No Servers to get chunk')

        # data_recv = bytearray()
        logger.debug('len data received', len(data_received))
        data_received = b''.join(data_received)
        return pickle.loads(data_received)

    def put(self, key, value: bytes, apply_hash_to_key=True):
        logger = logging.getLogger(__name__)

        logger.debug(f'key: {key}, value: {value}')
        # print(self.connection.root.upload_file.)
        self.connection.root.upload_file(key=key, data=value, apply_hash_to_key=apply_hash_to_key)
        sleep(1)
        logger.info(f'put > Success')

    def _update_bootstrap_nodes(self, connection: rpyc.Connection):
        logger = logging.getLogger(__name__)

        nodes_to_add = [node for node in connection.root.find_neighbors(
        ) if node not in self.bootstrap_nodes]
        self.bootstrap_nodes.extend(nodes_to_add)
        logger.debug(f'Neighbors {self.bootstrap_nodes}')

    def broadcast(self) -> bool:
        print('Listening broadcasts')
        ms = Message_System()
        try:
            ip, port = ms.receive().split(" ")
        except ValueError:
            ip = None
            port = None
        if ip:
            self.bootstrap_nodes.append((ip, int(port)))
            return True

        print('No broadcasts received.')
        return False


