"""Session-level fixtures for E2E Playwright tests.

Supports two modes, controlled by environment variables:

  VENTO_TEST_MODE  = "simulator"  (default) – auto-starts simulator + backend
                   = "network"              – tests run against an already-
                                             running backend on a real network
  VENTO_BASE_URL   = "http://localhost:8080" (default)
  VENTO_FAN_COUNT  = 3           (default, simulator mode only)

Simulator mode (default):
    pytest tests/webdashboard/e2e/test_fan_workflow.py

Real-network mode (backend must already be running):
    VENTO_TEST_MODE=network \\
    VENTO_BASE_URL=http://192.168.1.50:8080 \\
    pytest tests/webdashboard/e2e/test_fan_workflow.py
"""
from __future__ import annotations

import os
import socket
import subprocess
import time
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Configuration from environment
# ---------------------------------------------------------------------------

_MODE      = os.getenv("VENTO_TEST_MODE", "simulator")
_BASE_URL  = os.getenv("VENTO_BASE_URL", "http://localhost:8080")
_FAN_COUNT = int(os.getenv("VENTO_FAN_COUNT", "3"))

_REPO_ROOT = Path(__file__).parents[3]   # …/Arabella/
_PYTHON    = "python3.11"
_BACKEND_HOST = "127.0.0.1"
_BACKEND_PORT = 8080
_SIMULATOR_STARTUP_SECONDS = 1.0  # UDP socket binds quickly; 1 s is more than enough


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _wait_tcp(host: str, port: int, timeout: float = 20.0) -> None:
    """Block until a TCP port is accepting connections, or raise TimeoutError."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return
        except OSError:
            time.sleep(0.25)
    raise TimeoutError(f"Service at {host}:{port} not ready after {timeout}s")


# ---------------------------------------------------------------------------
# Session-scoped fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def sim_proc():
    """Start the UDP fan simulator (simulator mode only).

    Yields the subprocess.Popen object so teardown can terminate it.
    Yields None in network mode (caller must handle).
    """
    if _MODE != "simulator":
        yield None
        return

    proc = subprocess.Popen(
        [_PYTHON, "-m", "ventocontrol.simulator", "--count", str(_FAN_COUNT)],
        cwd=_REPO_ROOT,
    )
    time.sleep(_SIMULATOR_STARTUP_SECONDS)
    yield proc
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture(scope="session")
def web_proc(sim_proc):  # noqa: ARG001  – sim_proc must start first
    """Start the web-dashboard backend (simulator mode only).

    Waits until the HTTP server is accepting connections before yielding.
    Yields None in network mode.
    """
    if _MODE != "simulator":
        yield None
        return

    proc = subprocess.Popen(
        [_PYTHON, "-m", "webdashboard"],
        cwd=_REPO_ROOT,
    )
    _wait_tcp(_BACKEND_HOST, _BACKEND_PORT)
    yield proc
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture(scope="session")
def e2e_base_url(web_proc) -> str:  # noqa: ARG001  – web_proc must start first
    """Return the base URL of the web dashboard under test."""
    return _BASE_URL


@pytest.fixture(scope="session")
def e2e_fan_count() -> int | None:
    """Return the expected number of discoverable fans.

    In simulator mode this is the fixed value of VENTO_FAN_COUNT.
    In network mode it is unknown (None), so tests skip the exact count check.
    """
    return _FAN_COUNT if _MODE == "simulator" else None


@pytest.fixture(scope="session")
def e2e_device_prefix() -> str:
    """Return a device-ID prefix used to filter which fans are power-cycled.

    In simulator mode all simulated fans share the 'SIMFAN' prefix, so the
    test restricts itself to those and ignores any real fans on the LAN.
    In network mode the prefix is empty, meaning all discovered fans are tested.
    Override with the VENTO_DEVICE_PREFIX environment variable if needed.
    """
    default = "SIMFAN" if _MODE == "simulator" else ""
    return os.getenv("VENTO_DEVICE_PREFIX", default)
