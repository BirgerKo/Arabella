# Arabella

Cross-platform support for Blauberg Vento Expert Wi-Fi fans, built on
Blauberg's openly available protocol document (B133-4-1EN-02).
Development is assisted by AI language models.

## Components

| Package | Description |
|---------|-------------|
| `blauberg_vento/` | Pure-Python UDP API library (no dependencies) |
| `ventocontrol/` | PyQt6 desktop GUI — macOS, Windows, Linux |
| `ventocontrol/simulator.py` | Software fan simulator for development without hardware |

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

## Docker (simulated fans in containers)

```bash
make up      # build images and start 3 virtual fans
make down    # stop containers
make logs    # follow container logs
```

Requires Docker Desktop.
macOS users: also run `sudo ./setup-loopback.sh` once per reboot.
