from typer import Typer, Argument, Option
from typing import Match, Optional
import socket
from core.storage import PersistentStorage
from core.network import Server
import threading
import time
import sys
from message_system.message_system import Message_System
from core.utils import get_ips
import logging

# Create a file handler
file_handler = logging.FileHandler('log_file.log')

# Set the logging format
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# Add the file handler to the logger
# logging.basicConfig(level=logging.INFO,
#                     format='%(asctime)s  - %(name)s - %(levelname)s - %(message)s')
# logging.getLogger("SERVER/8086").setLevel(logging.CRITICAL)
# Create a logger instance
logger = logging.getLogger(__name__)


def start_server(host_ip=None):
    # host_ip = socket.gethostbynahost_ipme(socket.gethostname())
    broadcast = None
    logger.debug(host_ip)
    bootstrap_nodes = None
    # print(host_ip)
    if host_ip is None:
        ip_br = get_ips()[0]
        broadcast = ip_br['broadcast']
        host_ip = ip_br['addr']
    logger.info(host_ip)

    # print(host_ip)
    ms = Message_System(host_ip, broadcast)
    hosts = []

    msg = ms.receive(service_name='dfs')
    logger.debug(msg)
    if msg:
        hosts.append(msg)
        logger.debug(f"Found {msg}")
        bootstrap_nodes = msg
    else:
        logger.info("No servers answered :(")
    # time.sleep(1)

    if host_ip is None:
        logger.warning(f"aaa {socket.get_hostname()}")
        host_ip = socket.gethostbyname(socket.gethostname())
        # client_session = ClientSession(ip=host_ip)

    Server.init(ip=host_ip.split(" ")[0])

    logger.info(f"broadcasting {Server.node.ip} {Server.node.port}")
    ms.add_to_send(f"dfs {Server.node.ip} {Server.node.port}")
    heartbeat_thread = threading.Thread(target=ms.send_heartbeat)
    heartbeat_thread.start()
    # # Server.init(ip="192.168.26.2")
    if bootstrap_nodes:
        target_host, target_port = bootstrap_nodes.split(' ')
        Server.bootstrap([(target_host, target_port)])

    logger.info(f'Server started at {host_ip}')


app = Typer()


@app.command()
def _start(host_ip=Option(default=None), log_level=Option(default='INFO')):

    if log_level == 'INFO':
        log_level = logging.INFO
    if log_level == 'DEBUG':
        log_level = logging.DEBUG
    if log_level == 'WARNING':
        log_level = logging.WARNING

    logging.basicConfig(level=log_level,
                        format='%(asctime)s  - %(name)s - %(levelname)s - %(message)s')

    logging.getLogger("SERVER/8086").setLevel(logging.CRITICAL)
    # Create a logger instance
    logger = logging.getLogger(__name__)

    logger.debug(host_ip)
    start_server(host_ip)


if __name__ == '__main__':
    app()
