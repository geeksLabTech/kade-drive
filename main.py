import typer 
import socket
from typing import Optional, List
from kademlia.storage import PersistentStorage
from kademlia.network import Server
import time

app = typer.Typer()
running_server: Server|None = None

@app.command()
def start(bootstrap_nodes: Optional[str]):
    host_ip = socket.gethostbyname(socket.gethostname())
    port = 8080
    server = Server(storage=PersistentStorage())
    server.listen(port=port, interface=host_ip)
    if bootstrap_nodes:
        target_host, target_port = bootstrap_nodes.split(' ')
        server.bootstrap([(target_host, target_port)])

    time.sleep(0.3)
    running_server = server
    print(f'Server started at {host_ip}')


@app.command()
def get_by_key(key: str):
    assert running_server is not None
    result = running_server.get(key)
    assert result is not None
    print(f'value is {result.decode()}')

@app.command()
def put(key: str, value: str):
    assert running_server is not None
    result = running_server.set(key, value)
    print(f'info saved')




if __name__ == "__main__":
    app()
    print('cli started')
