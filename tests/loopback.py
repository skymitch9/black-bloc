"""Asyncio self-pipes close with a reset, so a run leaves no loopback TIME_WAIT behind."""

import socket
import struct
import sys

_pair = socket.socketpair
_RESET_ON_CLOSE = struct.pack("hh", 1, 0)


def quiet_socketpair(*args, **kwargs):
    ends = _pair(*args, **kwargs)
    for end in ends:
        end.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, _RESET_ON_CLOSE)
    return ends


if sys.platform == "win32":
    socket.socketpair = quiet_socketpair
