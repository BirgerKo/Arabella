#include "ScheduleViewModel.h"

ScheduleViewModel::ScheduleViewModel(DeviceService *service, QObject *parent)
    : QAbstractListModel(parent), m_service(service)
{
    connect(m_service, &DeviceService::scheduleLoaded, this, &ScheduleViewModel::onScheduleLoaded);
    connect(m_service, &DeviceService::serviceError,   this, &ScheduleViewModel::onServiceError);
}

int ScheduleViewModel::rowCount(const QModelIndex &parent) const
{
    if (parent.isValid()) return 0;
    return m_periods.size();
}

QVariant ScheduleViewModel::data(const QModelIndex &index, int role) const
{
    if (!index.isValid() || index.row() >= m_periods.size()) return {};
    const SchedulePeriodData &p = m_periods[index.row()];
    switch (role) {
    case DayRole:        return p.day;
    case PeriodRole:     return p.period;
    case SpeedRole:      return p.speed;
    case EndHoursRole:   return p.endHours;
    case EndMinutesRole: return p.endMinutes;
    }
    return {};
}

QHash<int, QByteArray> ScheduleViewModel::roleNames() const
{
    return {
        { DayRole,        "day" },
        { PeriodRole,     "period" },
        { SpeedRole,      "speed" },
        { EndHoursRole,   "endHours" },
        { EndMinutesRole, "endMinutes" },
    };
}

void ScheduleViewModel::load()
{
    if (m_loading) return;
    m_loading = true;
    m_loaded  = false;
    emit loadingChanged();
    emit loadedChanged();
    m_service->loadFullSchedule();
}

void ScheduleViewModel::setPeriod(int day, int period, int speed, int endH, int endM)
{
    m_service->setSchedulePeriod(day, period, speed, endH, endM);

    for (SchedulePeriodData &p : m_periods) {
        if (p.day == day && p.period == period) {
            p.speed      = speed;
            p.endHours   = endH;
            p.endMinutes = endM;
            const int row = m_periods.indexOf(p);
            const QModelIndex idx = index(row);
            emit dataChanged(idx, idx, {SpeedRole, EndHoursRole, EndMinutesRole});
            return;
        }
    }
}

void ScheduleViewModel::setScheduleEnabled(bool enabled)
{
    m_service->setScheduleEnabled(enabled);
}

void ScheduleViewModel::onScheduleLoaded(QList<SchedulePeriodData> schedule)
{
    beginResetModel();
    m_periods = schedule;
    endResetModel();
    m_loading = false;
    m_loaded  = true;
    emit loadingChanged();
    emit loadedChanged();
}

void ScheduleViewModel::onServiceError(QString message)
{
    m_loading   = false;
    m_lastError = message;
    emit loadingChanged();
    emit lastErrorChanged();
}
