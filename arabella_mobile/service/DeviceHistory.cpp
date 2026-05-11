#include "DeviceHistory.h"
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QStandardPaths>

DeviceHistory::DeviceHistory(QObject *parent) : QObject(parent)
{
    load();
}

void DeviceHistory::recordConnection(const QString &deviceId, const QString &ip, const QString &password)
{
    for (int i = 0; i < m_entries.size(); ++i) {
        if (m_entries[i].deviceId == deviceId) {
            const QString existingLabel = m_entries[i].label;
            m_entries.removeAt(i);
            m_entries.prepend({deviceId, ip, password, existingLabel});
            save();
            emit dataChanged();
            return;
        }
    }

    if (m_entries.size() >= kMaxEntries)
        m_entries.removeLast();

    m_entries.prepend({deviceId, ip, password, {}});
    save();
    emit dataChanged();
}

void DeviceHistory::setLabel(const QString &deviceId, const QString &label)
{
    for (HistoryEntry &e : m_entries) {
        if (e.deviceId == deviceId) {
            e.label = label;
            save();
            emit dataChanged();
            return;
        }
    }
}

void DeviceHistory::removeEntry(const QString &deviceId)
{
    const int before = m_entries.size();
    m_entries.removeIf([&](const HistoryEntry &e) { return e.deviceId == deviceId; });
    if (m_entries.size() != before) {
        save();
        emit dataChanged();
    }
}

QString DeviceHistory::storePath() const
{
    return QStandardPaths::writableLocation(QStandardPaths::AppDataLocation)
        + QStringLiteral("/device_history.json");
}

void DeviceHistory::load()
{
    QFile f(storePath());
    if (!f.open(QIODevice::ReadOnly)) return;
    QJsonDocument doc = QJsonDocument::fromJson(f.readAll());
    if (doc.isNull()) return;
    for (const QJsonValue &v : doc.array()) {
        QJsonObject o = v.toObject();
        m_entries.append({
            o["device_id"].toString(),
            o["ip"].toString(),
            o["password"].toString(),
            o["label"].toString(),
        });
    }
}

void DeviceHistory::save() const
{
    const QString path = storePath();
    QDir().mkpath(QFileInfo(path).absolutePath());

    QJsonArray arr;
    for (const HistoryEntry &e : m_entries) {
        QJsonObject o;
        o["device_id"] = e.deviceId;
        o["ip"]        = e.ip;
        o["password"]  = e.password;
        o["label"]     = e.label;
        arr.append(o);
    }
    QFile f(path);
    if (f.open(QIODevice::WriteOnly))
        f.write(QJsonDocument(arr).toJson());
}
