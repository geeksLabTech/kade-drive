from typer import Typer, Option
import socket
from kade_drive.core.network import Server
import threading
from message_system.message_system import logger, MessageSystem
from kade_drive.core.config import Config
import logging

# Create a file handler
file_handler = logging.FileHandler("log_file.log")

# Set the logging format
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)

# Add the file handler to the logger
# logging.basicConfig(level=logging.INFO,
#                     format='%(asctime)s  - %(name)s - %(levelname)s - %(message)s')
# logging.getLogger("SERVER/8086").setLevel(logging.CRITICAL)
# Create a logger instance
logger = logging.getLogger(__name__)


def start_server(host_ip=None, config: Config | None = None):
    broadcast = None
    logger.debug(host_ip)
    bootstrap_nodes = None

    if host_ip is None:
        ip_br = MessageSystem.get_ips()[0]
        logger.debug(ip_br)
        broadcast = ip_br["broadcast"]
        host_ip = ip_br["addr"]
    logger.info(host_ip)

    ms = MessageSystem(host_ip, broadcast)
    hosts = []

    msg = ms.receive(service_name="dfs")
    logger.debug(msg)
    if msg:
        hosts.append(msg)
        logger.debug(f"Found {msg}")
        bootstrap_nodes = msg
    else:
        logger.info("No servers answered :(")

    if host_ip is None:
        logger.warning(f"aaa {socket.gethostname()}")
        host_ip = socket.gethostbyname(socket.gethostname())

    if config is None:
        config = Config()
    Server.init(ip=host_ip.split(" ")[0], config=config)

    logger.info(f"broadcasting {Server.node.ip} {Server.node.port}")
    ms.add_to_send(f"dfs {Server.node.ip} {Server.node.port}")
    heartbeat_thread = threading.Thread(target=ms.send_heartbeat)
    heartbeat_thread.start()

    if bootstrap_nodes:
        target_host, target_port = bootstrap_nodes.split(" ")
        Server.bootstrap([(target_host, target_port)])

    logger.info(f"Server started at {host_ip}")


app = Typer()


@app.command()
def start(host_ip=Option(default=None), log_level=Option(default="DEBUG")):
    match log_level:
        case 'INFO':
            log_level = logging.INFO
        case 'DEBUG':
            log_level = logging.DEBUG
        case 'WARNING':
            log_level = logging.WARNING
        case _:
            log_level = logging.INFO

    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    logging.getLogger("SERVER").setLevel(logging.CRITICAL+1)
    # Create a logger instance
    logger = logging.getLogger(__name__)
    if not type(host_ip) == str:
        host_ip = None
    logger.debug(host_ip)
    start_server(host_ip)


if __name__ == "__main__":
    app()
