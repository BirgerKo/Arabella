#pragma once
#include <QList>
#include <QObject>
#include <QString>

struct HistoryEntry {
    QString deviceId;
    QString ip;
    QString password;
    QString label;   // user-supplied nickname (may be empty)
};

Q_DECLARE_METATYPE(HistoryEntry)

/**
 * DeviceHistory — persists recently connected fans so the Connect page
 * can offer a one-tap reconnect list.
 */
class DeviceHistory : public QObject {
    Q_OBJECT
public:
    static constexpr int kMaxEntries = 10;

    explicit DeviceHistory(QObject *parent = nullptr);

    QList<HistoryEntry> entries() const { return m_entries; }

    void recordConnection(const QString &deviceId, const QString &ip, const QString &password);
    void setLabel(const QString &deviceId, const QString &label);
    void removeEntry(const QString &deviceId);

signals:
    void dataChanged();

private:
    QList<HistoryEntry> m_entries;

    QString storePath() const;
    void load();
    void save() const;
};
