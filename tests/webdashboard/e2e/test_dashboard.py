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
import re

import pytest
from playwright.sync_api import Page, expect

BASE = "http://localhost:8080"

_DEFAULT_IP        = "127.0.0.1"
_DEFAULT_DEVICE_ID = "VENT-SIM"


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {**browser_context_args, "base_url": BASE}


# ── Private helpers ─────────────────────────────────────────────────────────────

def _connect(page: Page, ip: str = _DEFAULT_IP, device_id: str = _DEFAULT_DEVICE_ID) -> None:
    """Fill in the connect dialog and submit it."""
    page.get_by_placeholder("IP address").fill(ip)
    page.get_by_placeholder("Device ID").fill(device_id)
    page.get_by_role("button", name="Connect").click()


# ── Connect dialog ─────────────────────────────────────────────────────────────

def test_connect_dialog_shown_on_load(page: Page):
    """Connect dialog is visible when no device is connected."""
    page.goto("/")
    expect(page.get_by_role("dialog", name="Connect to device")).to_be_visible()


def test_connect_dialog_has_rescan_button(page: Page):
    """Rescan button is present in the connect dialog."""
    page.goto("/")
    expect(page.get_by_role("button", name="Rescan")).to_be_visible()


# ── Power button ───────────────────────────────────────────────────────────────

def test_power_button_visible_when_connected(page: Page):
    """Power button is rendered after connecting."""
    page.goto("/")
    _connect(page)
    expect(page.get_by_role("button", name=re.compile(r"Turn (on|off)", re.IGNORECASE))).to_be_visible(timeout=10_000)


def test_power_button_toggle(page: Page):
    """Clicking the power button changes its state."""
    page.goto("/")
    _connect(page)

    power_btn = page.get_by_role("button", name=re.compile(r"Turn (on|off)", re.IGNORECASE))
    expect(power_btn).to_be_visible(timeout=10_000)
    initial_label = power_btn.get_attribute("aria-label")
    power_btn.click()

    # After click, label should be the opposite
    expected = "Turn off" if initial_label == "Turn on" else "Turn on"
    expect(power_btn).to_have_attribute("aria-label", expected, timeout=8_000)


# ── Speed control ──────────────────────────────────────────────────────────────

def test_speed_preset_buttons_visible(page: Page):
    """Speed preset buttons 1, 2, and 3 appear after connecting."""
    page.goto("/")
    _connect(page)
    expect(page.get_by_role("button", name="1").first).to_be_visible(timeout=10_000)
    expect(page.get_by_role("button", name="2").first).to_be_visible()
    expect(page.get_by_role("button", name="3").first).to_be_visible()


def test_speed_preset_activates(page: Page):
    """Clicking a speed preset marks it as pressed."""
    page.goto("/")
    _connect(page)
    btn2 = page.get_by_role("button", name="2").first
    expect(btn2).to_be_visible(timeout=10_000)
    btn2.click()
    expect(btn2).to_have_attribute("aria-pressed", "true", timeout=8_000)


# ── Mode selector ──────────────────────────────────────────────────────────────

def test_mode_buttons_present(page: Page):
    """All three operation-mode buttons are visible after connecting."""
    page.goto("/")
    _connect(page)
    expect(page.get_by_role("button", name="Ventilation")).to_be_visible(timeout=10_000)
    expect(page.get_by_role("button", name="Heat Recovery")).to_be_visible()
    expect(page.get_by_role("button", name="Supply")).to_be_visible()


# ── Scenarios ──────────────────────────────────────────────────────────────────

def test_save_scenario_modal(page: Page):
    """'Save as Scenario' opens the save dialog."""
    page.goto("/")
    _connect(page)
    page.get_by_role("button", name=re.compile(r"Scenario", re.IGNORECASE)).click(timeout=10_000)
    expect(page.get_by_role("dialog", name="Save scenario")).to_be_visible()


def test_save_scenario_and_appears_in_list(page: Page):
    """A saved scenario appears in the scenario list."""
    page.goto("/")
    _connect(page)
    page.get_by_role("button", name=re.compile(r"Scenario", re.IGNORECASE)).click(timeout=10_000)
    page.get_by_label("Name").fill("E2E Test Scenario")
    page.get_by_role("button", name="Save").click()
    expect(page.get_by_text("E2E Test Scenario")).to_be_visible(timeout=5_000)


# ── Status bar ─────────────────────────────────────────────────────────────────

def test_status_bar_shows_connected(page: Page):
    """Status bar reflects the connected state."""
    page.goto("/")
    _connect(page)
    expect(page.get_by_text("Connected")).to_be_visible(timeout=10_000)


# ── Fan switching ──────────────────────────────────────────────────────────────


def test_switch_button_visible_after_connect(page: Page):
    """The 'Switch…' button must be shown in the device header once connected."""
    page.goto("/")
    _connect(page)
    expect(page.get_by_role("button", name="Switch")).to_be_visible(timeout=10_000)


def test_switch_reopens_connect_dialog(page: Page):
    """Clicking 'Switch…' must re-open the connect dialog without a full page reload."""
    page.goto("/")
    _connect(page)

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
    _connect(page)
    expect(page.get_by_text("VENT-SIM")).to_be_visible(timeout=10_000)

    page.get_by_role("button", name="Switch").click()

    expect(page.get_by_placeholder("IP address")).to_have_value("127.0.0.1", timeout=5_000)
    expect(page.get_by_placeholder("Device ID")).to_have_value("VENT-SIM", timeout=5_000)


# ── Details modal ───────────────────────────────────────────────────────────────

def _open_details(page: Page) -> None:
    """Click the Details… button to open the fan details modal."""
    page.get_by_role("button", name="Details…").click(timeout=10_000)
    expect(page.get_by_role("dialog", name="Fan details")).to_be_visible(timeout=5_000)


def test_details_button_visible_when_connected(page: Page):
    """Details… button is rendered after connecting."""
    page.goto("/")
    _connect(page, "127.0.0.1", "VENT-SIM")
    expect(page.get_by_role("button", name="Details…")).to_be_visible(timeout=10_000)


def test_details_modal_opens(page: Page):
    """Clicking Details… opens the fan details modal."""
    page.goto("/")
    _connect(page, "127.0.0.1", "VENT-SIM")
    _open_details(page)


def test_details_modal_closes_on_x(page: Page):
    """Clicking the close button hides the fan details modal."""
    page.goto("/")
    _connect(page, "127.0.0.1", "VENT-SIM")
    _open_details(page)
    page.get_by_role("button", name="Close details").click()
    expect(page.get_by_role("dialog", name="Fan details")).not_to_be_visible(timeout=5_000)


# ── Schedule / RTC (inside Details modal) ──────────────────────────────────────

def test_schedule_section_visible_in_details(page: Page):
    """Schedule controls are visible inside the fan details modal."""
    page.goto("/")
    _connect(page, "127.0.0.1", "VENT-SIM")
    _open_details(page)

    expect(page.get_by_role("button", name=re.compile(r"Schedule:", re.IGNORECASE))).to_be_visible(timeout=5_000)
    expect(page.get_by_role("button", name="Edit…")).to_be_visible()
    expect(page.get_by_role("button", name="Sync RTC")).to_be_visible()


def test_schedule_enable_toggle(page: Page):
    """Clicking the Schedule toggle in the details modal changes its pressed state."""
    page.goto("/")
    _connect(page, "127.0.0.1", "VENT-SIM")
    _open_details(page)

    toggle = page.get_by_role("button", name=re.compile(r"Schedule:", re.IGNORECASE))
    expect(toggle).to_be_visible(timeout=5_000)

    initial = toggle.get_attribute("aria-pressed")
    toggle.click()

    expected = "false" if initial == "true" else "true"
    expect(toggle).to_have_attribute("aria-pressed", expected, timeout=8_000)


def test_schedule_editor_opens(page: Page):
    """Clicking 'Edit…' in the details modal opens the schedule editor dialog."""
    page.goto("/")
    _connect(page, "127.0.0.1", "VENT-SIM")
    _open_details(page)

    page.get_by_role("button", name="Edit…").click()
    expect(page.get_by_role("dialog", name="Weekly schedule editor")).to_be_visible()


def test_sync_rtc_button_clickable(page: Page):
    """Sync RTC button in the details modal responds to a click without error."""
    page.goto("/")
    _connect(page, "127.0.0.1", "VENT-SIM")
    _open_details(page)

    sync_btn = page.get_by_role("button", name="Sync RTC")
    expect(sync_btn).to_be_enabled(timeout=5_000)
    sync_btn.click()
    # No error dialog should appear — details modal remains visible
    expect(page.get_by_role("button", name="Sync RTC")).to_be_visible(timeout=5_000)
