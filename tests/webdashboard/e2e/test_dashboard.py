"""Playwright E2E tests for the Arabella web dashboard.

Prerequisites:
  - Backend running on http://localhost:8080
  - Frontend built and served by the backend (`python -m webdashboard`), OR
    Vite dev server on http://localhost:5173 (with backend proxy)
  - A connected device or the VentoFanSim simulator running

Run with:
    pytest tests/webdashboard/e2e/ --base-url http://localhost:8080

These tests use Playwright's sync API via pytest-playwright.
"""
import pytest
from playwright.sync_api import Page, expect

BASE = "http://localhost:8080"


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {**browser_context_args, "base_url": BASE}


# ── Connect dialog ─────────────────────────────────────────────────────────────

def test_connect_dialog_shown_on_load(page: Page):
    """Connect dialog is visible when no device is connected."""
    page.goto("/")
    expect(page.get_by_role("dialog", name="Connect to device")).to_be_visible()


def test_connect_dialog_has_rescan_button(page: Page):
    page.goto("/")
    expect(page.get_by_role("button", name="Rescan")).to_be_visible()


# ── Power button ───────────────────────────────────────────────────────────────

def test_power_button_visible_when_connected(page: Page):
    """Power button is rendered after connecting."""
    page.goto("/")
    # Connect via the manual form using the simulator defaults
    page.get_by_placeholder("IP address").fill("127.0.0.1")
    page.get_by_placeholder("Device ID").fill("VENT-SIM")
    page.get_by_role("button", name="Connect").click()

    expect(page.get_by_role("button", name=/Turn (on|off)/i)).to_be_visible(timeout=10_000)


def test_power_button_toggle(page: Page):
    """Clicking the power button changes its state."""
    page.goto("/")
    page.get_by_placeholder("IP address").fill("127.0.0.1")
    page.get_by_placeholder("Device ID").fill("VENT-SIM")
    page.get_by_role("button", name="Connect").click()

    power_btn = page.get_by_role("button", name=/Turn (on|off)/i)
    expect(power_btn).to_be_visible(timeout=10_000)
    initial_label = power_btn.get_attribute("aria-label")
    power_btn.click()

    # After click, label should be the opposite
    expected = "Turn off" if initial_label == "Turn on" else "Turn on"
    expect(power_btn).to_have_attribute("aria-label", expected, timeout=8_000)


# ── Speed control ──────────────────────────────────────────────────────────────

def test_speed_preset_buttons_visible(page: Page):
    page.goto("/")
    page.get_by_placeholder("IP address").fill("127.0.0.1")
    page.get_by_placeholder("Device ID").fill("VENT-SIM")
    page.get_by_role("button", name="Connect").click()

    expect(page.get_by_role("button", name="1").first).to_be_visible(timeout=10_000)
    expect(page.get_by_role("button", name="2").first).to_be_visible()
    expect(page.get_by_role("button", name="3").first).to_be_visible()


def test_speed_preset_activates(page: Page):
    page.goto("/")
    page.get_by_placeholder("IP address").fill("127.0.0.1")
    page.get_by_placeholder("Device ID").fill("VENT-SIM")
    page.get_by_role("button", name="Connect").click()

    btn2 = page.get_by_role("button", name="2").first
    expect(btn2).to_be_visible(timeout=10_000)
    btn2.click()
    expect(btn2).to_have_attribute("aria-pressed", "true", timeout=8_000)


# ── Mode selector ──────────────────────────────────────────────────────────────

def test_mode_buttons_present(page: Page):
    page.goto("/")
    page.get_by_placeholder("IP address").fill("127.0.0.1")
    page.get_by_placeholder("Device ID").fill("VENT-SIM")
    page.get_by_role("button", name="Connect").click()

    expect(page.get_by_role("button", name="Ventilation")).to_be_visible(timeout=10_000)
    expect(page.get_by_role("button", name="Heat Recovery")).to_be_visible()
    expect(page.get_by_role("button", name="Supply")).to_be_visible()


# ── Scenarios ──────────────────────────────────────────────────────────────────

def test_save_scenario_modal(page: Page):
    page.goto("/")
    page.get_by_placeholder("IP address").fill("127.0.0.1")
    page.get_by_placeholder("Device ID").fill("VENT-SIM")
    page.get_by_role("button", name="Connect").click()

    page.get_by_role("button", name="Save as Scenario").click(timeout=10_000)
    expect(page.get_by_role("dialog", name="Save scenario")).to_be_visible()


def test_save_scenario_and_appears_in_list(page: Page):
    page.goto("/")
    page.get_by_placeholder("IP address").fill("127.0.0.1")
    page.get_by_placeholder("Device ID").fill("VENT-SIM")
    page.get_by_role("button", name="Connect").click()

    page.get_by_role("button", name="Save as Scenario").click(timeout=10_000)
    page.get_by_label("Name").fill("E2E Test Scenario")
    page.get_by_role("button", name="Save").click()

    expect(page.get_by_text("E2E Test Scenario")).to_be_visible(timeout=5_000)


# ── Status bar ─────────────────────────────────────────────────────────────────

def test_status_bar_shows_connected(page: Page):
    page.goto("/")
    page.get_by_placeholder("IP address").fill("127.0.0.1")
    page.get_by_placeholder("Device ID").fill("VENT-SIM")
    page.get_by_role("button", name="Connect").click()

    expect(page.get_by_text("Connected")).to_be_visible(timeout=10_000)


# ── Fan switching ──────────────────────────────────────────────────────────────

def _connect(page: Page, ip: str, device_id: str) -> None:
    """Fill in the connect dialog and submit it."""
    page.get_by_placeholder("IP address").fill(ip)
    page.get_by_placeholder("Device ID").fill(device_id)
    page.get_by_role("button", name="Connect").click()


def test_switch_button_visible_after_connect(page: Page):
    """The 'Switch…' button must be shown in the device header once connected."""
    page.goto("/")
    _connect(page, "127.0.0.1", "VENT-SIM")
    expect(page.get_by_role("button", name="Switch")).to_be_visible(timeout=10_000)


def test_switch_reopens_connect_dialog(page: Page):
    """Clicking 'Switch…' must re-open the connect dialog without a full page reload."""
    page.goto("/")
    _connect(page, "127.0.0.1", "VENT-SIM")

    page.get_by_role("button", name="Switch").click(timeout=10_000)
    expect(page.get_by_role("dialog", name="Connect to device")).to_be_visible(timeout=5_000)


def test_switch_between_fans(page: Page):
    """Connecting to a second device via 'Switch…' must update the dashboard to show the new device ID."""
    page.goto("/")

    # Connect to first fan
    _connect(page, "127.0.0.1", "VENT-SIM-1")
    expect(page.get_by_text("VENT-SIM-1")).to_be_visible(timeout=10_000)

    # Switch to second fan
    page.get_by_role("button", name="Switch").click()
    expect(page.get_by_role("dialog", name="Connect to device")).to_be_visible(timeout=5_000)
    _connect(page, "127.0.0.1", "VENT-SIM-2")

    # Dashboard must now show the second fan's device ID, not the first
    expect(page.get_by_text("VENT-SIM-2")).to_be_visible(timeout=10_000)
    expect(page.get_by_text("VENT-SIM-1")).not_to_be_visible()


def test_switch_connect_dialog_is_prefilled_with_current_device(page: Page):
    """The connect dialog opened via 'Switch…' must pre-populate the current device's IP and ID."""
    page.goto("/")
    _connect(page, "127.0.0.1", "VENT-SIM")
    expect(page.get_by_text("VENT-SIM")).to_be_visible(timeout=10_000)

    page.get_by_role("button", name="Switch").click()

    expect(page.get_by_placeholder("IP address")).to_have_value("127.0.0.1", timeout=5_000)
    expect(page.get_by_placeholder("Device ID")).to_have_value("VENT-SIM", timeout=5_000)
