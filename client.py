
import pickle
import socket
import rpyc
import sys
from time import sleep
from rpyc.core.protocol import PingError
from message_system.message_system import Message_System

# rpyc.core.protocol.DEFAULT_CONFIG['allow_pickle'] = True

class ClientSession:
    """
    Class to handle connection to the distributed file system
    It is necessary to run ensure_connection or broadcast method before
    accessing to the other functionality
    """

    def __init__(self, bootstrap_nodes: list[tuple[str, int]], attempts_to_reconnect=2) -> None:
        self.connection: rpyc.Connection | None = None
        self.bootstrap_nodes: list[tuple[str, int]] = bootstrap_nodes
        self.total_attempts_to_reconnect = attempts_to_reconnect
        self.current_attempts_to_reconnect = attempts_to_reconnect

    def ensure_connection(self, time_to_reconnect=5, use_broadcast_if_needed: bool = False, update_boostrap_nodes: bool = True) -> bool:
        was_successful = False
        while not was_successful or len(self.bootstrap_nodes) > 0 or use_broadcast_if_needed:
            if len(self.bootstrap_nodes) == 0 and use_broadcast_if_needed:
                print("Unable to connect to any server known server")
                if not self.broadcast():
                    was_successful = False
                    break

            ip, port = self.bootstrap_nodes[0]
            try:
                if self.connection:
                    self.connection.ping()
                    was_successful = True
                    break
                self.connection = rpyc.connect(ip, port, keepalive=True, config = {'allow_pickle': True})
                print(f"Connected to {ip}:{port}")
                was_successful = True
                break
            except (PingError, EOFError) as e:
                self.connection = None
                self._reconnect(ip, e, time_to_reconnect)
            except (ConnectionRefusedError, ConnectionResetError, ConnectionError, ) as e:
                self._reconnect(ip, e, time_to_reconnect)

        if was_successful and update_boostrap_nodes:
            self._update_bootstrap_nodes()
        if not was_successful:
            print("Unable to connect to any server known server")
        return was_successful

    def _reconnect(self, ip: str, e: Exception, time_to_reconnect: int):
        print(f"Connection to {ip} failed by {e}.")
        if self.current_attempts_to_reconnect > 0:
            self.current_attempts_to_reconnect -= 1
            print(
                f"Trying to reconnect to {ip} in {time_to_reconnect} seconds... attempts left: {self.current_attempts_to_reconnect}")
            sleep(time_to_reconnect)
        else:
            print(
                f"Connection to {ip} failed, removing from bootstrap nodes list.")
            self.bootstrap_nodes.pop(0)
            self.attempts_to_reconnect = self.total_attempts_to_reconnect

    def get(self, key):
        metadata_list = self.connection.root.get(key)
        data_received = []
        for chunk_key in metadata_list:
            print('chunk key', chunk_key)
            location = self.connection.root.get_file_chunk_location(chunk_key)[0]
                
            print('sali de location', location, self.bootstrap_nodes[0])
            if location == self.bootstrap_nodes[0]:
                print('entro misma conexion')
                data_received.append(self.connection.root.get_file_chunk_value(chunk_key))
            else:
                print('noooo')
                with rpyc.connect(location[0], location[1]) as conn:
                    data_received.append(conn.root.get_file_chunk_value(chunk_key))

        # data_recv = bytearray()
        print('len data received', len(data_received))
        data_received = b''.join(data_received)
        return pickle.loads(data_received)

    def put(self, key, value):
        print(f'key: {key}, value: {value}')
        # print(self.connection.root.upload_file.)
        self.connection.root.upload_file(key=key, data=value)
        print(f'value putted')
    
    def _update_bootstrap_nodes(self):
        nodes_to_add = [node for node in self.connection.root.find_neighbors(
        ) if node not in self.bootstrap_nodes]
        self.bootstrap_nodes.extend(nodes_to_add)
        print(' neidieom', self.bootstrap_nodes)

    def broadcast(self) -> bool:
        print('Initiating broadcast')
        ms = Message_System()
        ip, port = ms.receive().split(" ")

        if ip:
            self.bootstrap_nodes.append((ip, int(port)))
            return True

        print('Broadcast was not able to find any server.')
        return False


client_session: ClientSession | None = None


if __name__ == "__main__":
    ip = None
    port = 8086
    if len(sys.argv) < 2:
        print('Initiating client with local ip and default port')

    if len(sys.argv) == 2:
        ip = sys.argv[1]

    if len(sys.argv) == 3:
        ip, port = sys.argv[1], sys.argv[2]

    initial_bootstrap_nodes = [(ip, int(port))] if ip else []
    client_session = ClientSession(initial_bootstrap_nodes)

    print('Client shell started')
    while True:
        command = input('Expecting command: ').split(' ')
        if command[0] == 'exit':
            break

        response = client_session.ensure_connection(
            use_broadcast_if_needed=True)
        if not response:
            break

        args = command[1:] if len(command) >= 1 else []
        func = getattr(ClientSession, command[0], None)
        if func is None or not callable(func):
            print('not finded command with that name')
            continue
        print(f'calling {func} with arguments: {args}')
        print()
        result = func(client_session, *args)
        if result:
            print(f'Result is: {result}')
        else:
            print(f'command returned None')
