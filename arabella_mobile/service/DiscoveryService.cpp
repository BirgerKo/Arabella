#include "DiscoveryService.h"
#include "protocol.h"
#include <QtConcurrent/QtConcurrent>
#include <QFutureWatcher>

DiscoveryService::DiscoveryService(QObject *parent) : QObject(parent) {}

void DiscoveryService::startDiscovery()
{
    if (m_running) return;
    m_running = true;

    auto *watcher = new QFutureWatcher<QList<DiscoveredDeviceInfo>>(this);

    connect(watcher, &QFutureWatcher<QList<DiscoveredDeviceInfo>>::finished, this,
        [this, watcher] {
            m_running = false;
            const auto result = watcher->result();
            if (result.isEmpty())
                emit discoveryError(QStringLiteral("No fans found on the local network"));
            else
                emit discoveryFinished(result);
            watcher->deleteLater();
        });

    watcher->setFuture(QtConcurrent::run([timeout = kTimeoutSecs, max = kMaxDevices] {
        QList<DiscoveredDeviceInfo> found;
        VentoDeviceList list{};
        VentoStatus st = vento_discover(
            "255.255.255.255", 4000,
            timeout, max, &list);

        if (st == Ok && list.devices && list.count > 0) {
            for (quint32 i = 0; i < list.count; ++i) {
                const VentoDiscoveredDevice &d = list.devices[i];
                found.append({
                    QString::fromUtf8(d.ip),
                    QString::fromUtf8(d.device_id),
                    d.unit_type,
                    QString::fromUtf8(d.unit_type_name),
                });
            }
            vento_device_list_free(&list);
        }
        return found;
    }));
}
