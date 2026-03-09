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

## Phase 2 — Mobile: iOS and Android

Native apps via **BeeWare / Briefcase** — keeps Python, reuses `blauberg_vento` unchanged.

### Mac development environment setup

| Target | Install on Mac |
|--------|----------------|
| Linux | Docker (already set up) — no extras needed |
| Windows | Parallels/UTM with Windows 11, or GitHub Actions CI |
| iOS | Xcode from Mac App Store + `pip install briefcase` |
| Android | Android Studio (includes JDK 17) + `pip install briefcase` |

### Architecture

- `blauberg_vento/` — reused unchanged (pure Python, no dependencies)
- `ventocontrol/` — GUI layer ported from PyQt6 → **Toga** (BeeWare's widget toolkit)
- Briefcase packages the Toga app for each platform (iOS `.ipa`, Android `.apk`, macOS `.app`, Windows `.exe`, Linux AppImage)

### Estimated porting effort

| Component | Effort |
|-----------|--------|
| MainWindow layout (780 lines) | 20–30 h |
| Scenario dialogs (851 lines) | 25–35 h |
| Custom widgets — PowerButton, StatusLED (266 lines) | 15–20 h |
| Threading: QThread → asyncio/background tasks | 15–25 h |
| Dark theme: QSS → Toga CSS | 10–15 h |
| **Total** | **85–125 h** |

### Briefcase workflow (once Toga port is complete)

```bash
briefcase create ios        # scaffold Xcode project
briefcase build ios         # compile
briefcase run ios           # launch in iPhone Simulator

briefcase create android    # scaffold Gradle project
briefcase build android     # compile APK
briefcase run android       # launch in Android emulator
```
