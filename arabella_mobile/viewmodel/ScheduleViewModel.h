#pragma once
#include "DeviceService.h"
#include <QAbstractListModel>
#include <QObject>
#include <QQmlEngine>

/**
 * ScheduleViewModel — exposes the weekly schedule grid (8 day-groups × 4 periods)
 * to QML as a flat list model. Loading is lazy: triggered when the user opens
 * the Schedule page.
 */
class ScheduleViewModel : public QAbstractListModel {
    Q_OBJECT
    QML_ELEMENT
    Q_PROPERTY(bool   loading    READ loading    NOTIFY loadingChanged)
    Q_PROPERTY(bool   loaded     READ loaded     NOTIFY loadedChanged)
    Q_PROPERTY(QString lastError READ lastError  NOTIFY lastErrorChanged)

public:
    enum Roles {
        DayRole    = Qt::UserRole + 1,
        PeriodRole,
        SpeedRole,
        EndHoursRole,
        EndMinutesRole,
    };

    explicit ScheduleViewModel(DeviceService *service, QObject *parent = nullptr);

    // QAbstractListModel
    int      rowCount(const QModelIndex &parent = {}) const override;
    QVariant data(const QModelIndex &index, int role = Qt::DisplayRole) const override;
    QHash<int, QByteArray> roleNames() const override;

    bool    loading()   const { return m_loading; }
    bool    loaded()    const { return m_loaded; }
    QString lastError() const { return m_lastError; }

public slots:
    Q_INVOKABLE void load();
    Q_INVOKABLE void setPeriod(int day, int period, int speed, int endH, int endM);
    Q_INVOKABLE void setScheduleEnabled(bool enabled);

signals:
    void loadingChanged();
    void loadedChanged();
    void lastErrorChanged();

private slots:
    void onScheduleLoaded(QList<SchedulePeriodData> schedule);
    void onServiceError(QString message);

private:
    DeviceService             *m_service;
    QList<SchedulePeriodData>  m_periods;
    bool                       m_loading  = false;
    bool                       m_loaded   = false;
    QString                    m_lastError;
};
