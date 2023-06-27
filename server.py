from typer import Typer, Argument, Option
from typing import Optional
import socket
from kademlia.storage import PersistentStorage
from kademlia.network import Server
import threading
import time
import sys
from message_system.message_system import Message_System
from kademlia.utils import get_ips

def start_(host_ip: Optional[str], bootstrap_nodes: Optional[str] = None):
    # host_ip = socket.gethostbyname(socket.gethostname())
    broadcast = None
    print(host_ip)
    if host_ip is None:
        ip_br = get_ips()
        broadcast = ip_br['broadcast']
        host_ip = ip_br['addr']
        
    print(host_ip)
    ms = Message_System(host_ip, broadcast)
    hosts = []
    if bootstrap_nodes is None:
        print("No bootstrap Nodes given, trying to auto-detect")

        msg = ms.receive()
        print(msg)
        if msg:
            hosts.append(msg)
            print("Found ", msg)
            bootstrap_nodes = msg
        else:
            print("No servers answered :(")
        # time.sleep(1)

    if host_ip is None:
        print('Initiating client with local ip and default port')
        host_ip = socket.gethostbyname(socket.gethostname())
        # client_session = ClientSession(ip=host_ip)

    Server.init(ip=host_ip.split(" ")[0])

    print(f"broadcasting {Server.node.ip} {Server.node.port}")
    ms.add_to_send(f"{Server.node.ip} {Server.node.port}")
    heartbeat_thread = threading.Thread(target=ms.send_heartbeat)
    heartbeat_thread.start()
    # Server.init(ip="192.168.26.2")
    if bootstrap_nodes:
        target_host, target_port = bootstrap_nodes.split(' ')
        Server.bootstrap([(target_host, target_port)])

    print(f'Server started at {host_ip}')


app = Typer()


@app.command()
def start(host_ip=Option(None), bootstrap_nodes=Option(None)):
    print(host_ip)
    if bootstrap_nodes:
        start_(host_ip, bootstrap_nodes)
    else:
        start_(host_ip)


if __name__ == '__main__':
    app()
