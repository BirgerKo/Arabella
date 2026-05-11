#pragma once
#include "DeviceService.h"
#include "DeviceHistory.h"
#include "DiscoveryService.h"
#include <QObject>
#include <QQmlEngine>
#include <QString>

/**
 * DeviceViewModel — all device-state Q_PROPERTY bindings consumed by QML.
 *
 * Never contains business logic. Reads state from DeviceService and forwards
 * commands down to it. Also owns DiscoveryService and DeviceHistory for the
 * Connect page.
 */
class DeviceViewModel : public QObject {
    Q_OBJECT
    QML_ELEMENT

    // ── Connection ──────────────────────────────────────────────────────
    Q_PROPERTY(bool   connected   READ connected   NOTIFY connectionChanged)
    Q_PROPERTY(QString statusText  READ statusText  NOTIFY statusTextChanged)
    Q_PROPERTY(QString deviceId    READ deviceId    NOTIFY deviceInfoChanged)
    Q_PROPERTY(QString deviceIp    READ deviceIp    NOTIFY deviceInfoChanged)
    Q_PROPERTY(int     unitType    READ unitType    NOTIFY deviceInfoChanged)

    // ── Power & speed ───────────────────────────────────────────────────
    Q_PROPERTY(bool   power        READ power        NOTIFY stateChanged)
    Q_PROPERTY(int    speed        READ speed        NOTIFY stateChanged)
    Q_PROPERTY(int    manualSpeed  READ manualSpeed  NOTIFY stateChanged)
    Q_PROPERTY(int    mode         READ mode         NOTIFY stateChanged)

    // ── Boost ────────────────────────────────────────────────────────────
    Q_PROPERTY(bool   boostActive      READ boostActive      NOTIFY stateChanged)
    Q_PROPERTY(int    boostDelayMinutes READ boostDelayMinutes NOTIFY stateChanged)

    // ── Humidity ─────────────────────────────────────────────────────────
    Q_PROPERTY(int    humiditySensor    READ humiditySensor    NOTIFY stateChanged)
    Q_PROPERTY(int    humidityThreshold READ humidityThreshold NOTIFY stateChanged)
    Q_PROPERTY(int    currentHumidity   READ currentHumidity   NOTIFY stateChanged)

    // ── RPM ──────────────────────────────────────────────────────────────
    Q_PROPERTY(int    fan1Rpm  READ fan1Rpm  NOTIFY stateChanged)
    Q_PROPERTY(int    fan2Rpm  READ fan2Rpm  NOTIFY stateChanged)

    // ── Schedule ─────────────────────────────────────────────────────────
    Q_PROPERTY(bool   scheduleEnabled READ scheduleEnabled NOTIFY stateChanged)

    // ── Maintenance ──────────────────────────────────────────────────────
    Q_PROPERTY(bool   filterNeedsReplacement READ filterNeedsReplacement NOTIFY stateChanged)
    Q_PROPERTY(int    alarmStatus            READ alarmStatus            NOTIFY stateChanged)
    Q_PROPERTY(QString firmwareVersion       READ firmwareVersion        NOTIFY stateChanged)

    // ── Discovery ────────────────────────────────────────────────────────
    Q_PROPERTY(bool   discovering    READ discovering    NOTIFY discoveringChanged)
    Q_PROPERTY(QVariantList discoveredDevices READ discoveredDevices NOTIFY discoveredDevicesChanged)
    Q_PROPERTY(QVariantList historyEntries    READ historyEntries    NOTIFY historyChanged)

    // ── Error ────────────────────────────────────────────────────────────
    Q_PROPERTY(QString lastError READ lastError NOTIFY lastErrorChanged)

public:
    explicit DeviceViewModel(DeviceService *service,
                             DiscoveryService *discovery,
                             DeviceHistory *history,
                             QObject *parent = nullptr);

    // Property getters
    bool    connected()   const { return m_state.connected; }
    QString statusText()  const { return m_statusText; }
    QString deviceId()    const { return m_state.deviceId; }
    QString deviceIp()    const { return m_state.ip; }
    int     unitType()    const { return m_state.unitType; }

    bool    power()        const { return m_state.power; }
    int     speed()        const { return m_state.speed; }
    int     manualSpeed()  const { return m_state.manualSpeed; }
    int     mode()         const { return m_state.operationMode; }

    bool    boostActive()        const { return m_state.boostActive; }
    int     boostDelayMinutes()  const { return m_state.boostDelayMinutes; }

    int     humiditySensor()    const { return m_state.humiditySensor; }
    int     humidityThreshold() const { return m_state.humidityThreshold; }
    int     currentHumidity()   const { return m_state.currentHumidity; }

    int     fan1Rpm() const { return m_state.fan1Rpm; }
    int     fan2Rpm() const { return m_state.fan2Rpm; }

    bool    scheduleEnabled()       const { return m_state.weeklyScheduleEnabled; }
    bool    filterNeedsReplacement() const { return m_state.filterNeedsReplacement; }
    int     alarmStatus()           const { return m_state.alarmStatus; }
    QString firmwareVersion()       const;

    bool            discovering()       const { return m_discovery->isRunning(); }
    QVariantList    discoveredDevices() const;
    QVariantList    historyEntries()    const;

    QString lastError() const { return m_lastError; }

public slots:
    // Connection
    Q_INVOKABLE void connectToDevice(const QString &host,
                                     const QString &deviceId,
                                     const QString &password);
    Q_INVOKABLE void disconnectFromDevice();
    Q_INVOKABLE void startDiscovery();

    // Power & speed
    Q_INVOKABLE void setPower(bool on);
    Q_INVOKABLE void setSpeed(int speed);
    Q_INVOKABLE void setManualSpeed(int value);
    Q_INVOKABLE void setMode(int mode);

    // Boost
    Q_INVOKABLE void setBoostStatus(bool on);
    Q_INVOKABLE void setBoostDelay(int minutes);

    // Humidity
    Q_INVOKABLE void setHumiditySensor(int state);
    Q_INVOKABLE void setHumidityThreshold(int rh);

    // Schedule
    Q_INVOKABLE void setScheduleEnabled(bool enabled);

    // Maintenance
    Q_INVOKABLE void syncRtc();
    Q_INVOKABLE void resetAlarms();
    Q_INVOKABLE void resetFilterTimer();

    // History
    Q_INVOKABLE void renameDevice(const QString &deviceId, const QString &label);
    Q_INVOKABLE void removeFromHistory(const QString &deviceId);

signals:
    void connectionChanged();
    void statusTextChanged();
    void deviceInfoChanged();
    void stateChanged();
    void discoveringChanged();
    void discoveredDevicesChanged();
    void historyChanged();
    void lastErrorChanged();
    void connectionError(QString message);

private slots:
    void onConnected(DeviceStateSnapshot state);
    void onConnectionFailed(QString message);
    void onStateUpdated(DeviceStateSnapshot state);
    void onServiceError(QString message);
    void onDiscoveryFinished(QList<DiscoveredDeviceInfo> devices);
    void onDiscoveryError(QString message);

private:
    DeviceService    *m_service;
    DiscoveryService *m_discovery;
    DeviceHistory    *m_history;

    DeviceStateSnapshot           m_state;
    QList<DiscoveredDeviceInfo>   m_discovered;
    QString                       m_statusText;
    QString                       m_lastError;
};
