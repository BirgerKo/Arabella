find_package(Qt6 REQUIRED COMPONENTS Core Quick QuickControls2)

qt_add_executable(arabella_app main.cpp)

qt_add_qml_module(arabella_app
    URI Arabella
    VERSION 1.0
    QML_FILES
        main.qml
        DashboardPage.qml
        ConnectPage.qml
        DetailsPage.qml
        SchedulePage.qml
        ScenarioPage.qml
        components/PowerButton.qml
        components/SpeedControl.qml
        components/ModeSelector.qml
        components/RpmDisplay.qml
        components/HumidityWidget.qml
    RESOURCES
        ${CMAKE_SOURCE_DIR}/platform/ios/qtquickcontrols2.conf
)

target_link_libraries(arabella_app
    PRIVATE
        Qt6::Core
        Qt6::Quick
        Qt6::QuickControls2
        arabella_viewmodel
)

if(CMAKE_SYSTEM_NAME STREQUAL "iOS")
    set_target_properties(arabella_app PROPERTIES
        MACOSX_BUNDLE TRUE
        MACOSX_BUNDLE_INFO_PLIST "${CMAKE_SOURCE_DIR}/platform/ios/Info.plist"
        XCODE_ATTRIBUTE_CODE_SIGN_ENTITLEMENTS
            "${CMAKE_SOURCE_DIR}/platform/ios/Arabella.entitlements"
    )
endif()
