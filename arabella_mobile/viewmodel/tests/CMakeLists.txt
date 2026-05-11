find_package(Qt6 REQUIRED COMPONENTS Core Quick Test)

# Viewmodel sources compiled against arabella_service_stub (stub FFI, no arabella_protocol).
qt_add_library(arabella_viewmodel_stub STATIC
    ${CMAKE_CURRENT_SOURCE_DIR}/../DeviceViewModel.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/../ScheduleViewModel.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/../ScenarioViewModel.cpp
)

target_include_directories(arabella_viewmodel_stub
    PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/..
)

target_link_libraries(arabella_viewmodel_stub
    PUBLIC Qt6::Core Qt6::Quick arabella_service_stub
)

# service/tests contains stub_protocol.h, needed by viewmodel tests.
set(STUB_INCLUDE_DIR ${CMAKE_SOURCE_DIR}/service/tests)

function(add_viewmodel_test name src)
    qt_add_executable(${name} ${src})
    target_include_directories(${name} PRIVATE ${STUB_INCLUDE_DIR})
    target_link_libraries(${name} PRIVATE arabella_viewmodel_stub Qt6::Test)
    add_test(NAME ${name} COMMAND ${name})
endfunction()

add_viewmodel_test(tst_DeviceViewModel   tst_DeviceViewModel.cpp)
add_viewmodel_test(tst_ScheduleViewModel tst_ScheduleViewModel.cpp)
add_viewmodel_test(tst_ScenarioViewModel tst_ScenarioViewModel.cpp)
