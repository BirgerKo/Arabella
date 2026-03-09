from __future__ import annotations
import asyncio, socket, logging
from .exceptions import VentoConnectionError, VentoDiscoveryError
from .parameters import DEFAULT_PORT
log = logging.getLogger(__name__)
_BUFSZ = 1024

class VentoTransport:
    def __init__(self, timeout=3.0): self.timeout = timeout
    def send_recv(self, host, packet, port=DEFAULT_PORT, timeout=None):
        t = timeout if timeout is not None else self.timeout
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.settimeout(t); s.sendto(packet, (host, port))
                data, addr = s.recvfrom(_BUFSZ); return data
        except socket.timeout: raise VentoConnectionError(f"Timeout from {host}:{port}")
        except OSError as e: raise VentoConnectionError(f"Socket error {host}:{port}: {e}") from e
    def send_only(self, host, packet, port=DEFAULT_PORT):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.sendto(packet, (host, port))
        except OSError as e: raise VentoConnectionError(f"Send error {host}:{port}: {e}") from e
    def discover(self, pkt, broadcast='255.255.255.255', port=DEFAULT_PORT, timeout=3.0, max_devices=64):
        results = []
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.settimeout(timeout); s.sendto(pkt, (broadcast, port))
                while len(results) < max_devices:
                    try: data, addr = s.recvfrom(_BUFSZ); results.append({'ip': addr[0], 'raw': data})
                    except socket.timeout: break
        except OSError as e: raise VentoDiscoveryError(f"Discovery error: {e}") from e
        return results

class _AsyncUDPProto(asyncio.DatagramProtocol):
    def __init__(self, fut): self._f = fut
    def datagram_received(self, data, addr):
        if not self._f.done(): self._f.set_result((data, addr))
    def error_received(self, exc):
        if not self._f.done(): self._f.set_exception(exc)

class _AsyncDiscoveryProto(asyncio.DatagramProtocol):
    def __init__(self, q): self._q = q
    def datagram_received(self, data, addr): self._q.put_nowait({'ip': addr[0], 'raw': data})

class AsyncVentoTransport:
    def __init__(self, timeout=3.0): self.timeout = timeout
    async def send_recv(self, host, packet, port=DEFAULT_PORT, timeout=None):
        t = timeout if timeout is not None else self.timeout
        loop = asyncio.get_running_loop(); fut = loop.create_future()
        try: tr, _ = await loop.create_datagram_endpoint(lambda: _AsyncUDPProto(fut), remote_addr=(host, port))
        except OSError as e: raise VentoConnectionError(f"Cannot open socket {host}:{port}: {e}") from e
        try:
            tr.sendto(packet); data, addr = await asyncio.wait_for(fut, timeout=t); return data
        except asyncio.TimeoutError: raise VentoConnectionError(f"Async timeout {host}:{port}")
        finally: tr.close()
    async def send_only(self, host, packet, port=DEFAULT_PORT):
        loop = asyncio.get_running_loop()
        tr, _ = await loop.create_datagram_endpoint(asyncio.DatagramProtocol, remote_addr=(host, port))
        tr.sendto(packet); tr.close()
    async def discover(self, pkt, broadcast='255.255.255.255', port=DEFAULT_PORT, timeout=3.0, max_devices=64):
        loop = asyncio.get_running_loop(); q = asyncio.Queue()
        try: tr, _ = await loop.create_datagram_endpoint(lambda: _AsyncDiscoveryProto(q), family=socket.AF_INET, allow_broadcast=True)
        except OSError as e: raise VentoDiscoveryError(f"Async discovery error: {e}") from e
        results = []
        try:
            tr.sendto(pkt, (broadcast, port)); deadline = loop.time() + timeout
            while len(results) < max_devices:
                rem = deadline - loop.time()
                if rem <= 0: break
                try: results.append(await asyncio.wait_for(q.get(), timeout=rem))
                except asyncio.TimeoutError: break
        finally: tr.close()
        return results
