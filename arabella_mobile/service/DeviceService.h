#pragma once
#include "DeviceWorker.h"
#include <QObject>
#include <QThread>
#include <QTimer>

/**
 * DeviceService — owns the connection to one fan.
 *
 * Lives on the main thread. All FFI calls are dispatched to DeviceWorker
 * which runs on a dedicated QThread. The 2-second poll fires on the main
 * thread timer and is forwarded to the worker via a queued signal.
 */
class DeviceService : public QObject {
    Q_OBJECT
public:
    explicit DeviceService(QObject *parent = nullptr, int pollIntervalMs = kPollIntervalMs);
    ~DeviceService() override;

    bool isConnected() const { return m_connected; }
    const DeviceStateSnapshot &lastState() const { return m_lastState; }

public slots:
    void connectToDevice(const QString &host, const QString &deviceId, const QString &password);
    void disconnectFromDevice();

    void setPower(bool on);
    void setSpeed(int speed);
    void setManualSpeed(int value);
    void setMode(int mode);
    void setBoostStatus(bool on);
    void setBoostDelay(int minutes);
    void setHumiditySensor(int state);
    void setHumidityThreshold(int rh);
    void setScheduleEnabled(bool enabled);
    void setSchedulePeriod(int day, int period, int speed, int endH, int endM);
    void loadFullSchedule();
    void syncRtc();
    void resetAlarms();
    void resetFilterTimer();

signals:
    void connectedToDevice(DeviceStateSnapshot state);
    void connectionFailed(QString message);
    void stateUpdated(DeviceStateSnapshot state);
    void scheduleLoaded(QList<SchedulePeriodData> schedule);
    void commandDone();
    void serviceError(QString message);

    // ── Private signals forwarded to worker ──────────────────────────────
    void _sigConnect(QString host, QString deviceId, QString password);
    void _sigDisconnect();
    void _sigPoll();
    void _sigSetPower(bool on);
    void _sigSetSpeed(int speed);
    void _sigSetManualSpeed(int value);
    void _sigSetMode(int mode);
    void _sigSetBoostStatus(bool on);
    void _sigSetBoostDelay(int minutes);
    void _sigSetHumiditySensor(int state);
    void _sigSetHumidityThreshold(int rh);
    void _sigSetScheduleEnabled(bool enabled);
    void _sigSetSchedulePeriod(int day, int period, int speed, int endH, int endM);
    void _sigLoadFullSchedule();
    void _sigSyncRtc();
    void _sigResetAlarms();
    void _sigResetFilterTimer();

private slots:
    void onConnected(DeviceStateSnapshot state);
    void onConnectionFailed(QString message);
    void onStateUpdated(DeviceStateSnapshot state);
    void onCommandDone();
    void onWorkerError(QString message);

private:
    QThread          m_thread;
    DeviceWorker    *m_worker;
    QTimer           m_pollTimer;
    bool             m_connected  = false;
    DeviceStateSnapshot m_lastState;
    int              m_pollInterval;

    static constexpr int kPollIntervalMs = 2000;
};
