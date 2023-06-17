
import socket
import rpyc
import sys


class ClientSession: 
    def __init__(self, ip: str|None = None, port: int = 8086) -> None:
        self.ip = ip if ip is not None else socket.gethostbyname(socket.gethostname())
        self.port = port 
        self.connection: rpyc.Connection|None = None
    
    def connect(self):
        self.connection = rpyc.connect(self.ip, self.port, keepalive=True)
        assert self.connection is not None and self.connection.root is not None 
        # print(self.connection.root.__dict__)
    
    def get(self, key):
        result = self.connection.root.get(key)
        return result
    
    def put(self, key, value):
        self.connection.root.set_key(key, value)
        print(f'value putted')


client_session: ClientSession|None = None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise Exception("Please specify ip and port to connect client")
    
    ip, port = sys.argv[1], sys.argv[2]
    client_session = ClientSession(ip, int(port))
    print('Connecting client to server')
    client_session.connect()
    print('Client shell started')
    while True:
        command = input('Expecting command: ').split(' ')
        if command[0] == 'exit':
            break
        
        args = command[1:] if len(command) >= 1 else []
        func = getattr(ClientSession, command[0], None)
        if func is None or not callable(func):
            print('not finded command with that name')
            continue
        print(f'calling {func} with arguments: {args}')
        result = func(client_session, *args)
        if result:
            print(f'Result is: {result}')
        else:
            print(f'command returned None')

