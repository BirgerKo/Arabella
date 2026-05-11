find_package(Qt6 REQUIRED COMPONENTS Core Quick)

qt_add_library(arabella_viewmodel STATIC
    DeviceViewModel.cpp
    ScheduleViewModel.cpp
    ScenarioViewModel.cpp
)

target_include_directories(arabella_viewmodel PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(arabella_viewmodel PUBLIC Qt6::Core Qt6::Quick arabella_service)
