import typer
from typing import Optional
import socket
from kademlia.storage import PersistentStorage
from kademlia.network import Server
import threading
import time

app = app = typer.Typer()

@app.command()
def start(bootstrap_nodes: Optional[str] = None):
    host_ip = socket.gethostbyname(socket.gethostname())
    port = 8080
    server = Server(storage=PersistentStorage())
    threading.Thread(target=server.listen, args=(port, host_ip)).start()
    time.sleep(0.3)
    if bootstrap_nodes:
        target_host, target_port = bootstrap_nodes.split(' ')
        server.bootstrap([(target_host, target_port)])
    
    time.sleep(0.3)
    print(f'Server started at {host_ip}')

if __name__ == '__main__':
    app()