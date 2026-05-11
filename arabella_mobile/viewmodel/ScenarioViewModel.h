#pragma once
#include "ScenarioStore.h"
#include "DeviceService.h"
#include <QAbstractListModel>
#include <QObject>
#include <QQmlEngine>

/**
 * ScenarioViewModel — exposes the scenario list to QML and handles
 * save / apply / delete / quick-slot operations.
 */
class ScenarioViewModel : public QAbstractListModel {
    Q_OBJECT
    QML_ELEMENT
    Q_PROPERTY(QStringList quickSlots READ quickSlots NOTIFY quickSlotsChanged)

public:
    enum Roles {
        NameRole = Qt::UserRole + 1,
    };

    explicit ScenarioViewModel(ScenarioStore *store,
                               DeviceService *service,
                               QObject *parent = nullptr);

    // QAbstractListModel
    int      rowCount(const QModelIndex &parent = {}) const override;
    QVariant data(const QModelIndex &index, int role = Qt::DisplayRole) const override;
    QHash<int, QByteArray> roleNames() const override;

    QStringList quickSlots() const;

public slots:
    Q_INVOKABLE void saveCurrentState(const QString &name,
                                      const QString &deviceId,
                                      const DeviceStateSnapshot &state);
    Q_INVOKABLE void applyScenario(const QString &name, const QString &deviceId);
    Q_INVOKABLE void deleteScenario(const QString &name);
    Q_INVOKABLE void setQuickSlot(int slot, const QString &name);
    Q_INVOKABLE void applyQuickSlot(int slot, const QString &deviceId);
    Q_INVOKABLE void renameScenario(const QString &oldName, const QString &newName);

    void setCurrentDeviceId(const QString &deviceId);

signals:
    void quickSlotsChanged();

private slots:
    void onStoreChanged();

private:
    ScenarioStore        *m_store;
    DeviceService        *m_service;
    QString               m_currentDeviceId;
    QList<ScenarioEntry>  m_entries;

    void applySettings(const ScenarioSettings &s);
    void refresh();
};
