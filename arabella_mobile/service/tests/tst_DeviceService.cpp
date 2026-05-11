#include "DeviceService.h"
#include "stub_protocol.h"
#include <QSignalSpy>
#include <QTest>

// Poll interval kept very short so timer-driven tests finish quickly.
static constexpr int kTestPollMs = 50;

class tst_DeviceService : public QObject {
    Q_OBJECT

private slots:
    void init()    { StubProtocol::reset(); }
    void cleanup() { StubProtocol::reset(); }

    void connectSuccess_emitsConnected() {
        VentoDeviceState state{};
        strncpy(state.device_id, "TESTFAN000000001", 63);
        strncpy(state.ip,        "127.0.0.1",        63);
        state.power_valid = 1; state.power = 1;
        state.speed_valid = 1; state.speed = 2;
        StubProtocol::setNextState(state);

        DeviceService svc(nullptr, kTestPollMs);
        QSignalSpy spy(&svc, &DeviceService::connectedToDevice);

        svc.connectToDevice("127.0.0.1", "TESTFAN000000001", "1111");

        QTRY_COMPARE(spy.count(), 1);
        const DeviceStateSnapshot snap = spy[0][0].value<DeviceStateSnapshot>();
        QVERIFY(snap.connected);
        QCOMPARE(snap.deviceId, QString("TESTFAN000000001"));
        QVERIFY(snap.powerValid);
        QCOMPARE(snap.power, true);
        QCOMPARE(snap.speed, (quint8)2);
    }

    void connectFailure_emitsConnectionFailed() {
        StubProtocol::setGetStateError(ErrConnection, "no route to host");

        DeviceService svc(nullptr, kTestPollMs);
        QSignalSpy spy(&svc, &DeviceService::connectionFailed);

        svc.connectToDevice("10.0.0.1", "TESTFAN000000001", "1111");

        QTRY_COMPARE(spy.count(), 1);
        QVERIFY(!spy[0][0].toString().isEmpty());
    }

    void clientNewFail_emitsConnectionFailed() {
        StubProtocol::setConnectFail(true);

        DeviceService svc(nullptr, kTestPollMs);
        QSignalSpy spy(&svc, &DeviceService::connectionFailed);

        svc.connectToDevice("10.0.0.1", "TESTFAN000000001", "1111");

        QTRY_COMPARE(spy.count(), 1);
    }

    void commandDone_triggersImmediatePoll() {
        VentoDeviceState state{};
        StubProtocol::setNextState(state);

        DeviceService svc(nullptr, kTestPollMs);
        QSignalSpy connected(&svc, &DeviceService::connectedToDevice);
        svc.connectToDevice("127.0.0.1", "TESTFAN000000001", "1111");
        QTRY_COMPARE(connected.count(), 1);

        QSignalSpy updated(&svc, &DeviceService::stateUpdated);
        svc.setPower(true);

        // The command triggers an immediate poll → stateUpdated
        QTRY_VERIFY(updated.count() >= 1);
        QCOMPARE(StubProtocol::lastCommand(), std::string("turn_on"));
    }

    void pollTimerFires_emitsStateUpdated() {
        VentoDeviceState state{};
        StubProtocol::setNextState(state);

        DeviceService svc(nullptr, kTestPollMs);
        QSignalSpy connected(&svc, &DeviceService::connectedToDevice);
        svc.connectToDevice("127.0.0.1", "TESTFAN000000001", "1111");
        QTRY_COMPARE(connected.count(), 1);

        QSignalSpy updated(&svc, &DeviceService::stateUpdated);
        // Wait for at least two poll cycles
        QTRY_VERIFY_WITH_TIMEOUT(updated.count() >= 2, kTestPollMs * 10);
    }

    void disconnectStopsPoll() {
        VentoDeviceState state{};
        StubProtocol::setNextState(state);

        DeviceService svc(nullptr, kTestPollMs);
        QSignalSpy connected(&svc, &DeviceService::connectedToDevice);
        svc.connectToDevice("127.0.0.1", "TESTFAN000000001", "1111");
        QTRY_COMPARE(connected.count(), 1);

        svc.disconnectFromDevice();
        const int countAfterDisconnect = StubProtocol::getStateCount();

        // Wait two poll intervals — count must not grow after disconnect
        QTest::qWait(kTestPollMs * 3);
        QCOMPARE(StubProtocol::getStateCount(), countAfterDisconnect);
    }

    void commandErrorEmitsServiceError() {
        VentoDeviceState state{};
        StubProtocol::setNextState(state);

        DeviceService svc(nullptr, kTestPollMs);
        QSignalSpy connected(&svc, &DeviceService::connectedToDevice);
        svc.connectToDevice("127.0.0.1", "TESTFAN000000001", "1111");
        QTRY_COMPARE(connected.count(), 1);

        StubProtocol::setCommandError(ErrValue, "speed out of range");
        QSignalSpy errors(&svc, &DeviceService::serviceError);
        svc.setSpeed(99);

        QTRY_COMPARE(errors.count(), 1);
        QVERIFY(errors[0][0].toString().contains("speed"));
    }
};

QTEST_MAIN(tst_DeviceService)
#include "tst_DeviceService.moc"
