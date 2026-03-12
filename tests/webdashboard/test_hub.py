"""Unit tests for the WebSocket broadcast hub."""
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from webdashboard.backend.hub import ConnectionHub


@pytest.fixture
def hub():
    return ConnectionHub()


def make_websocket():
    ws = MagicMock()
    ws.accept = AsyncMock()
    ws.send_text = AsyncMock()
    ws.receive_text = AsyncMock(return_value="ping")
    return ws


@pytest.mark.asyncio
async def test_connect_accepts_websocket(hub):
    ws = make_websocket()
    await hub.connect(ws)
    ws.accept.assert_awaited_once()
    assert hub.client_count == 1


@pytest.mark.asyncio
async def test_disconnect_removes_client(hub):
    ws = make_websocket()
    await hub.connect(ws)
    hub.disconnect(ws)
    assert hub.client_count == 0


@pytest.mark.asyncio
async def test_broadcast_sends_json_to_all_clients(hub):
    ws1 = make_websocket()
    ws2 = make_websocket()
    await hub.connect(ws1)
    await hub.connect(ws2)

    msg = {"type": "state", "data": {"power": True}}
    await hub.broadcast(msg)

    expected = json.dumps(msg)
    ws1.send_text.assert_awaited_once_with(expected)
    ws2.send_text.assert_awaited_once_with(expected)


@pytest.mark.asyncio
async def test_broadcast_removes_dead_connections(hub):
    ws_dead = make_websocket()
    ws_dead.send_text = AsyncMock(side_effect=RuntimeError("closed"))
    ws_ok   = make_websocket()

    await hub.connect(ws_dead)
    await hub.connect(ws_ok)

    await hub.broadcast({"type": "ping"})

    assert hub.client_count == 1
    ws_ok.send_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_broadcast_to_empty_hub_is_noop(hub):
    # Must not raise
    await hub.broadcast({"type": "test"})
    assert hub.client_count == 0
