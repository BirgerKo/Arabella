#include "ScenarioViewModel.h"
#include "ScenarioStore.h"
#include "DeviceService.h"
#include "stub_protocol.h"
#include <QFile>
#include <QSignalSpy>
#include <QStandardPaths>
#include <QTest>

static constexpr int kPollMs = 50;

class tst_ScenarioViewModel : public QObject {
    Q_OBJECT

private slots:
    void initTestCase() { QStandardPaths::setTestModeEnabled(true); }

    void init() {
        StubProtocol::reset();
        removeStoreFile();
    }

    void cleanup() {
        StubProtocol::reset();
        removeStoreFile();
    }

    void saveCurrentStateAddsEntry() {
        ScenarioStore store;
        DeviceService svc(nullptr, kPollMs);
        ScenarioViewModel vm(&store, &svc);

        QCOMPARE(vm.rowCount(), 0);

        DeviceStateSnapshot state;
        state.speedValid = true; state.speed = 2;
        vm.saveCurrentState("Night", "DEV001", state);

        QCOMPARE(vm.rowCount(), 1);
        QCOMPARE(vm.data(vm.index(0), ScenarioViewModel::NameRole).toString(),
                 QString("Night"));
    }

    void deleteScenarioRemovesEntry() {
        ScenarioStore store;
        DeviceService svc(nullptr, kPollMs);
        ScenarioViewModel vm(&store, &svc);

        DeviceStateSnapshot state;
        vm.saveCurrentState("Day", "DEV001", state);
        QCOMPARE(vm.rowCount(), 1);

        vm.deleteScenario("Day");
        QCOMPARE(vm.rowCount(), 0);
    }

    void applyScenarioIssuesCommandsToService() {
        VentoDeviceState devState{};
        StubProtocol::setNextState(devState);

        ScenarioStore store;
        DeviceService svc(nullptr, kPollMs);
        QSignalSpy connected(&svc, &DeviceService::connectedToDevice);
        svc.connectToDevice("127.0.0.1", "TESTFAN000000001", "1111");
        QTRY_COMPARE(connected.count(), 1);

        ScenarioViewModel vm(&store, &svc);
        vm.setCurrentDeviceId("TESTFAN000000001");

        DeviceStateSnapshot snap;
        snap.powerValid = true; snap.power = true;
        vm.saveCurrentState("Morning", "TESTFAN000000001", snap);

        vm.applyScenario("Morning", "TESTFAN000000001");
        QTRY_COMPARE(StubProtocol::lastCommand(), std::string("turn_on"));
    }

    void quickSlotRoundTrip() {
        ScenarioStore store;
        DeviceService svc(nullptr, kPollMs);
        ScenarioViewModel vm(&store, &svc);
        vm.setCurrentDeviceId("DEV001");

        DeviceStateSnapshot state;
        vm.saveCurrentState("Eco", "DEV001", state);

        vm.setQuickSlot(0, "Eco");
        const QStringList slotNames = vm.quickSlots();
        QCOMPARE(slotNames[0], QString("Eco"));
    }

    void renameScenarioUpdatesModel() {
        ScenarioStore store;
        DeviceService svc(nullptr, kPollMs);
        ScenarioViewModel vm(&store, &svc);

        DeviceStateSnapshot state;
        vm.saveCurrentState("OldName", "DEV001", state);
        QCOMPARE(vm.rowCount(), 1);

        vm.renameScenario("OldName", "NewName");

        QCOMPARE(vm.rowCount(), 1);
        QCOMPARE(vm.data(vm.index(0), ScenarioViewModel::NameRole).toString(),
                 QString("NewName"));
    }

    void setCurrentDeviceIdEmitsQuickSlotsChanged() {
        ScenarioStore store;
        DeviceService svc(nullptr, kPollMs);
        ScenarioViewModel vm(&store, &svc);

        QSignalSpy spy(&vm, &ScenarioViewModel::quickSlotsChanged);
        vm.setCurrentDeviceId("DEV002");
        QCOMPARE(spy.count(), 1);
    }

private:
    static void removeStoreFile() {
        QFile::remove(QStandardPaths::writableLocation(QStandardPaths::AppDataLocation)
                      + QStringLiteral("/scenarios.json"));
    }
};

QTEST_MAIN(tst_ScenarioViewModel)
#include "tst_ScenarioViewModel.moc"
