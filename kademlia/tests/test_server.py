import asyncio

import pytest

from kademlia.network import Server
from kademlia.protocol import FileSystemProtocol, KademliaTCPProtocol, KademliaUDPProtocol
from kademlia.storage import PersistentStorage



@pytest.mark.asyncio
async def test_server_storing(bootstrap_node):
    storage = PersistentStorage()
    server = Server(storage=storage)
    await server.listen(bootstrap_node[1] + 1)
    await server.bootstrap([bootstrap_node])
    await server.set('key', 'value')
    result = await server.get('key')
    result = result.decode()
    assert result == 'value'

    server.stop()


class TestSwappableProtocol:

    def test_default_protocol(self):  # pylint: disable=no-self-use
        """
        An ordinary Server object will initially not have a protocol, but will
        have a FileSystemProtocol object as its protocol after its listen()
        method is called.
        """
        loop = asyncio.get_event_loop()
        server = Server()
        # assert server.protocol is None
        loop.run_until_complete(server.listen(8469))
        assert isinstance(server.protocol, FileSystemProtocol)
        assert isinstance(server.protocol.tcp_protocol, KademliaTCPProtocol)
        assert isinstance(server.protocol.udp_protocol, KademliaUDPProtocol)
        server.stop()

    
    
    
    