# Blauberg Vento — Home Assistant Integration

Home Assistant integration controlling Blauberg Vento Expert Wi-Fi fans via
[blauberg_vento_api](https://github.com/BirgerKo/blauberg_vento_api).

## Install (HACS custom component)

Copy `custom_components/blauberg_vento` into `<config>/custom_components/`,
restart Home Assistant, then add the integration via **Settings → Devices & Services →
Add Integration → Blauberg Vento**. Enter the fan's IP, device ID, and password
(default `1111`).

## Entities per device

- **Fan**: on/off, speed percentage (speed 1–3), preset modes (ventilation, heat recovery, supply)
- **Sensors**: humidity, fan 1/2 RPM (battery voltage on A30 units)
- **Binary sensors**: humidity over threshold, voltage over threshold, relay state, filter needs replacement
- **Numbers**: manual speed (0–255), humidity threshold (40–80)

## Development

```bash
pip install -r requirements_test.txt homeassistant blauberg-vento
pytest
ruff check custom_components tests
mypy custom_components
```

Tests use `pytest-homeassistant-custom-component`, which mirrors the core HA
test harness so they can be ported to `home-assistant/core` with only the
import path changed.

## Roadmap

1. Custom integration (this repo) — done enough to dogfood.
2. Library hardening in `blauberg_vento_api` (typed, async discover).
3. Quality scale silver, HAAL sign-off, then PR to `home-assistant/core`.
