# Arabella

Cross-platform support for Blauberg Vento Expert Wi-Fi fans, built on
Blauberg's openly available protocol document (B133-4-1EN-02).
Development is assisted by AI language models.

## Components

| Package | Description |
|---------|-------------|
| `blauberg_vento/` | Pure-Python UDP API library (no dependencies) |
| `ventocontrol/` | PySide6 desktop GUI — macOS, Windows, Linux |
| `ventocontrol/simulator.py` | Software fan simulator for development without hardware |
| `webdashboard/` | React + FastAPI web dashboard — same palette as the desktop GUI |

## Install

```bash
git clone https://github.com/BirgerKo/Arabella.git
cd Arabella
pip install -e ".[dev]"      # API + test dependencies
pip install -e ".[gui]"      # add PyQt6 for the desktop GUI
```

## Quick Start (API)

```python
from blauberg_vento import VentoClient
devices = VentoClient.discover()
client  = VentoClient('192.168.1.50', 'ABCD1234EFGH5678')
state   = client.get_state()
print(state)
client.turn_on()
client.set_speed(2)
```

## Run the GUI

```bash
ventocontrol
```

## Run the Simulator

```bash
ventosim --count 3
```

## Run Tests

```bash
pytest
```

## Features

Both the desktop GUI and web dashboard provide full fan control parity:

| Feature | Desktop GUI | Web Dashboard |
|---------|-------------|---------------|
| Power on/off | ✓ | ✓ |
| Speed (presets 1–3 + manual 0–255) | ✓ | ✓ |
| Operation mode (Ventilation / Heat Recovery / Supply) | ✓ | ✓ |
| Boost toggle | ✓ | ✓ |
| Humidity sensor (Off / On / Invert) + threshold | ✓ | ✓ |
| Real-time fan 1 / fan 2 RPM display | ✓ | ✓ |
| Alarm indicator | ✓ | ✓ |
| Scenario save / apply / quick-slots | ✓ | ✓ |
| Add current fan to existing scenario | ✓ | ✓ |
| IP address shown on hover only | ✓ | ✓ |

## Web Dashboard

### Install dependencies

```bash
pip install -e ".[web]"                     # FastAPI + uvicorn
cd webdashboard/frontend && npm install     # React + Vite
```

### Development (with live reload)

```bash
# Terminal 1 — API backend
python -m webdashboard

# Terminal 2 — Vite dev server (proxies /api and /ws to :8080)
cd webdashboard/frontend && npm run dev
# Open http://localhost:5173
```

### Production build

```bash
cd webdashboard/frontend && npm run build
python -m webdashboard
# Open http://localhost:8080
```

### E2E tests (Playwright)

```bash
pip install pytest-playwright
playwright install chromium
python -m webdashboard &   # start backend first
pytest tests/webdashboard/e2e/ --base-url http://localhost:8080
```

---

## Docker (simulated fans in containers)

```bash
make up      # build images and start 3 virtual fans
make down    # stop containers
make logs    # follow container logs
```

Requires Docker Desktop.
macOS users: also run `sudo ./setup-loopback.sh` once per reboot.
