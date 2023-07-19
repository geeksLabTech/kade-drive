import pickle
import rpyc
from time import sleep
from rpyc.core.protocol import PingError
from message_system.message_system import MessageSystem

import logging

try:
    logger = logging.getLogger(__name__)
except:
    pass


class ClientSession:
    """
    Class to handle connection to the distributed file system
    It is necessary to run ensure_connection or broadcast method before
    accessing to the other functionality
    """

    def __init__(
        self, bootstrap_nodes: list[tuple[str, int]], log_level=logging.DEBUG
    ) -> None:
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s",
        )
        logging.getLogger(__name__)
        self.connection: rpyc.Connection | None = None
        self.bootstrap_nodes: list[tuple[str, int]] = bootstrap_nodes

    def connect(
        self,
        time_to_reconnect=5,
        use_broadcast_if_needed: bool = False,
        update_boostrap_nodes: bool = True,
        attempts_to_reconnect=2,
    ) -> bool:
        self.connection, self.bootstrap_nodes = self._ensure_connection(
            self.bootstrap_nodes,
            self.connection,
            time_to_reconnect,
            use_broadcast_if_needed,
            update_boostrap_nodes,
            attempts_to_reconnect,
        )
        return self.connection is not None

    def _ensure_connection(
        self,
        nodes_to_try: list[tuple[str, int]],
        connection: rpyc.Connection | None,
        time_to_reconnect=5,
        use_broadcast_if_needed: bool = False,
        update_boostrap_nodes: bool = True,
        attempts_to_reconnect=2,
    ) -> tuple[rpyc.Connection | None, list[tuple[str, int]]]:
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
                connection = rpyc.connect(
                    ip,
                    port,
                    keepalive=True,
                    config={"allow_pickle": True, "sync_request_timeout": None},
                )
                print(f"Connected to {ip}:{port}")
                break
            except (PingError, EOFError) as e:
                connection = None
                nodes_to_try, remaining_attempts_to_reconnect = self._reconnect(
                    nodes_to_try,
                    ip,
                    e,
                    time_to_reconnect,
                    remaining_attempts_to_reconnect,
                    attempts_to_reconnect,
                )
            except (
                ConnectionRefusedError,
                ConnectionResetError,
                ConnectionError,
            ) as e:
                nodes_to_try, remaining_attempts_to_reconnect = self._reconnect(
                    nodes_to_try,
                    ip,
                    e,
                    time_to_reconnect,
                    remaining_attempts_to_reconnect,
                    attempts_to_reconnect,
                )

        if connection and update_boostrap_nodes:
            self._update_bootstrap_nodes(connection)
        if not connection:
            print("Unable to connect to any server known server")
        return connection, nodes_to_try

    def _reconnect(
        self,
        nodes_to_try: list[tuple[str, int]],
        ip: str,
        e: Exception,
        time_to_reconnect: int,
        remaining_attempts_to_reconnect: int,
        total_attempts_to_reconnect: int,
    ) -> tuple[list[tuple[str, int]], int]:
        print(f"Connection to {ip} failed by {e}.")
        if remaining_attempts_to_reconnect > 0:
            remaining_attempts_to_reconnect -= 1
            print(
                f"Trying to reconnect to {ip} in {time_to_reconnect} seconds... attempts left: {remaining_attempts_to_reconnect}"
            )
            sleep(time_to_reconnect)
        else:
            print(f"Connection to {ip} failed, removing from bootstrap nodes list.")
            nodes_to_try.pop(0)
            return nodes_to_try, total_attempts_to_reconnect

        return nodes_to_try, remaining_attempts_to_reconnect

    def get(self, key) -> tuple:
        if not self.connection:
            logger.error("No connection stablished to do get")
            return None, None

        try:
            metadata_list = self.connection.root.get(key)
        except EOFError as e:
            logger.error(f"Connection lost in get when doing get rpc, exception: {e}")
            return None, None
        logger.debug(f"METADATAAAAA {metadata_list}")
        if metadata_list:
            logger.debug(f"metadata_list received {str(len(metadata_list) > 0)}")
        data_received = []

        if metadata_list is None or len(metadata_list) == 0:
            logger.debug(f"No data with key {key}")
            return None, self.connection

        for chunk_key in metadata_list:
            try:
                locations: list[
                    tuple[str, int]
                ] = self.connection.root.get_file_chunk_location(chunk_key)
            except EOFError as e:
                logger.error(
                    f"Connection lost in get when doing get_file_chunk_location, exception: {e}"
                )
                return None, None

            if locations is None:
                continue

            logger.info(f"locations for chunk_key {chunk_key} are {locations}")

            if len(locations) > 0:
                while len(locations) > 0:
                    conn, locations = self._ensure_connection(
                        locations,
                        None,
                        use_broadcast_if_needed=False,
                        update_boostrap_nodes=False,
                    )
                    if conn:
                        try:
                            data_to_add = conn.root.rpc_get_file_chunk_value(chunk_key)
                            if data_to_add is None:
                                locations.pop(0)
                                continue
                            data_received.append(data_to_add)
                            break
                        except EOFError as e:
                            logger.error(
                                f"Connection lost in get when doing rpc_get_file_chunk_value, exception: {e}"
                            )

                            continue
            elif len(locations) == 0:
                logger.warning("No Servers to get chunk")
                break

        logger.debug(f"len data received {len(data_received)} {type(data_received)}")
        if len(data_received) == 0:
            logger.error("len of data_received is 0")
            return None, self.connection
        data_received = b"".join(data_received)
        try:
            data_to_return = pickle.loads(data_received)
            return data_to_return, self.connection
        except pickle.UnpicklingError as e:
            logger.error(e)
            return None, self.connection

    def put(self, key, value: bytes) -> tuple:
        if self.connection:
            try:
                response = self.connection.root.upload_file(
                    key_name=key, key=key, data=value
                )
                sleep(1)
                message = "put > Success" if response else "put failed"
                logger.info(message)
                return response, self.connection
            except EOFError as e:
                logger.error(f"Connection lost in put, exception: {e}")

        else:
            logger.error("No connection stablished to do put")

        return False, None

    def delete(self, key):
        if self.connection:
            try:
                response = self.connection.root.delete(key=key)
                sleep(1)
                message = "Delete > Success" if response else "Delete failed"
                logger.info(message)
                return response, self.connection
            except EOFError as e:
                logger.error(f"Connection lost in delete, exception: {e}")

        else:
            logger.error("No connection stablished to do Delete")

        return False, None

    def ls(self):
        if self.connection:
            try:
                response = self.connection.root.get_all_file_names()
                sleep(1)
                message = "ls > Success" if response else "ls failed"
                logger.info(message)
                return response, self.connection
            except EOFError as e:
                logger.error(f"Connection lost in ls, exception: {e}")

        else:
            logger.error("No connection stablished to do Delete")

        return False, None

    def _update_bootstrap_nodes(self, connection: rpyc.Connection):
        try:
            nodes_to_add = [
                node
                for node in connection.root.find_neighbors()
                if node not in self.bootstrap_nodes
            ]
            self.bootstrap_nodes.extend(nodes_to_add)
            logger.debug(f"Neighbors {self.bootstrap_nodes}")
        except EOFError as e:
            logger.error(f"Connection lost in _update_bootstrap_nodes, exception: {e}")

    def broadcast(self) -> bool:
        print("Listening broadcasts")
        ms = MessageSystem()
        try:
            ip, port = ms.receive(service_name="dfs").split(" ")
            print(ip, port)
        except ValueError:
            ip = None
            port = None
        if ip:
            self.bootstrap_nodes.append((ip, int(port)))
            return True

        print("No broadcasts received.")
        return False
