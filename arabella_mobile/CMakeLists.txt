cmake_minimum_required(VERSION 3.20)
project(ArabellaMobile C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# ── Corrosion (Rust → CMake) ──────────────────────────────────────────────────
include(FetchContent)
FetchContent_Declare(
    Corrosion
    GIT_REPOSITORY https://github.com/corrosion-rs/corrosion.git
    GIT_TAG v0.5
)
FetchContent_MakeAvailable(Corrosion)

# iOS: point Corrosion at the device target triple.
# The simulator slice is handled by a separate XCFramework post-build step.
if(CMAKE_SYSTEM_NAME STREQUAL "iOS")
    corrosion_import_crate(
        MANIFEST_PATH protocol/Cargo.toml
        FLAGS --target aarch64-apple-ios
    )
else()
    corrosion_import_crate(MANIFEST_PATH protocol/Cargo.toml)
endif()

# ── Phase 1 Step 9: C FFI integration test ───────────────────────────────────
# Must be called before any add_subdirectory that contains add_test() calls.
enable_testing()

# ── Phase 2: Qt application layers ───────────────────────────────────────────
find_package(Qt6 QUIET COMPONENTS Core Quick QuickControls2 Concurrent)

if(Qt6_FOUND)
    qt_standard_project_setup()
    add_subdirectory(service)
    add_subdirectory(viewmodel)
    add_subdirectory(ui)
else()
    message(STATUS "Qt6 not found — skipping service/viewmodel/ui targets")
endif()

add_executable(ffi_test tests/ffi_test.c)
target_include_directories(ffi_test PRIVATE protocol/include)
target_link_libraries(ffi_test PRIVATE arabella_protocol pthread dl m)

# Register as a CTest integration test.
# Set ARABELLA_SIM_IP, ARABELLA_SIM_ID, ARABELLA_SIM_PWD to override defaults.
add_test(
    NAME ffi_integration
    COMMAND ffi_test
        "${ARABELLA_SIM_IP}"
        "${ARABELLA_SIM_ID}"
        "${ARABELLA_SIM_PWD}"
)
set_tests_properties(ffi_integration PROPERTIES
    ENVIRONMENT "ARABELLA_SIM_IP=127.0.0.1;ARABELLA_SIM_ID=SIMFAN0000000001;ARABELLA_SIM_PWD=1111"
    LABELS "integration"
    TIMEOUT 30
)
