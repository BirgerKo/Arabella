#include "ScheduleViewModel.h"
#include "DeviceService.h"
#include "stub_protocol.h"
#include <QSignalSpy>
#include <QStandardPaths>
#include <QTest>

static constexpr int kPollMs = 50;

class tst_ScheduleViewModel : public QObject {
    Q_OBJECT

private slots:
    void initTestCase() { QStandardPaths::setTestModeEnabled(true); }
    void init()    { StubProtocol::reset(); }
    void cleanup() { StubProtocol::reset(); }

    void initiallyNotLoadedAndNotLoading() {
        DeviceService svc(nullptr, kPollMs);
        ScheduleViewModel vm(&svc);
        QVERIFY(!vm.loaded());
        QVERIFY(!vm.loading());
        QCOMPARE(vm.rowCount(), 0);
    }

    void loadSetsLoadingFlagThenClears() {
        VentoDeviceState state{};
        StubProtocol::setNextState(state);

        DeviceService svc(nullptr, kPollMs);
        QSignalSpy connected(&svc, &DeviceService::connectedToDevice);
        svc.connectToDevice("127.0.0.1", "TESTFAN000000001", "1111");
        QTRY_COMPARE(connected.count(), 1);

        ScheduleViewModel vm(&svc);
        vm.load();
        QVERIFY(vm.loading());
        QTRY_VERIFY(vm.loaded());
        QVERIFY(!vm.loading());
    }

    void afterLoadRowCountIs32() {
        // doGetFullSchedule loops: 8 days × 4 periods
        VentoDeviceState state{};
        StubProtocol::setNextState(state);

        DeviceService svc(nullptr, kPollMs);
        QSignalSpy connected(&svc, &DeviceService::connectedToDevice);
        svc.connectToDevice("127.0.0.1", "TESTFAN000000001", "1111");
        QTRY_COMPARE(connected.count(), 1);

        ScheduleViewModel vm(&svc);
        vm.load();
        QTRY_VERIFY(vm.loaded());
        QCOMPARE(vm.rowCount(), 32);
    }

    void modelDataMatchesStubOutput() {
        // Stub vento_get_schedule_period: speed=1, end_hours=(day*3)%24, end_minutes=0
        VentoDeviceState state{};
        StubProtocol::setNextState(state);

        DeviceService svc(nullptr, kPollMs);
        QSignalSpy connected(&svc, &DeviceService::connectedToDevice);
        svc.connectToDevice("127.0.0.1", "TESTFAN000000001", "1111");
        QTRY_COMPARE(connected.count(), 1);

        ScheduleViewModel vm(&svc);
        vm.load();
        QTRY_VERIFY(vm.loaded());

        // Row 0: day=0, period=1 → endHours=0
        const QModelIndex r0 = vm.index(0);
        QCOMPARE(vm.data(r0, ScheduleViewModel::DayRole).toInt(),        0);
        QCOMPARE(vm.data(r0, ScheduleViewModel::PeriodRole).toInt(),     1);
        QCOMPARE(vm.data(r0, ScheduleViewModel::SpeedRole).toInt(),      1);
        QCOMPARE(vm.data(r0, ScheduleViewModel::EndHoursRole).toInt(),   0);
        QCOMPARE(vm.data(r0, ScheduleViewModel::EndMinutesRole).toInt(), 0);

        // Row 8: day=2, period=1 → endHours=6
        const QModelIndex r8 = vm.index(8);
        QCOMPARE(vm.data(r8, ScheduleViewModel::DayRole).toInt(),      2);
        QCOMPARE(vm.data(r8, ScheduleViewModel::EndHoursRole).toInt(), 6);
    }

    void setPeriodUpdatesModelOptimistically() {
        VentoDeviceState state{};
        StubProtocol::setNextState(state);

        DeviceService svc(nullptr, kPollMs);
        QSignalSpy connected(&svc, &DeviceService::connectedToDevice);
        svc.connectToDevice("127.0.0.1", "TESTFAN000000001", "1111");
        QTRY_COMPARE(connected.count(), 1);

        ScheduleViewModel vm(&svc);
        vm.load();
        QTRY_VERIFY(vm.loaded());

        // Row 5: day=1, period=2 (4 periods per day, 0-indexed days)
        vm.setPeriod(1, 2, 3, 22, 30);

        const QModelIndex idx = vm.index(5);
        QCOMPARE(vm.data(idx, ScheduleViewModel::SpeedRole).toInt(),      3);
        QCOMPARE(vm.data(idx, ScheduleViewModel::EndHoursRole).toInt(),   22);
        QCOMPARE(vm.data(idx, ScheduleViewModel::EndMinutesRole).toInt(), 30);

        QTRY_COMPARE(StubProtocol::lastCommand(), std::string("set_schedule_period"));
    }

    void secondLoadWhileLoadingIsIgnored() {
        VentoDeviceState state{};
        StubProtocol::setNextState(state);

        DeviceService svc(nullptr, kPollMs);
        QSignalSpy connected(&svc, &DeviceService::connectedToDevice);
        svc.connectToDevice("127.0.0.1", "TESTFAN000000001", "1111");
        QTRY_COMPARE(connected.count(), 1);

        ScheduleViewModel vm(&svc);
        vm.load();
        vm.load();  // second call while m_loading=true → guard returns early
        QTRY_VERIFY(vm.loaded());
        QCOMPARE(vm.rowCount(), 32);
    }
};

QTEST_MAIN(tst_ScheduleViewModel)
#include "tst_ScheduleViewModel.moc"
