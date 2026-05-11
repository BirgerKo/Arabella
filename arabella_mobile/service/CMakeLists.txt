find_package(Qt6 REQUIRED COMPONENTS Core Concurrent)

qt_add_library(arabella_service STATIC
    DeviceWorker.cpp
    DeviceService.cpp
    DiscoveryService.cpp
    ScenarioStore.cpp
    DeviceHistory.cpp
)

target_include_directories(arabella_service
    PUBLIC  ${CMAKE_CURRENT_SOURCE_DIR}
    PRIVATE ${CMAKE_SOURCE_DIR}/protocol/include
)

target_link_libraries(arabella_service
    PUBLIC  Qt6::Core
    PRIVATE Qt6::Concurrent arabella_protocol
)

add_subdirectory(tests)
