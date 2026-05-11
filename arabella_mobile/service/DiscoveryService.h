#pragma once
#include "DeviceWorker.h"
#include <QObject>

/**
 * DiscoveryService — UDP broadcast discovery, runs asynchronously via
 * QtConcurrent so the UI never blocks.
 */
class DiscoveryService : public QObject {
    Q_OBJECT
public:
    explicit DiscoveryService(QObject *parent = nullptr);

    bool isRunning() const { return m_running; }

public slots:
    void startDiscovery();

signals:
    void discoveryFinished(QList<DiscoveredDeviceInfo> devices);
    void discoveryError(QString message);

private:
    bool m_running = false;

    static constexpr float  kTimeoutSecs = 1.5f;
    static constexpr quint32 kMaxDevices = 64;
};
