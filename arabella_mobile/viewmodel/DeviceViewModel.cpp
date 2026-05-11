#include "DeviceViewModel.h"

DeviceViewModel::DeviceViewModel(DeviceService *service,
                                 DiscoveryService *discovery,
                                 DeviceHistory *history,
                                 QObject *parent)
    : QObject(parent), m_service(service), m_discovery(discovery), m_history(history)
{
    connect(m_service, &DeviceService::connectedToDevice, this, &DeviceViewModel::onConnected);
    connect(m_service, &DeviceService::connectionFailed,  this, &DeviceViewModel::onConnectionFailed);
    connect(m_service, &DeviceService::stateUpdated,      this, &DeviceViewModel::onStateUpdated);
    connect(m_service, &DeviceService::serviceError,      this, &DeviceViewModel::onServiceError);
    connect(m_discovery, &DiscoveryService::discoveryFinished, this, &DeviceViewModel::onDiscoveryFinished);
    connect(m_discovery, &DiscoveryService::discoveryError,    this, &DeviceViewModel::onDiscoveryError);
    connect(m_history, &DeviceHistory::dataChanged, this, &DeviceViewModel::historyChanged);
}

QString DeviceViewModel::firmwareVersion() const
{
    if (!m_state.firmwareValid) return {};
    return QStringLiteral("%1.%2").arg(m_state.firmwareMajor).arg(m_state.firmwareMinor);
}

QVariantList DeviceViewModel::discoveredDevices() const
{
    QVariantList list;
    for (const DiscoveredDeviceInfo &d : m_discovered) {
        QVariantMap m;
        m["deviceId"]     = d.deviceId;
        m["ip"]           = d.ip;
        m["unitType"]     = d.unitType;
        m["unitTypeName"] = d.unitTypeName;
        list.append(m);
    }
    return list;
}

QVariantList DeviceViewModel::historyEntries() const
{
    QVariantList list;
    for (const HistoryEntry &e : m_history->entries()) {
        QVariantMap m;
        m["deviceId"] = e.deviceId;
        m["ip"]       = e.ip;
        m["password"] = e.password;
        m["label"]    = e.label.isEmpty() ? e.deviceId : e.label;
        list.append(m);
    }
    return list;
}

void DeviceViewModel::connectToDevice(const QString &host,
                                      const QString &deviceId,
                                      const QString &password)
{
    m_statusText = QStringLiteral("Connecting…");
    emit statusTextChanged();
    m_service->connectToDevice(host, deviceId, password);
}

void DeviceViewModel::disconnectFromDevice()
{
    m_service->disconnectFromDevice();
    m_state = {};
    m_statusText = QStringLiteral("Disconnected");
    emit connectionChanged();
    emit stateChanged();
    emit statusTextChanged();
}

void DeviceViewModel::startDiscovery()
{
    emit discoveringChanged();
    m_discovery->startDiscovery();
}

void DeviceViewModel::setPower(bool on)               { m_service->setPower(on); }
void DeviceViewModel::setSpeed(int s)                 { m_service->setSpeed(s); }
void DeviceViewModel::setManualSpeed(int v)           { m_service->setManualSpeed(v); }
void DeviceViewModel::setMode(int m)                  { m_service->setMode(m); }
void DeviceViewModel::setBoostStatus(bool on)         { m_service->setBoostStatus(on); }
void DeviceViewModel::setBoostDelay(int min)          { m_service->setBoostDelay(min); }
void DeviceViewModel::setHumiditySensor(int s)        { m_service->setHumiditySensor(s); }
void DeviceViewModel::setHumidityThreshold(int rh)    { m_service->setHumidityThreshold(rh); }
void DeviceViewModel::setScheduleEnabled(bool e)      { m_service->setScheduleEnabled(e); }
void DeviceViewModel::syncRtc()                       { m_service->syncRtc(); }
void DeviceViewModel::resetAlarms()                   { m_service->resetAlarms(); }
void DeviceViewModel::resetFilterTimer()              { m_service->resetFilterTimer(); }

void DeviceViewModel::renameDevice(const QString &deviceId, const QString &label)
{
    m_history->setLabel(deviceId, label);
}

void DeviceViewModel::removeFromHistory(const QString &deviceId)
{
    m_history->removeEntry(deviceId);
}

void DeviceViewModel::onConnected(DeviceStateSnapshot state)
{
    m_history->recordConnection(state.deviceId, state.ip, {});
    m_state = state;
    m_statusText = QStringLiteral("Connected");
    emit connectionChanged();
    emit stateChanged();
    emit deviceInfoChanged();
    emit statusTextChanged();
}

void DeviceViewModel::onConnectionFailed(QString message)
{
    m_statusText = QStringLiteral("Connection failed");
    m_lastError  = message;
    emit statusTextChanged();
    emit lastErrorChanged();
    emit connectionError(message);
}

void DeviceViewModel::onStateUpdated(DeviceStateSnapshot state)
{
    m_state = state;
    emit stateChanged();
}

void DeviceViewModel::onServiceError(QString message)
{
    m_lastError = message;
    emit lastErrorChanged();
}

void DeviceViewModel::onDiscoveryFinished(QList<DiscoveredDeviceInfo> devices)
{
    m_discovered = devices;
    emit discoveredDevicesChanged();
    emit discoveringChanged();
}

void DeviceViewModel::onDiscoveryError(QString message)
{
    m_lastError = message;
    emit lastErrorChanged();
    emit discoveringChanged();
}
