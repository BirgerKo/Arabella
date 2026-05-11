#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QtQuickControls2/QQuickStyle>

#include "DeviceService.h"
#include "DiscoveryService.h"
#include "DeviceHistory.h"
#include "ScenarioStore.h"
#include "DeviceViewModel.h"
#include "ScheduleViewModel.h"
#include "ScenarioViewModel.h"

int main(int argc, char *argv[])
{
    QGuiApplication app(argc, argv);
    app.setApplicationName(QStringLiteral("Arabella"));
    app.setOrganizationName(QStringLiteral("Arabella"));

    QQuickStyle::setStyle(QStringLiteral("Cupertino"));

    DeviceService    deviceService;
    DiscoveryService discoveryService;
    DeviceHistory    deviceHistory;
    ScenarioStore    scenarioStore;

    DeviceViewModel  deviceVM(&deviceService, &discoveryService, &deviceHistory);
    ScheduleViewModel scheduleVM(&deviceService);
    ScenarioViewModel scenarioVM(&scenarioStore, &deviceService);

    // Keep scenario ViewModel's current device ID in sync.
    QObject::connect(&deviceVM, &DeviceViewModel::connectionChanged, [&] {
        scenarioVM.setCurrentDeviceId(deviceVM.deviceId());
    });

    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty(QStringLiteral("DeviceVM"),   &deviceVM);
    engine.rootContext()->setContextProperty(QStringLiteral("ScheduleVM"), &scheduleVM);
    engine.rootContext()->setContextProperty(QStringLiteral("ScenarioVM"), &scenarioVM);

    const QUrl url(QStringLiteral("qrc:/Arabella/main.qml"));
    engine.load(url);
    if (engine.rootObjects().isEmpty()) return -1;

    return app.exec();
}
