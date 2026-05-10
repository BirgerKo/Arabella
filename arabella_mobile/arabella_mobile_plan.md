# Arabella Mobile — Implementation Plan

## Goal

A cross-platform mobile app with full feature parity to the `ventocontrol` PyQt6 desktop app,
communicating directly with Blauberg Vento fans using the same UDP protocol as `blauberg_vento/`.

Target platforms (in order):
1. **iOS** (primary)
2. **Android**
3. **SailfishOS**

---

## Framework: Qt/QML (C++) + Rust protocol layer

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

The **protocol layer is written in Rust** and compiled as a static library. It is the innermost
layer and has zero Qt or UI dependencies — the ideal candidate for Rust's strengths (memory
safety, strong type system, excellent cross-compilation). The service, viewmodel, and UI layers
are C++/Qt as normal.

---

## Architecture

Clean Architecture — dependencies point strictly inward:

```
QML UI  →  ViewModels (QObject/Q_PROPERTY)  →  Services (C++)  →  Protocol (Rust)
```

### Layers

- **Protocol layer (Rust)** — pure Rust, no Qt. UDP sockets via `std::net::UdpSocket` (sync)
  or `tokio::net::UdpSocket` (async). Zero knowledge of UI or framework.
  Translates the `blauberg_vento/` Python library (~400 lines, mechanical port).
  Compiled as a `staticlib`, linked into the Qt/CMake build via **Corrosion**.
- **FFI bridge** — thin `extern "C"` header (or `cxx` crate for safer C++/Rust interop)
  exposing the Rust API to the C++ service layer.
- **Service layer (C++)** — owns the FFI calls into `VentoClient`, the 2-second `QTimer`
  poll, and JSON persistence.
- **ViewModel layer (C++)** — exposes `Q_PROPERTY` + NOTIFY signals to QML. No business logic.
- **QML UI** — platform-adaptive pages and components.

### Dependency rule

```
┌──────────────────────────────────────────────────────────┐
│  QML UI  (platform-specific style)                       │
├──────────────────────────────────────────────────────────┤
│  ViewModel  (QObject subclasses, Q_PROPERTY + signals)   │
├──────────────────────────────────────────────────────────┤
│  Service  (C++: DeviceService, DiscoveryService, stores) │
├──────────────────────────────────────────────────────────┤
│  FFI bridge  (extern "C" or cxx crate)                   │
├──────────────────────────────────────────────────────────┤
│  Protocol  (Rust: VentoClient, packets, UDP socket)      │
│  — no Qt, no UI, compiled as staticlib                   │
└──────────────────────────────────────────────────────────┘
```

### FFI integration

The Rust crate is integrated into CMake via [Corrosion](https://github.com/corrosion-rs/corrosion):

```cmake
find_package(Corrosion REQUIRED)
corrosion_import_crate(MANIFEST_PATH protocol/Cargo.toml)
target_link_libraries(arabella_service PRIVATE arabella_protocol)
```

Two FFI options (choose one at project start):

| Option | Pros | Cons |
|---|---|---|
| `cxx` crate | Safe, compile-time checked, idiomatic | Extra build step, `cxx` dependency |
| `extern "C"` + C header | Simple, no extra deps | Manual, unsafe at boundary |

---

## Project Structure

Lives under `arabella_mobile/` in the existing monorepo. All Python code is untouched.

```
arabella_mobile/
├── CMakeLists.txt               Root CMake project (includes Corrosion)
├── CMakePresets.json            Presets: ios / android / sailfish / desktop-debug
│
├── protocol/                    Rust crate — Blauberg Vento protocol library
│   ├── Cargo.toml
│   ├── build.rs                 cbindgen invocation (generates protocol.h)
│   └── src/
│       ├── lib.rs               Public API + extern "C" exports
│       ├── param.rs             VentoParam enum + metadata table
│       ├── packet.rs            Packet builder + parser
│       ├── transport.rs         UDP socket (std::net or tokio)
│       ├── client.rs            VentoClient (high-level API)
│       ├── models.rs            DeviceState and related structs
│       └── error.rs             VentoError enum
│
├── service/                     C++ use-case / service layer
│   ├── CMakeLists.txt
│   ├── DeviceService.h/.cpp     Owns FFI calls + QTimer poll
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
└── tests/                       Rust unit tests for protocol layer (cargo test)
    └── (inline #[cfg(test)] modules in protocol/src/)
```

### Scenario file interoperability

The `ScenarioStore` JSON schema is kept identical to the desktop app's
`~/.ventocontrol/scenarios.json` (v2 format) so scenario files can be shared between
the desktop and mobile apps.

---

## Protocol Port (Rust translation of blauberg_vento/)

| Python module | Rust equivalent |
|---|---|
| `parameters.py` | `param.rs` — `VentoParam` enum + `ParamMeta` array |
| `protocol.py` | `packet.rs` — `PacketBuilder` + `PacketParser` |
| `transport.py` | `transport.rs` — UDP socket (no Qt dependency) |
| `client.py` | `client.rs` — `VentoClient` (all high-level methods) |
| `models.py` | `models.rs` — `DeviceState` and related structs |
| `exceptions.py` | `error.rs` — `VentoError` enum (thiserror) |

Packet format summary:
- Header: `0xFD 0xFD` + protocol_type(`0x02`) + id_len + id_bytes + pwd_len + pwd_bytes + func_byte
- TLV data markers: `CMD_PAGE(0xFF)`, `CMD_SIZE(0xFE)`, `CMD_NOT_SUP(0xFD)`, `CMD_FUNC(0xFC)`
- Checksum: 16-bit little-endian sum of payload bytes (`sum & 0xFFFF`)
- Discovery: READ with `DEFAULT_DEVICEID` + params `[DEVICE_SEARCH(0x007C), UNIT_TYPE(0x00B9)]`

Rust target triples:

| Platform | Rust target |
|---|---|
| iOS device | `aarch64-apple-ios` |
| iOS Simulator | `aarch64-apple-ios-sim` |
| Android arm64 | `aarch64-linux-android` |
| Android armv7 | `armv7-linux-androideabi` |
| SailfishOS armv7 | `armv7-unknown-linux-gnueabihf` |
| SailfishOS aarch64 | `aarch64-unknown-linux-gnu` |
| Desktop (dev) | host triple |

---

## Implementation Phases

### Phase 1 — Rust protocol library + desktop validation (4–6 weeks)

**Goal:** Rust protocol crate complete and talking to real fans. Tested against the Python library.

1. CMake + Corrosion scaffold with `desktop-debug` preset.
2. Port `parameters.py` → `param.rs` (`VentoParam` enum + `ParamMeta` const array).
3. Port `protocol.py` → `packet.rs` (`PacketBuilder::build`, `PacketParser::parse`).
4. Port `transport.py` → `transport.rs` (UDP socket, no Qt).
5. Port `client.py` → `client.rs` (all high-level methods: `turn_on`, `set_speed`, `set_mode`,
   `sync_rtc`, `get_schedule_period`, etc.).
6. Write Rust tests (`#[cfg(test)]`) using byte vectors extracted from the Python test suite
   to guarantee byte-for-byte identical output. Run with `cargo test`.
7. **Verify SailfishOS cross-compilation first week**: install
   `armv7-unknown-linux-gnueabihf` target, link against the Mer SDK sysroot.
   If blocked, fall back to C++ for the protocol layer before proceeding further.
8. Write the C FFI layer (`extern "C"` exports in `lib.rs`, header generated by `cbindgen`).
9. Build a minimal throwaway Qt Widgets desktop app (C++) that calls the Rust library via FFI
   to validate against a real fan or the existing Docker simulator.

**Deliverable:** `protocol/` Rust crate compiles and passes tests on Linux/macOS; confirmed
cross-compiles to at least one mobile target.

---

### Phase 2 — iOS application (6–8 weeks)

**Goal:** Feature-complete iOS app.

1. Add iOS CMakePreset (`CMAKE_SYSTEM_NAME: iOS`, Qt 6.6+). Configure Corrosion to build
   `aarch64-apple-ios` and `aarch64-apple-ios-sim` targets.
2. Implement `DeviceViewModel`, `ScheduleViewModel`, `ScenarioViewModel` (C++/Qt).
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

1. Add Android CMakePreset. Configure Corrosion for `aarch64-linux-android` and
   `armv7-linux-androideabi`. Switch QML style to `Material`.
2. `AndroidManifest.xml`: `INTERNET` + `CHANGE_WIFI_MULTICAST_STATE` permissions.
3. `CHANGE_WIFI_MULTICAST_STATE` requires a `WifiManager.MulticastLock` — implement via
   thin JNI bridge or Qt Android extras to acquire/release on app foreground/background.
4. Build via `qt-cmake` with Android NDK.

**Deliverable:** APK deployable to Google Play.

---

### Phase 4 — SailfishOS application (3–5 weeks)

1. Add Sailfish CMakePreset (Mer toolchain, armv7hl / aarch64 cross-compile). Rust cross-compile
   to `armv7-unknown-linux-gnueabihf` against the Mer sysroot (validated in Phase 1 step 7).
2. The Rust protocol crate requires no changes for Sailfish — it uses `std::net` with no
   platform-specific code.
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
| SailfishOS Rust cross-compilation (Mer sysroot + armv7 target) | Validate in Phase 1 week 1; fall back to C++ protocol layer if blocked |
| iOS UDP broadcast requires user permission (iOS 14+) | Manual connect is a full first-class path; discovery is a convenience |
| FFI boundary complexity (Rust ↔ C++ string types, error propagation) | Define a minimal, stable C ABI; errors returned as enum codes, not exceptions |
| Schedule read = 32 UDP round-trips, worst-case ~2 min | Load lazily on Schedule page navigation; show per-period progress indicator |
| Protocol translation bugs (checksum, CMD_PAGE boundaries) | Rust tests assert byte-for-byte identical output vs Python library |
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

- `blauberg_vento/protocol.py` — packet build/parse logic to port to Rust
- `blauberg_vento/client.py` — high-level client API to port to Rust
- `blauberg_vento/parameters.py` — parameter enum and metadata to port to Rust
- `ventocontrol/controllers/device_worker.py` — polling and command architecture
- `ventocontrol/scenarios.py` — scenario JSON schema (v2)
- `tests/test_protocol.py` — reference byte vectors for Rust test suite
