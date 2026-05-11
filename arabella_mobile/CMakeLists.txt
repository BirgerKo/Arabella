cmake_minimum_required(VERSION 3.20)
project(ArabellaMobile C CXX)

# Fetch Corrosion to integrate the Rust protocol crate into CMake
include(FetchContent)
FetchContent_Declare(
    Corrosion
    GIT_REPOSITORY https://github.com/corrosion-rs/corrosion.git
    GIT_TAG v0.5
)
FetchContent_MakeAvailable(Corrosion)

# Import the Rust crate — produces CMake target: arabella_protocol
corrosion_import_crate(MANIFEST_PATH protocol/Cargo.toml)

# ── Phase 1 Step 9: C FFI integration test ───────────────────────────────────
# Requires the Python simulator: python3 -m ventocontrol.simulator
enable_testing()

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

# ── Phase 2+: Qt/service/viewmodel/UI ────────────────────────────────────────
# add_subdirectory(service)
# add_subdirectory(viewmodel)
# add_subdirectory(ui)
