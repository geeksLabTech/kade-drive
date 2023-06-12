
import asyncio
from asyncio import DatagramTransport, BaseProtocol, Transport
import logging
from math import log
import os
from base64 import b64encode
from hashlib import sha1
from typing import Any, Callable
from functools import wraps

import umsgpack

from rpc.exceptions import MalformedMessage

LOG = logging.getLogger(__name__)


async def _process_data(protocol: BaseProtocol, data: bytes, address: tuple[str | Any, int] | None = None):
    if len(data) < 22:
        LOG.warning("received datagram too small from %s,"
                    " ignoring", address)
        return
    msg_id = data[1:21]
    LOG.warning('proceso data')
    if data[:1] == b'\x00':
        # schedule accepting request and returning the result
        LOG.warning("ENTROOOOOO")
        data = umsgpack.unpackb(data[21:])
        asyncio.ensure_future(_accept_request(protocol, msg_id, data, address))
    elif data[:1] == b'\x01':
        data = umsgpack.unpackb(data[21:])
        _accept_response(protocol, msg_id, data, address)
    else:
        # otherwise, don't know the format, don't do anything
        LOG.warning("Received unknown message from %s, ignoring", address)


def _accept_response(protocol: BaseProtocol, msg_id, data, address: tuple[str | Any, int] | None = None):
    msgargs = (b64encode(msg_id), address)
    if msg_id not in protocol._outstanding:
        LOG.warning("received unknown message %s "
                    "from %s; ignoring", *msgargs)
        return
    LOG.debug("received response %s for message "
              "id %s from %s", data, *msgargs)
    future, timeout = protocol._outstanding[msg_id]
    timeout.cancel()
    future.set_result((True, data))
    del protocol._outstanding[msg_id]


async def _accept_request(protocol: BaseProtocol, msg_id, data, address: tuple[str | Any, int] | None = None):
    if not isinstance(data, list) or len(data) != 3:
        raise MalformedMessage("Could not read packet: %s" % data)
    funcname, args, kwargs = data
    func = getattr(protocol, funcname, None)
    if func is None or not callable(func):
        msgargs = (protocol.__class__.__name__, funcname)
        LOG.warning("%s has no callable method "
                    "%s; ignoring request", *msgargs)
        return
    if not asyncio.iscoroutinefunction(func):
        func = asyncio.coroutine(func)
    LOG.warning('Calling function')
    response = await func(address, *args, *kwargs)
    LOG.warning("sending response %s for msg id %s to %s",
                response, b64encode(msg_id), address)
    txdata = b'\x01' + msg_id + umsgpack.packb(response)
    LOG.warning(f'tipo de dato sendto, {type(txdata)}')
    if isinstance(protocol.transport, DatagramTransport):
        protocol.transport.sendto(txdata, address)

    elif isinstance(protocol.transport, Transport):
        protocol.transport.write(txdata)

    else:
        LOG.error('Protocol class does not have transport attribute')


def rpc_tcp(f: Callable):
    """
    Use this function to decorate class methods that you need to be
    called on remote machines using TCP protocol.
    """
    @wraps(f)
    def _impl(self, *method_args, **method_kwargs):
        return __decorator_impl(self, f, -1, method_args, method_kwargs)
    return _impl


def rpc_udp(index_of_sender_in_args: int):
    """
    Use this function to decorate class methods that you need to be
    called on remote machines using UDP protocol

    Args:
        index_of_sender_in_args (int): index of argument that refers to sender address starting in 1,
        (self doesn't count). 
    """
    def _wrapper(f: Callable):
        @wraps(f)
        def _impl(self, *method_args, **method_kwargs):
            return __decorator_impl(self, f, index_of_sender_in_args, *method_args, *method_kwargs)
        return _impl
    return _wrapper


def __decorator_impl(self: BaseProtocol, f: Callable, index_of_sender_in_args: int, *method_args, **method_kwargs):
    func_name = f.__name__
    msg_id = sha1(os.urandom(32)).digest()
    data = umsgpack.packb([func_name, method_args, method_kwargs])
    if len(data) > 8192:
        raise MalformedMessage("Total length of function "
                               "name and arguments cannot exceed 8K")
    txdata = b'\x00' + msg_id + data
    # assert type(txdata) == str or type(txdata) == bytes or type(txdata) == bytearray
    LOG.warning(f'tipo de dato sendto, {type(txdata)}')
    # print('PRUBEAAA')
    if index_of_sender_in_args >= 0:
        address = method_args[index_of_sender_in_args]
        LOG.warning(f'method args are {method_args}')
        LOG.warning(f'Address es {address}')
        LOG.warning(f'txdata es {type(txdata)}')
        LOG.warning("calling remote function %s on %s using UDP, (msgid %s)",
                    func_name, address, b64encode(msg_id))
        try:
            LOG.warning(self.transport)
            self.transport.sendto(txdata, address)
        except:
            LOG.warning('Failed sendto')

    else:
        LOG.warning("calling remote function %s using TCP, (msgid %s)",
                    func_name, b64encode(msg_id))
        self.transport.write(txdata)

    loop = asyncio.get_event_loop()
    if hasattr(loop, 'create_future'):
        future = loop.create_future()
    else:
        future = asyncio.Future()

    timeout = loop.call_later(self._wait_timeout,
                              self._timeout, msg_id)
    self._outstanding[msg_id] = (future, timeout)
    return future
