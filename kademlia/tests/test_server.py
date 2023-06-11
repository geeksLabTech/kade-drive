import asyncio

import pytest

from kademlia.network import Server
from kademlia.protocol import FileSystemProtocol


@pytest.mark.asyncio
async def test_storing(bootstrap_node):
    server = Server()
    await server.listen(bootstrap_node[1] + 1)
    print("listen")
    await server.bootstrap([bootstrap_node])
    print("bootstrap")
    await server.set('key', 'value')
    print("set")
    result = await server.get('key')
    print("result")
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
        # loop.run_until_complete(server.listen(8469))
        assert isinstance(server.protocol, FileSystemProtocol)
        server.stop()

    
    
    
    