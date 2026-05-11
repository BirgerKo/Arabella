find_package(Qt6 REQUIRED COMPONENTS Core Test Concurrent)

# Service sources compiled against stub FFI — no dependency on arabella_protocol.
qt_add_library(arabella_service_stub STATIC
    ${CMAKE_CURRENT_SOURCE_DIR}/../DeviceWorker.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/../DeviceService.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/../DiscoveryService.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/../ScenarioStore.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/../DeviceHistory.cpp
    stub_protocol.cpp
)

target_include_directories(arabella_service_stub
    PUBLIC  ${CMAKE_CURRENT_SOURCE_DIR}/..
            ${CMAKE_CURRENT_SOURCE_DIR}
            ${CMAKE_SOURCE_DIR}/protocol/include
)

target_link_libraries(arabella_service_stub
    PUBLIC  Qt6::Core
    PRIVATE Qt6::Concurrent
)

function(add_service_test name src)
    qt_add_executable(${name} ${src})
    target_include_directories(${name} PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
    target_link_libraries(${name} PRIVATE arabella_service_stub Qt6::Test)
    add_test(NAME ${name} COMMAND ${name})
endfunction()

add_service_test(tst_DeviceService tst_DeviceService.cpp)
add_service_test(tst_DeviceHistory tst_DeviceHistory.cpp)
add_service_test(tst_ScenarioStore tst_ScenarioStore.cpp)
