"""Playwright E2E workflow tests: startup → scan → start/stop/start all fans.

These three tests cover the primary user journey in sequence:
  1. The GUI loads and shows the connect dialog.
  2. Scanning discovers the expected fans.
  3. Every discovered fan is turned on, off, and on again.

Running against the simulator (default):
    pytest tests/webdashboard/e2e/test_fan_workflow.py

Running against a real network (backend must already be running):
    VENTO_TEST_MODE=network \\
    VENTO_BASE_URL=http://192.168.1.50:8080 \\
    pytest tests/webdashboard/e2e/test_fan_workflow.py

See conftest.py for the full set of environment variables.
"""
from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect

# ---------------------------------------------------------------------------
# Timeouts (milliseconds)
# ---------------------------------------------------------------------------

_SCAN_TIMEOUT    = 20_000   # UDP discovery can be slow; allow 20 s
_CONNECT_TIMEOUT = 10_000   # time from clicking a device to the power button appearing
_POWER_TIMEOUT   = 10_000   # time for a power-state change to propagate back from the fan


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _wait_scan_idle(page: Page) -> None:
    """Block until the Rescan button is present and no longer showing 'Scanning…'.

    The button may already read 'Scanning…' when we arrive (e.g. the dialog
    auto-scans on mount), so we match both texts to find the element first,
    then wait for it to settle to 'Rescan'.
    """
    rescan = page.get_by_role("button", name=re.compile(r"Rescan|Scanning", re.IGNORECASE))
    expect(rescan).to_be_visible(timeout=_SCAN_TIMEOUT)
    expect(rescan).to_have_text("Rescan", timeout=_SCAN_TIMEOUT)


def _power_button(page: Page):
    """Return a locator for the power button regardless of its current state."""
    return page.get_by_role("button", name=re.compile(r"Turn (on|off)", re.IGNORECASE))


def _set_power(page: Page, *, on: bool) -> None:
    """Ensure the fan is in the requested power state, toggling if necessary."""
    btn = _power_button(page)
    expect(btn).to_be_visible(timeout=_CONNECT_TIMEOUT)

    current_label = btn.get_attribute("aria-label")
    currently_on  = current_label == "Turn off"

    if currently_on != on:
        btn.click()

    expected_label = "Turn off" if on else "Turn on"
    expect(btn).to_have_attribute("aria-label", expected_label, timeout=_POWER_TIMEOUT)


# ---------------------------------------------------------------------------
# Test 1 – GUI startup
# ---------------------------------------------------------------------------

def test_gui_starts(page: Page, e2e_base_url: str) -> None:
    """The web GUI loads and immediately shows the connect dialog."""
    page.goto(e2e_base_url)
    expect(page.get_by_role("dialog", name="Connect to device")).to_be_visible()
    expect(page.get_by_role("button", name="Rescan")).to_be_visible()


# ---------------------------------------------------------------------------
# Test 2 – Fan discovery
# ---------------------------------------------------------------------------

def test_scan_discovers_fans(
    page: Page,
    e2e_base_url: str,
    e2e_fan_count: int | None,
) -> None:
    """Scanning discovers at least one fan (at least N in simulator mode)."""
    page.goto(e2e_base_url)

    # The dialog fires an automatic scan on mount; wait for it to finish.
    _wait_scan_idle(page)

    device_items = page.locator(".device-item")
    expect(device_items.first).to_be_visible(timeout=_SCAN_TIMEOUT)

    if e2e_fan_count is not None:
        # Simulator mode: at least the simulated fans must be present.
        # More may appear if real fans are also on the LAN.
        actual = device_items.count()
        assert actual >= e2e_fan_count, (
            f"Expected at least {e2e_fan_count} simulated fan(s), found {actual}"
        )


# ---------------------------------------------------------------------------
# Test 3 – Start / stop / start all discovered fans
# ---------------------------------------------------------------------------

def test_start_stop_start_all_fans(
    page: Page,
    e2e_base_url: str,
    e2e_device_prefix: str,
) -> None:
    """Connect to every discovered fan and cycle its power: on → off → on.

    Each fan gets a fresh page load to avoid a race where WebSocket state
    updates from the previously connected fan collapse the connect dialog
    while its auto-scan is still in progress.
    """
    # ── Discover fans (first load) ───────────────────────────────────────────
    page.goto(e2e_base_url)
    _wait_scan_idle(page)

    device_items = page.locator(".device-item")
    expect(device_items.first).to_be_visible(timeout=_SCAN_TIMEOUT)

    # Collect device names before any navigation away from the dialog.
    # Each .dev-name span holds just the device ID (without the IP address).
    # In simulator mode, restrict to the SIMFAN* devices so real LAN fans
    # (which may be unreachable or behave unexpectedly) are not power-cycled.
    all_names: list[str] = page.locator(".dev-name").all_text_contents()
    device_names = (
        [n for n in all_names if n.startswith(e2e_device_prefix)]
        if e2e_device_prefix
        else all_names
    )
    assert device_names, (
        f"No fans matching prefix '{e2e_device_prefix}' found — "
        "cannot run power-cycle test"
    )

    # ── Power-cycle each fan ─────────────────────────────────────────────────
    for index, name in enumerate(device_names):
        if index > 0:
            # Disconnect via the REST API so the backend is no longer connected.
            # Without this, page.reload() would see a 200 /api/state and skip
            # the connect dialog entirely.
            page.request.delete(f"{e2e_base_url}/api/connect")
            page.reload()
            _wait_scan_idle(page)

        # Connect by clicking the device's row in the discovered list.
        page.locator(".device-item").filter(has_text=name).click()
        expect(_power_button(page)).to_be_visible(timeout=_CONNECT_TIMEOUT)

        # Power cycle: on → off → on
        _set_power(page, on=True)
        _set_power(page, on=False)
        _set_power(page, on=True)
