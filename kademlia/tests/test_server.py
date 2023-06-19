

import pytest

from kademlia.network import Server
from kademlia.protocol import FileSystemProtocol
from kademlia.storage import PersistentStorage
import time


# @pytest.mark.asyncio
def test_server_storing():
    bootstrap_node = Server(storage=PersistentStorage())
    bootstrap_node.listen(8468)
    time.sleep(0.5)
    storage = PersistentStorage()
    server = Server(storage=storage)
    server.listen(8469)
    time.sleep(0.5)
    bootstrap_address = (bootstrap_node.node.ip, bootstrap_node.node.port)

    server.bootstrap([bootstrap_address])
    time.sleep(0.5)
    server.set('key', 'value')
    result = server.get('key')
    bootstrap_node.stop()
    server.stop()
    result = result.decode()

    assert result == 'value'


# class TestSwappableProtocol:

#     def test_default_protocol(self):  # pylint: disable=no-self-use
#         """
#         An ordinary Server object will initially not have a protocol, but will
#         have a FileSystemProtocol object as its protocol after its listen()
#         method is called.
#         """
#         loop = asyncio.get_event_loop()
#         server = Server()
#         # assert server.protocol is None
#         loop.run_until_complete(server.listen(8469))
#         assert isinstance(server.protocol, FileSystemProtocol)
#         assert isinstance(server.protocol.tcp_protocol, KademliaTCPProtocol)
#         assert isinstance(server.protocol.udp_protocol, KademliaUDPProtocol)
#         server.stop()
