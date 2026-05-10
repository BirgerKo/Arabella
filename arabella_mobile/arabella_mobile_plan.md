# Arabella Mobile — Implementation Plan

## Goal

A cross-platform mobile app with full feature parity to the `ventocontrol` PyQt6 desktop app,
communicating directly with Blauberg Vento fans using the same UDP protocol as `blauberg_vento/`.

Target platforms (in order):
1. **iOS** (primary)
2. **Android**
3. **SailfishOS**

---

## Framework: Qt/QML (C++)

The SailfishOS requirement is the deciding constraint. Sailfish's native UI toolkit is Silica —
QML built on Qt Quick. Every other serious option (Flutter, React Native, Kotlin Multiplatform)
has no credible SailfishOS path. Qt/QML targets all three platforms natively:

| Framework | iOS | Android | SailfishOS |
|---|---|---|---|
| Qt/QML (C++) | ✓ | ✓ | ✓ Native |
| Flutter | ✓ | ✓ | ✗ (unmaintained community port) |
| React Native | ✓ | ✓ | ✗ |
| Kotlin Multiplatform | ✓ | ✓ | ✗ |

Platform-adaptive style: **Cupertino** on iOS, **Material** on Android, **Silica** on SailfishOS.

---

## Architecture

Clean Architecture — dependencies point strictly inward:

```
QML UI  →  ViewModels (QObject/Q_PROPERTY)  →  Services  →  Protocol (plain C++)
```

### Layers

- **Protocol layer** — pure C++17, no Qt except `QUdpSocket`. Zero knowledge of UI.
  Translates the `blauberg_vento/` Python library (~400 lines, mechanical port).
- **Service layer** — owns `VentoClient`, the 2-second poll timer, and JSON persistence.
- **ViewModel layer** — exposes `Q_PROPERTY` + NOTIFY signals to QML. No business logic.
- **QML UI** — platform-adaptive pages and components.

### Dependency rule

```
┌──────────────────────────────────────────────────────────┐
│  QML UI  (platform-specific style)                       │
├──────────────────────────────────────────────────────────┤
│  ViewModel  (QObject subclasses, Q_PROPERTY + signals)   │
├──────────────────────────────────────────────────────────┤
│  Service  (DeviceService, DiscoveryService, stores)      │
├──────────────────────────────────────────────────────────┤
│  Protocol  (VentoClient, VentoUdpSocket, packets)        │
│  — no Qt above QUdpSocket, no UI knowledge               │
└──────────────────────────────────────────────────────────┘
```

---

## Project Structure

Lives under `arabella_mobile/` in the existing monorepo. All Python code is untouched.

```
arabella_mobile/
├── CMakeLists.txt               Root CMake project
├── CMakePresets.json            Presets: ios / android / sailfish / desktop-debug
│
├── protocol/                    C++ Blauberg Vento protocol library
│   ├── CMakeLists.txt
│   ├── VentoParam.h             Param enum + constexpr metadata table
│   ├── VentoPacketBuilder.h/.cpp
│   ├── VentoPacketParser.h/.cpp
│   ├── VentoUdpSocket.h/.cpp    Wraps QUdpSocket
│   ├── VentoClient.h/.cpp       High-level API (turnOn, setSpeed, setMode, …)
│   ├── DeviceState.h            Plain C++ structs (mirrors blauberg_vento/models.py)
│   └── VentoException.h
│
├── service/                     Use-case / service layer
│   ├── CMakeLists.txt
│   ├── DeviceService.h/.cpp     Owns VentoClient + poll timer
│   ├── DiscoveryService.h/.cpp
│   ├── ScenarioStore.h/.cpp     JSON persistence (schema matches desktop scenarios.json v2)
│   └── DeviceHistory.h/.cpp
│
├── viewmodel/                   QObject ViewModels (QML-facing)
│   ├── CMakeLists.txt
│   ├── DeviceViewModel.h/.cpp
│   ├── ScheduleViewModel.h/.cpp
│   └── ScenarioViewModel.h/.cpp
│
├── ui/                          QML pages
│   ├── main.qml
│   ├── DashboardPage.qml        Power, speed, mode, boost, RPM, quick scenarios
│   ├── ConnectPage.qml          Discovery, history, manual entry
│   ├── SchedulePage.qml         8 day-groups × 4 periods
│   ├── ScenarioPage.qml         Save / apply / rename / delete, quick slots
│   ├── DetailsPage.qml          Boost, humidity, RPM, RTC sync, firmware
│   └── components/
│       ├── PowerButton.qml
│       ├── SpeedControl.qml
│       ├── ModeSelector.qml
│       ├── RpmDisplay.qml
│       └── HumidityWidget.qml
│
├── platform/                    Platform-specific files
│   ├── ios/
│   │   └── Info.plist           NSLocalNetworkUsageDescription, entitlements
│   ├── android/
│   │   └── AndroidManifest.xml  INTERNET + CHANGE_WIFI_MULTICAST_STATE
│   └── sailfish/
│       ├── harbour-arabella.desktop
│       ├── harbour-arabella.spec    RPM spec for Harbour store
│       └── qml/cover/CoverPage.qml Sailfish cover (power state + RPM)
│
└── tests/                       C++ unit tests for protocol layer
    ├── CMakeLists.txt
    ├── test_packet_builder.cpp
    ├── test_packet_parser.cpp
    └── test_checksum.cpp
```

### Scenario file interoperability

The `ScenarioStore` JSON schema is kept identical to the desktop app's
`~/.ventocontrol/scenarios.json` (v2 format) so scenario files can be shared between
the desktop and mobile apps.

---

## Protocol Port (C++ translation of blauberg_vento/)

| Python module | C++ equivalent |
|---|---|
| `parameters.py` | `VentoParam.h` — enum class + constexpr metadata array |
| `protocol.py` | `VentoPacketBuilder` + `VentoPacketParser` |
| `transport.py` | `VentoUdpSocket` using `QUdpSocket` |
| `client.py` | `VentoClient` |
| `models.py` | `DeviceState.h` (plain structs) |
| `exceptions.py` | `VentoException.h` (std::exception subclasses) |

Packet format summary:
- Header: `0xFD 0xFD` + protocol_type(`0x02`) + id_len + id_bytes + pwd_len + pwd_bytes + func_byte
- TLV data markers: `CMD_PAGE(0xFF)`, `CMD_SIZE(0xFE)`, `CMD_NOT_SUP(0xFD)`, `CMD_FUNC(0xFC)`
- Checksum: 16-bit little-endian sum of payload bytes (`sum & 0xFFFF`)
- Discovery: READ with `DEFAULT_DEVICEID` + params `[DEVICE_SEARCH(0x007C), UNIT_TYPE(0x00B9)]`

---

## Implementation Phases

### Phase 1 — C++ protocol library + desktop validation (4–6 weeks)

**Goal:** Protocol library complete and talking to real fans. Tested against the Python library.

1. CMake scaffold with `desktop-debug` preset.
2. Port `parameters.py` → `VentoParam.h` (constexpr metadata table).
3. Port `protocol.py` → `VentoPacketBuilder` + `VentoPacketParser`.
4. Port `transport.py` → `VentoUdpSocket` (QUdpSocket, async `readyRead`).
5. Port `client.py` → `VentoClient` (all high-level methods).
6. Write C++ tests using byte vectors extracted from the Python test suite to guarantee
   byte-for-byte identical output.
7. Build a minimal throwaway Qt Widgets desktop app to validate against a real fan or
   the existing Docker simulator.

**Deliverable:** `protocol/` and `service/` compile and pass tests on Linux/macOS.

---

### Phase 2 — iOS application (6–8 weeks)

**Goal:** Feature-complete iOS app.

1. Add iOS CMakePreset (`CMAKE_SYSTEM_NAME: iOS`, Qt 6.6+).
2. Implement `DeviceViewModel`, `ScheduleViewModel`, `ScenarioViewModel`.
3. Build QML pages in order: Dashboard → Connect → Details → Schedule → Scenarios.
4. Style: `QtQuick.Controls 2` with `style: "Cupertino"` in `qtquickcontrols2.conf`.
5. UDP broadcast: configure `NSLocalNetworkUsageDescription` + `com.apple.security.network.client`
   entitlement. Test on a physical device (Simulator has a different network stack).
6. Persistence: write to `QStandardPaths::AppDataLocation`.

**Note on UDP broadcast on iOS 14+:** The system shows a one-time permission prompt before
allowing broadcast UDP. Manual connect (IP + device_id + password) is a fully viable fallback
and must be a first-class path regardless.

**Deliverable:** IPA running on a physical iPhone with all ventocontrol features.

---

### Phase 3 — Android application (3–4 weeks)

Largely free given Phase 2 is complete.

1. Add Android CMakePreset. Switch style to `Material`.
2. `AndroidManifest.xml`: `INTERNET` + `CHANGE_WIFI_MULTICAST_STATE` permissions.
3. `CHANGE_WIFI_MULTICAST_STATE` requires a `WifiManager.MulticastLock` — implement via
   thin JNI bridge or Qt Android extras to acquire/release on app foreground/background.
4. Build via `qt-cmake` with Android NDK.

**Deliverable:** APK deployable to Google Play.

---

### Phase 4 — SailfishOS application (3–5 weeks)

1. Add Sailfish CMakePreset (Mer toolchain, armv7hl / aarch64 cross-compile).
2. Protocol layer requires no changes (`QUdpSocket` unchanged since Qt 5.2).
3. QML shim: a build-time `PLATFORM_SAILFISH` define selects `Sailfish.Silica.ApplicationWindow`
   + `PageStack` instead of `QtQuick.Controls 2` equivalents. Each page gets a Silica variant
   (`DashboardPage.sailfish.qml`) selected via a QML platform singleton.
4. Background behaviour: polling must stop when the app is backgrounded
   (bind to `Qt.application.state`). Required by Harbour submission rules.
5. Cover page: `CoverPage.qml` shows current power state and fan RPM when minimised.
6. Package as RPM (`harbour-arabella.spec`).

**Deliverable:** RPM installable from Harbour or via `pkcon install-local`.

---

## Key Risks and Mitigations

| Risk | Mitigation |
|---|---|
| iOS UDP broadcast requires user permission (iOS 14+) | Manual connect is a full first-class path; discovery is a convenience |
| SailfishOS requires Qt 5.6 — must not use Qt 6-only API in shared layers | Keep `protocol/` on stable Qt 5.2-era API; `QUdpSocket` is unchanged |
| Schedule read = 32 UDP round-trips, worst-case ~2 min | Load lazily on Schedule page navigation; show per-period progress indicator |
| Protocol C++ translation bugs (checksum, CMD_PAGE boundaries) | Phase 1 tests assert byte-for-byte identical output vs Python library |
| Scenario file sharing between desktop and mobile | JSON schema is identical (v2 format); export/import via share sheet as future enhancement |

---

## On the REST Bridge Option

The `webdashboard` FastAPI backend could replace the protocol layer — the app calls REST
endpoints instead of UDP directly. This would allow any framework for the mobile app.

However it introduces a hard infrastructure dependency: the backend must always be running
on the local network, which breaks direct-to-fan WiFi AP mode (used during initial device
setup) and makes the app unusable without a home server.

**Decision:** Direct UDP is the primary connection mode. The REST bridge is an optional
secondary mode (selectable per device) for users who have deployed the webdashboard backend.

---

## Key Source Files (Reference)

- `blauberg_vento/protocol.py` — packet build/parse logic to port
- `blauberg_vento/client.py` — high-level client API to port
- `blauberg_vento/parameters.py` — parameter enum and metadata to port
- `ventocontrol/controllers/device_worker.py` — polling and command architecture
- `ventocontrol/scenarios.py` — scenario JSON schema (v2)
- `tests/test_protocol.py` — reference byte vectors for C++ test suite
