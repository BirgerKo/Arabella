cmake_minimum_required(VERSION 3.20)
project(ArabellaMobile CXX)

# Fetch Corrosion to integrate the Rust protocol crate into CMake
include(FetchContent)
FetchContent_Declare(
    Corrosion
    GIT_REPOSITORY https://github.com/corrosion-rs/corrosion.git
    GIT_TAG v0.5
)
FetchContent_MakeAvailable(Corrosion)

# Import the Rust crate — produces target: arabella_protocol
corrosion_import_crate(MANIFEST_PATH protocol/Cargo.toml)

# Qt/service/viewmodel/UI targets are added in Phase 2+
# add_subdirectory(service)
# add_subdirectory(viewmodel)
# add_subdirectory(ui)
