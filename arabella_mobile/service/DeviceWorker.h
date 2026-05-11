#pragma once
#include <QList>
#include <QObject>
#include <QString>

// ── Shared data types ─────────────────────────────────────────────────────────

struct DeviceStateSnapshot {
    bool    connected               = false;

    QString deviceId;
    QString ip;
    quint16 unitType                = 0;

    bool    powerValid              = false;  bool    power              = false;
    bool    speedValid              = false;  quint8  speed              = 0;
    bool    manualSpeedValid        = false;  quint8  manualSpeed        = 0;
    bool    operationModeValid      = false;  quint8  operationMode      = 0;
    bool    boostActiveValid        = false;  bool    boostActive        = false;
    bool    boostDelayValid         = false;  quint8  boostDelayMinutes  = 0;
    bool    timerModeValid          = false;  quint8  timerMode          = 0;

    bool    humiditySensorValid     = false;  quint8  humiditySensor     = 0;
    bool    humidityThresholdValid  = false;  quint8  humidityThreshold  = 60;
    bool    currentHumidityValid    = false;  quint8  currentHumidity    = 0;

    bool    fan1RpmValid            = false;  quint16 fan1Rpm            = 0;
    bool    fan2RpmValid            = false;  quint16 fan2Rpm            = 0;

    bool    filterNeedsReplacementValid = false;  bool filterNeedsReplacement = false;
    bool    alarmStatusValid        = false;  quint8  alarmStatus        = 0;

    bool    firmwareValid           = false;
    quint8  firmwareMajor           = 0;
    quint8  firmwareMinor           = 0;

    bool    weeklyScheduleEnabledValid = false;  bool weeklyScheduleEnabled = false;
    bool    cloudPermittedValid     = false;  bool    cloudPermitted     = false;
};

struct DiscoveredDeviceInfo {
    QString ip;
    QString deviceId;
    quint16 unitType      = 0;
    QString unitTypeName;
};

struct SchedulePeriodData {
    int day        = 0;
    int period     = 0;
    int speed      = 0;
    int endHours   = 0;
    int endMinutes = 0;
};

Q_DECLARE_METATYPE(DeviceStateSnapshot)
Q_DECLARE_METATYPE(DiscoveredDeviceInfo)
Q_DECLARE_METATYPE(QList<DiscoveredDeviceInfo>)
Q_DECLARE_METATYPE(QList<SchedulePeriodData>)

// ── DeviceWorker ──────────────────────────────────────────────────────────────

struct VentoClient;

class DeviceWorker : public QObject {
    Q_OBJECT
public:
    explicit DeviceWorker(QObject *parent = nullptr);
    ~DeviceWorker() override;

public slots:
    void doConnect(const QString &host, const QString &deviceId, const QString &password);
    void doPoll();
    void doDisconnect();

    void doSetPower(bool on);
    void doSetSpeed(int speed);
    void doSetManualSpeed(int value);
    void doSetMode(int mode);
    void doSetBoostStatus(bool on);
    void doSetBoostDelay(int minutes);
    void doSetHumiditySensor(int state);
    void doSetHumidityThreshold(int rh);
    void doSetScheduleEnabled(bool enabled);
    void doSetSchedulePeriod(int day, int period, int speed, int endH, int endM);
    void doGetFullSchedule();
    void doSyncRtc();
    void doResetAlarms();
    void doResetFilterTimer();

signals:
    void connected(DeviceStateSnapshot state);
    void connectionFailed(QString message);
    void stateUpdated(DeviceStateSnapshot state);
    void scheduleLoaded(QList<SchedulePeriodData> schedule);
    void commandDone();
    void error(QString message);

private:
    VentoClient *m_client = nullptr;

    DeviceStateSnapshot snapshotFromC(const void *raw) const;
    void runCommand(int ventoStatus);
};
