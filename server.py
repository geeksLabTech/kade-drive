from typer import Typer, Argument
from typing import Optional
import socket
from kademlia.storage import PersistentStorage
from kademlia.network import Server
import threading
import time
import sys


def start_(bootstrap_nodes: Optional[str] = None):
    host_ip = socket.gethostbyname(socket.gethostname())

    if len(sys.argv) < 2:
        print('Initiating client with local ip and default port')
        host_ip = socket.gethostbyname(socket.gethostname())
        # client_session = ClientSession(ip=host_ip)

    if len(sys.argv) == 2:
        host_ip = sys.argv[1]
        # client_session = ClientSession(ip=ip)

    Server.init(ip=host_ip.split(" ")[0])
    # Server.init(ip="192.168.26.2")
    time.sleep(0.3)
    if bootstrap_nodes:
        target_host, target_port = bootstrap_nodes.split(' ')
        Server.bootstrap([(target_host, target_port)])

    time.sleep(0.3)
    print(f'Server started at {host_ip}')


app = Typer()


@app.command()
def start(bootstrap_nodes=Argument(None)):
    if bootstrap_nodes:
        start_(bootstrap_nodes)
    else:
        start_()


if __name__ == '__main__':
    app()
