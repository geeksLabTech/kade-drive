"""
Package for interacting on the network via a Async Protocol
"""

import asyncio
from asyncio import DatagramProtocol, DatagramTransport, Protocol, Transport
import logging
from base64 import b64encode
from typing import Any
from utils import _process_data


LOG = logging.getLogger(__name__)




class RPCUDPProtocol(DatagramProtocol):
    """
    Protocol implementation using msgpack to encode messages and asyncio
    to handle async sending / recieving.
    """
    def __init__(self, wait_timeout=5):
        """
        Create a protocol instance.

        Args:
            wait_timeout (int): Time to wait for a response before giving up
        """
        self._wait_timeout = wait_timeout
        self._outstanding = {}
        self.transport : DatagramTransport | None = None

    def connection_made(self, transport: DatagramTransport):
        self.transport = transport

    def datagram_received(self, data: bytes, addr: tuple[str|Any, int]):
        LOG.debug("received datagram from %s", addr)
        asyncio.ensure_future(_process_data(self, data, addr))

    def _timeout(self, msg_id):
        args = (b64encode(msg_id), self._wait_timeout)
        LOG.error("Did not receive reply for msg "
                  "id %s within %i seconds", *args)
        self._outstanding[msg_id][0].set_result((False, None))
        del self._outstanding[msg_id]

   
    
    # def __getattr__(self, name):
    #     """
    #     If name begins with "_" or "rpc_", returns the value of
    #     the attribute in question as normal.

    #     Otherwise, returns the value as normal *if* the attribute
    #     exists, but does *not* raise AttributeError if it doesn't.

    #     Instead, returns a closure, func, which takes an argument
    #     "address" and additional arbitrary args (but not kwargs).

    #     func attempts to call a remote method "rpc_{name}",
    #     passing those args, on a node reachable at address.
    #     """
    #     if name.startswith("_") or name.startswith("rpc_"):
    #         return getattr(super(), name)

    #     try:
    #         return getattr(super(), name)
    #     except AttributeError:
    #         pass

    #     def func(address, *args):
    #         msg_id = sha1(os.urandom(32)).digest()
    #         data = umsgpack.packb([name, args])
    #         if len(data) > 8192:
    #             raise MalformedMessage("Total length of function "
    #                                    "name and arguments cannot exceed 8K")
    #         txdata = b'\x00' + msg_id + data
    #         LOG.debug("calling remote function %s on %s (msgid %s)",
    #                   name, address, b64encode(msg_id))
    #         self.transport.sendto(txdata, address)

    #         loop = asyncio.get_event_loop()
    #         if hasattr(loop, 'create_future'):
    #             future = loop.create_future()
    #         else:
    #             future = asyncio.Future()
    #         timeout = loop.call_later(self._wait_timeout,
    #                                   self._timeout, msg_id)
    #         self._outstanding[msg_id] = (future, timeout)
    #         return future

    #     return func

class RPCTCPProtocol(Protocol):
    """
    Protocol implementation using msgpack to encode messages and asyncio
    to handle async sending / recieving.
    """

    def __init__(self, wait_timeout=5):
        """
        Create a protocol instance.

        Args:
            wait_timeout (int): Time to wait for a response before giving up
        """
        self._wait_timeout = wait_timeout
        self._outstanding = {}
        self.transport: Transport | None = None

    def connection_made(self, transport: Transport):
        self.transport = transport

    def data_received(self, data: bytes) -> None:
        asyncio.ensure_future(_process_data(self, data))

    def _timeout(self, msg_id):
        args = (b64encode(msg_id), self._wait_timeout)
        LOG.error("Did not receive reply for msg "
                  "id %s within %i seconds", *args)
        self._outstanding[msg_id][0].set_result((False, None))
        del self._outstanding[msg_id]