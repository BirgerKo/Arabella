from __future__ import annotations

import asyncio
import socket
import logging

from .exceptions import VentoConnectionError, VentoDiscoveryError
from .parameters import DEFAULT_PORT

log = logging.getLogger(__name__)

_UDP_BUFFER_SIZE = 1024


class VentoTransport:
    def __init__(self, timeout: float = 3.0) -> None:
        self.timeout = timeout

    def send_recv(self, host: str, packet: bytes, port: int = DEFAULT_PORT, timeout: float | None = None) -> bytes:
        t = timeout if timeout is not None else self.timeout
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.settimeout(t)
                s.sendto(packet, (host, port))
                data, _ = s.recvfrom(_UDP_BUFFER_SIZE)
                return data
        except socket.timeout:
            raise VentoConnectionError(f"Timeout from {host}:{port}")
        except OSError as e:
            raise VentoConnectionError(f"Socket error {host}:{port}: {e}") from e

    def send_only(self, host: str, packet: bytes, port: int = DEFAULT_PORT) -> None:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.sendto(packet, (host, port))
        except OSError as e:
            raise VentoConnectionError(f"Send error {host}:{port}: {e}") from e

    def discover(
        self,
        pkt: bytes,
        broadcast: str = '255.255.255.255',
        port: int = DEFAULT_PORT,
        timeout: float = 3.0,
        max_devices: int = 64,
    ) -> list[dict]:
        results = []
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.settimeout(timeout)
                s.sendto(pkt, (broadcast, port))
                while len(results) < max_devices:
                    try:
                        data, addr = s.recvfrom(_UDP_BUFFER_SIZE)
                        results.append({'ip': addr[0], 'raw': data})
                    except socket.timeout:
                        break
        except OSError as e:
            raise VentoDiscoveryError(f"Discovery error: {e}") from e
        return results


class _SingleResponseProtocol(asyncio.DatagramProtocol):
    """Asyncio UDP protocol that resolves a Future with the first datagram received."""

    def __init__(self, future: asyncio.Future) -> None:
        self._future = future

    def datagram_received(self, data: bytes, addr: tuple) -> None:
        if not self._future.done():
            self._future.set_result((data, addr))

    def error_received(self, exc: Exception) -> None:
        if not self._future.done():
            self._future.set_exception(exc)


class _DiscoveryProtocol(asyncio.DatagramProtocol):
    """Asyncio UDP protocol that enqueues every datagram received for discovery."""

    def __init__(self, queue: asyncio.Queue) -> None:
        self._queue = queue

    def datagram_received(self, data: bytes, addr: tuple) -> None:
        self._queue.put_nowait({'ip': addr[0], 'raw': data})


class AsyncVentoTransport:
    def __init__(self, timeout: float = 3.0) -> None:
        self.timeout = timeout

    async def send_recv(self, host: str, packet: bytes, port: int = DEFAULT_PORT, timeout: float | None = None) -> bytes:
        t = timeout if timeout is not None else self.timeout
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        try:
            transport, _ = await loop.create_datagram_endpoint(
                lambda: _SingleResponseProtocol(future),
                remote_addr=(host, port),
            )
        except OSError as e:
            raise VentoConnectionError(f"Cannot open socket {host}:{port}: {e}") from e
        try:
            transport.sendto(packet)
            data, _ = await asyncio.wait_for(future, timeout=t)
            return data
        except asyncio.TimeoutError:
            raise VentoConnectionError(f"Async timeout {host}:{port}")
        finally:
            transport.close()

    async def send_only(self, host: str, packet: bytes, port: int = DEFAULT_PORT) -> None:
        loop = asyncio.get_running_loop()
        transport, _ = await loop.create_datagram_endpoint(
            asyncio.DatagramProtocol,
            remote_addr=(host, port),
        )
        transport.sendto(packet)
        await asyncio.sleep(0)  # yield so the event loop flushes the write buffer before closing
        transport.close()

    async def discover(
        self,
        pkt: bytes,
        broadcast: str = '255.255.255.255',
        port: int = DEFAULT_PORT,
        timeout: float = 3.0,
        max_devices: int = 64,
    ) -> list[dict]:
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()
        try:
            transport, _ = await loop.create_datagram_endpoint(
                lambda: _DiscoveryProtocol(queue),
                family=socket.AF_INET,
                allow_broadcast=True,
            )
        except OSError as e:
            raise VentoDiscoveryError(f"Async discovery error: {e}") from e
        results = []
        try:
            transport.sendto(pkt, (broadcast, port))
            deadline = loop.time() + timeout
            while len(results) < max_devices:
                remaining = deadline - loop.time()
                if remaining <= 0:
                    break
                try:
                    results.append(await asyncio.wait_for(queue.get(), timeout=remaining))
                except asyncio.TimeoutError:
                    break
        finally:
            transport.close()
        return results
