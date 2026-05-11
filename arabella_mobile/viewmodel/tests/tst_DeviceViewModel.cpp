#include "DeviceViewModel.h"
#include "stub_protocol.h"
#include <QSignalSpy>
#include <QStandardPaths>
#include <QTest>

static constexpr int kPollMs = 50;

class tst_DeviceViewModel : public QObject {
    Q_OBJECT

private slots:
    void initTestCase() { QStandardPaths::setTestModeEnabled(true); }
    void init()    { StubProtocol::reset(); }
    void cleanup() { StubProtocol::reset(); }

    void propertiesReflectConnectedState() {
        VentoDeviceState state{};
        strncpy(state.device_id, "FAN0000000000001", 63);
        strncpy(state.ip,        "192.168.1.5",      63);
        state.power_valid          = 1; state.power          = 1;
        state.speed_valid          = 1; state.speed          = 2;
        state.operation_mode_valid = 1; state.operation_mode = 1;
        state.firmware_valid       = 1;
        state.firmware_major       = 2; state.firmware_minor = 3;
        StubProtocol::setNextState(state);

        DeviceService    svc(nullptr, kPollMs);
        DiscoveryService disc;
        DeviceHistory    hist;
        DeviceViewModel  vm(&svc, &disc, &hist);

        QSignalSpy spy(&vm, &DeviceViewModel::connectionChanged);
        vm.connectToDevice("192.168.1.5", "FAN0000000000001", "1234");
        QTRY_COMPARE(spy.count(), 1);

        QVERIFY(vm.connected());
        QCOMPARE(vm.deviceId(), QString("FAN0000000000001"));
        QCOMPARE(vm.deviceIp(), QString("192.168.1.5"));
        QCOMPARE(vm.power(), true);
        QCOMPARE(vm.speed(), 2);
        QCOMPARE(vm.mode(),  1);
        QCOMPARE(vm.firmwareVersion(), QString("2.3"));
    }

    void firmwareVersionEmptyWhenNotValid() {
        DeviceService svc(nullptr, kPollMs);
        DiscoveryService disc;
        DeviceHistory    hist;
        DeviceViewModel  vm(&svc, &disc, &hist);
        QVERIFY(vm.firmwareVersion().isEmpty());
    }

    void disconnectClearsConnectedFlag() {
        VentoDeviceState state{};
        StubProtocol::setNextState(state);

        DeviceService svc(nullptr, kPollMs);
        DiscoveryService disc;
        DeviceHistory    hist;
        DeviceViewModel  vm(&svc, &disc, &hist);

        QSignalSpy connSpy(&vm, &DeviceViewModel::connectionChanged);
        vm.connectToDevice("127.0.0.1", "TESTFAN000000001", "1111");
        QTRY_COMPARE(connSpy.count(), 1);
        QVERIFY(vm.connected());

        vm.disconnectFromDevice();
        QVERIFY(!vm.connected());
    }

    void connectionFailureEmitsConnectionError() {
        StubProtocol::setConnectFail(true);

        DeviceService svc(nullptr, kPollMs);
        DiscoveryService disc;
        DeviceHistory    hist;
        DeviceViewModel  vm(&svc, &disc, &hist);

        QSignalSpy spy(&vm, &DeviceViewModel::connectionError);
        vm.connectToDevice("10.0.0.1", "TESTFAN000000001", "bad");
        QTRY_COMPARE(spy.count(), 1);
        QVERIFY(!vm.lastError().isEmpty());
    }

    void commandsDelegateToService() {
        VentoDeviceState state{};
        StubProtocol::setNextState(state);

        DeviceService svc(nullptr, kPollMs);
        DiscoveryService disc;
        DeviceHistory    hist;
        DeviceViewModel  vm(&svc, &disc, &hist);

        QSignalSpy connected(&vm, &DeviceViewModel::connectionChanged);
        vm.connectToDevice("127.0.0.1", "TESTFAN000000001", "1111");
        QTRY_COMPARE(connected.count(), 1);

        vm.setPower(true);
        QTRY_COMPARE(StubProtocol::lastCommand(), std::string("turn_on"));

        vm.setSpeed(3);
        QTRY_COMPARE(StubProtocol::lastCommand(), std::string("set_speed"));

        vm.setMode(2);
        QTRY_COMPARE(StubProtocol::lastCommand(), std::string("set_mode"));
    }
};

QTEST_MAIN(tst_DeviceViewModel)
#include "tst_DeviceViewModel.moc"
