# Arabella — Cross-platform Roadmap

## Current status (macOS)

| Component | Status |
|-----------|--------|
| `blauberg_vento` API | ✅ complete — 78 tests passing |
| `ventocontrol` PyQt6 GUI | ✅ complete — macOS |
| Fan simulator (`ventosim`) | ✅ complete |
| Docker fan containers (3 simulated fans) | ✅ complete — macOS |

---

## Phase 1 — Desktop: Linux and Windows  *(next)*

The PyQt6 GUI already runs on Linux and Windows with no code changes.
Only the Docker simulator discovery needs platform-aware tweaks.

### Files to change (5 files)

| File | Change |
|------|--------|
| `docker-compose.yml` | Remove `ports:` from fan services — makes it the Linux-native base |
| `docker-compose.mac.yml` | **New** — macOS/Windows overlay adding loopback-alias port mappings |
| `ventocontrol/controllers/device_worker.py` | Add `_docker_scan_base()` + update `do_docker_discover()` |
| `Makefile` | **New** — platform-detecting `make up/down/logs/build` targets |
| `tests/test_docker_discover.py` | **New** — 7 tests for `_docker_scan_base()` |

### Key design

```python
def _docker_scan_base() -> str:
    override = os.environ.get("VENTO_DOCKER_SUBNET", "").strip()
    if override:
        return override
    # macOS/Windows: fans mapped to loopback aliases
    # Linux: Docker bridge IPs are routed directly to host
    return "127.0.0" if sys.platform in ("darwin", "win32") else "172.28.0"
```

### Platform behaviour

| Platform | Fan IPs | Setup required |
|----------|---------|----------------|
| Linux | `172.28.0.11–13` (bridge, direct) | `docker compose up -d` |
| macOS | `127.0.0.11–13` (loopback aliases) | `sudo ./setup-loopback.sh` + `make up` |
| Windows | `127.0.0.11–13` (loopback, PowerShell netsh) | see README |

### Testing Linux from macOS

```bash
VENTO_DOCKER_SUBNET=172.28.0 python -c \
  "from ventocontrol.controllers.device_worker import _docker_scan_base; \
   print(_docker_scan_base())"
# → 172.28.0
```

---

## Phase 2 — Mobile: Android and iOS

New UI layer in **QML (Qt Quick)** backed by **PySide6** — keeps Python, reuses
`blauberg_vento` and all backend logic unchanged.  The existing PyQt6 desktop
app continues running on macOS/Windows/Linux alongside the new QML UI.

### Platform support

| Platform | Support | Notes |
|----------|---------|-------|
| macOS | ✅ Full | Works today with PySide6 |
| Windows | ✅ Full | Works today with PySide6 |
| Linux desktop | ✅ Full | Works today with PySide6 |
| Raspberry Pi / embedded | ✅ Excellent | Official Qt Boot-to-Qt for Pi 4 & 5 |
| Android | ✅ Official | PySide6 6.5+ — `pyside6-android-deploy` |
| iOS | ⚠️ In progress | Graphical modules targeted for a future Qt release |

### Architecture

```
blauberg_vento API          ← unchanged (pure Python, zero Qt deps)
ventocontrol/controllers/   ← unchanged (device_worker.py, poller.py)
ventocontrol/qml/           ← NEW: QML UI files (.qml)
ventocontrol/qml_app.py     ← NEW: PySide6 app entry point (replaces app.py for mobile)
```

Python backend exposes signals/properties to QML; QML handles all rendering.
Migration from PyQt6 → PySide6 is minimal — mostly import renames:

```python
# PyQt6                        # PySide6
from PyQt6.QtCore import …  →  from PySide6.QtCore import …
pyqtSignal(…)               →  Signal(…)
pyqtSlot(…)                 →  Slot(…)
```

### Desktop → mobile: changes required in QML

| Concern | Approach |
|---------|----------|
| Touch targets | Minimum 48 × 48 px buttons |
| Platform style | `style: "Material"` (Android) / `"Cupertino"` (iOS) — auto-adapts |
| Screen size | Relative sizing (`parent.width * 0.8`) + `Screen.pixelDensity` |
| Navigation | `StackView` with back-button (Android) / swipe (iOS) |
| Hover states | Replace with pressed/focus states |

### Mac development environment setup

| Target | Install on Mac |
|--------|----------------|
| Linux / Windows / macOS desktop | `pip install pyside6` — no extras needed |
| Android | Android Studio (JDK 17) + Android SDK/NDK · build via **GitHub Actions** (Linux runner) |
| iOS | Xcode from Mac App Store · graphical support targeted for future Qt release |

> **Note:** `pyside6-android-deploy` currently requires a Linux host.
> Use a GitHub Actions `ubuntu-latest` runner to build the Android `.apk`
> from the Mac-based repo without needing a separate Linux machine.

### Estimated effort

| Component | Effort |
|-----------|--------|
| PySide6 migration (import renames across ventocontrol/) | 2–4 h |
| `ventocontrol/qml/` — main screen (speed, mode, boost, status) | 15–25 h |
| `ventocontrol/qml/` — connect dialog + device discovery | 8–12 h |
| `ventocontrol/qml/` — scenario management screens | 15–20 h |
| Responsive layout (phone / tablet / desktop) | 5–8 h |
| Android deployment via GitHub Actions | 4–6 h |
| **Total** | **49–75 h** |

### Deployment workflow

```bash
# Desktop (any platform)
pip install pyside6
python -m ventocontrol.qml_app

# Android (via GitHub Actions ubuntu-latest runner)
pyside6-android-deploy --name Arabella --wheel-pyside6 ...
# → Arabella.apk

# iOS (future — once Qt graphical modules land)
# xcodebuild via Xcode on Mac
```
