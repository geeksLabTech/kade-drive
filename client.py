
import socket
import rpyc
import sys
from time import sleep
from message_system.message_system import Message_System


class ClientSession:
    def __init__(self, ip: str | None = None, port: int = 8086) -> None:
        self.ip = ip if ip is not None else socket.gethostbyname(
            socket.gethostname())
        self.port = port
        self.connection: rpyc.Connection | None = None
        self.neighbors = []

    def connect(self, ip: str | None, port: int = 8086):
        ip = ip if ip is not None else socket.gethostbyname(
            socket.gethostname())
        self.connection = rpyc.connect(ip, port, keepalive=True)
        # assert self.connection is not None and self.connection.root is not None
        # print(self.connection.root.__dict__)

    def get(self, key):
        result = self.connection.root.get(key)
        return result

    def put(self, key, value):
        print(f'key: {key}, value: {value}')
        self.connection.root.set_key(key, value)
        print(f'value putted')

    def _find_neighbors(self):

        self.neighbors.extend(self.connection.root.find_neighbors())
        print('a ver', type(self.neighbors))
        print(' neidieom', self.neighbors)

    def _reconnect(self):
        sleep(5)
        try:
            self.connect(self.ip, self.port)
            return
        # except Exception as e:
        #     print(f'Exception: {e}')
        except:
            print('no pudo')
            pass
        # neighbors = self._find_neighbors()
        print('tengo', self.neighbors)
        while len(self.neighbors) > 1:
            self.neighbors.pop(0)

            try:
                self.connect(self.neighbors[0][0], self.neighbors[0][1])
                sleep(5)
                self.connect(self.neighbors[0][0], self.neighbors[0][1])
                print('nuevos', self.neighbors)
                return
            except Exception as e:
                # print(f'Exception: {e}')
                continue


client_session: ClientSession | None = None


def create_session(ip, port=8086):
    client_session = ClientSession(ip, int(port))

    # assert client_session is not None
    print('Connecting client to server')
    try:
        client_session.connect(ip, int(port))
        client_session.neighbors.append((ip, int(port)))
        neighbors = client_session._find_neighbors()
        print('Client shell started')
        while True:
            command = input('Expecting command: ').split(' ')
            if command[0] == 'exit':
                break

            args = command[1:] if len(command) >= 1 else []
            func = getattr(ClientSession, command[0], None)
            if func is None or not callable(func):
                print(f'command {func} not found')
                continue
            print(f'calling {func} with arguments: {args}')
            print()

            try:
                result = func(client_session, *args)
                if result:
                    print(f'> {result}')
                else:
                    print(f'> None')
            except Exception as e:
                print(f'Exception: {e}')
                # neighbors = client_session._find_neighbors()
                client_session._reconnect()

                if not client_session.connection is None:
                    result = func(client_session, *args)
                    if result:
                        print(f'> {result}')
                    else:
                        print(f'> None')
    except Exception as e:
        ms = Message_System()
        ip = ms.receive()
        if ip:
            create_session(ip)
        else:
            print('The client was unable to reconnect to any server.')


if __name__ == "__main__":
    ip = None
    # port = 8086

    if len(sys.argv) < 2:
        print('Initiating client with local ip and default port')
        ip = socket.gethostbyname(socket.gethostname())
        # client_session = ClientSession(ip=ip)
        create_session(ip)

    if len(sys.argv) == 2:
        ip = sys.argv[1]
        # client_session = ClientSession(ip=ip)
        create_session(ip)

    if len(sys.argv) == 3:
        ip, port = sys.argv[1], sys.argv[2]
        # client_session = ClientSession(ip, int(port))
        create_session(ip, int(port))
