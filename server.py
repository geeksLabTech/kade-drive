from typer import Typer, Argument, Option
from typing import Optional
import socket
from core.storage import PersistentStorage
from core.network import Server
import threading
import time
import sys
from message_system.message_system import Message_System
from core.utils import get_ips
import logging

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s  - %(name)s - %(levelname)s - %(message)s')
logging.getLogger("SERVER/8086").setLevel(logging.CRITICAL)
# Create a logger instance
logger = logging.getLogger(__name__)


def start_(host_ip: Optional[str], bootstrap_nodes: Optional[str] = None):
    # host_ip = socket.gethostbyname(socket.gethostname())
    broadcast = None
    logger.debug(host_ip)
    # print(host_ip)
    if host_ip is None:
        ip_br = get_ips()[0]
        broadcast = ip_br['broadcast']
        host_ip = ip_br['addr']
    logger.debug(host_ip)

    # print(host_ip)
    ms = Message_System(host_ip, broadcast)
    hosts = []
    if bootstrap_nodes is None:
        logger.info("No bootstrap Nodes given, trying to auto-detect")

        msg = ms.receive()
        logger.debug(msg)
        if msg:
            hosts.append(msg)
            logger.debug("Found ", msg)
            bootstrap_nodes = msg
        else:
            logger.info("No servers answered :(")
        # time.sleep(1)

    if host_ip is None:
        host_ip = socket.gethostbyname(socket.gethostname())
        # client_session = ClientSession(ip=host_ip)

    Server.init(ip=host_ip.split(" ")[0])

    logger.info(f"broadcasting {Server.node.ip} {Server.node.port}")
    ms.add_to_send(f"{Server.node.ip} {Server.node.port}")
    heartbeat_thread = threading.Thread(target=ms.send_heartbeat)
    heartbeat_thread.start()
    # Server.init(ip="192.168.26.2")
    if bootstrap_nodes:
        target_host, target_port = bootstrap_nodes.split(' ')
        Server.bootstrap([(target_host, target_port)])

    logger.info(f'Server started at {host_ip}')


app = Typer()


@app.command()
def start(host_ip=Option(None), bootstrap_nodes=Option(None)):
    logger.debug(host_ip)
    if bootstrap_nodes:
        start_(host_ip, bootstrap_nodes)
    else:
        start_(host_ip)


if __name__ == '__main__':
    app()
