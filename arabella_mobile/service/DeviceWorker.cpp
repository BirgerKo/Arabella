#include "DeviceWorker.h"
#include "protocol.h"
#include <QDateTime>

DeviceWorker::DeviceWorker(QObject *parent) : QObject(parent)
{
    qRegisterMetaType<DeviceStateSnapshot>();
    qRegisterMetaType<DiscoveredDeviceInfo>();
    qRegisterMetaType<QList<DiscoveredDeviceInfo>>();
    qRegisterMetaType<QList<SchedulePeriodData>>();
}

DeviceWorker::~DeviceWorker()
{
    if (m_client) {
        vento_client_free(m_client);
        m_client = nullptr;
    }
}

void DeviceWorker::doConnect(const QString &host, const QString &deviceId, const QString &password)
{
    if (m_client) {
        vento_client_free(m_client);
        m_client = nullptr;
    }

    m_client = vento_client_new(
        host.toUtf8().constData(),
        deviceId.toUtf8().constData(),
        password.toUtf8().constData()
    );

    if (!m_client) {
        const QString msg = QStringLiteral("Failed to create client: %1").arg(vento_last_error());
        emit error(msg);
        emit connectionFailed(msg);
        return;
    }

    VentoDeviceState state{};
    VentoStatus st = vento_get_state(m_client, &state);
    if (st != Ok) {
        vento_client_free(m_client);
        m_client = nullptr;
        const QString msg = QStringLiteral("Connection failed: %1").arg(vento_last_error());
        emit error(msg);
        emit connectionFailed(msg);
        return;
    }

    emit connected(snapshotFromC(&state));
}

void DeviceWorker::doPoll()
{
    if (!m_client) return;
    VentoDeviceState state{};
    if (vento_get_state(m_client, &state) == Ok)
        emit stateUpdated(snapshotFromC(&state));
    else
        emit error(QStringLiteral("Poll error: %1").arg(vento_last_error()));
}

void DeviceWorker::doDisconnect()
{
    if (m_client) {
        vento_client_free(m_client);
        m_client = nullptr;
    }
}

void DeviceWorker::doSetPower(bool on)       { runCommand(on ? vento_turn_on(m_client) : vento_turn_off(m_client)); }
void DeviceWorker::doSetSpeed(int s)          { runCommand(vento_set_speed(m_client, (uint8_t)s)); }
void DeviceWorker::doSetManualSpeed(int v)    { runCommand(vento_set_manual_speed(m_client, (uint8_t)v)); }
void DeviceWorker::doSetMode(int m)           { runCommand(vento_set_mode(m_client, (uint8_t)m)); }
void DeviceWorker::doSetBoostStatus(bool on)  { runCommand(vento_set_boost_status(m_client, on ? 1 : 0)); }
void DeviceWorker::doSetBoostDelay(int min)   { runCommand(vento_set_boost_delay(m_client, (uint8_t)min)); }
void DeviceWorker::doSetHumiditySensor(int s) { runCommand(vento_set_humidity_sensor(m_client, (uint8_t)s)); }
void DeviceWorker::doSetHumidityThreshold(int rh) { runCommand(vento_set_humidity_threshold(m_client, (uint8_t)rh)); }
void DeviceWorker::doSetScheduleEnabled(bool e) { runCommand(vento_enable_weekly_schedule(m_client, e ? 1 : 0)); }
void DeviceWorker::doResetAlarms()            { runCommand(vento_reset_alarms(m_client)); }
void DeviceWorker::doResetFilterTimer()       { runCommand(vento_reset_filter_timer(m_client)); }

void DeviceWorker::doSetSchedulePeriod(int day, int period, int speed, int endH, int endM)
{
    runCommand(vento_set_schedule_period(m_client,
        (uint8_t)day, (uint8_t)period, (uint8_t)speed, (uint8_t)endH, (uint8_t)endM));
}

void DeviceWorker::doGetFullSchedule()
{
    if (!m_client) {
        emit error(QStringLiteral("Not connected"));
        emit scheduleLoaded({});
        return;
    }
    QList<SchedulePeriodData> result;
    for (int day = 0; day < 8; ++day) {
        for (int period = 1; period <= 4; ++period) {
            VentoSchedulePeriod sp{};
            if (vento_get_schedule_period(m_client, (uint8_t)day, (uint8_t)period, &sp) != Ok) {
                emit error(QStringLiteral("Schedule read error (day %1, period %2): %3")
                    .arg(day).arg(period).arg(vento_last_error()));
                emit scheduleLoaded(result);
                return;
            }
            result.append({day, period, sp.speed, sp.end_hours, sp.end_minutes});
        }
    }
    emit scheduleLoaded(result);
}

void DeviceWorker::doSyncRtc()
{
    if (!m_client) { emit error(QStringLiteral("Not connected")); return; }
    const QDateTime now = QDateTime::currentDateTime();
    VentoRtcInput rtc{};
    rtc.year       = (uint16_t)now.date().year();
    rtc.month      = (uint8_t)now.date().month();
    rtc.day        = (uint8_t)now.date().day();
    rtc.day_of_week= (uint8_t)now.date().dayOfWeek();
    rtc.hour       = (uint8_t)now.time().hour();
    rtc.minute     = (uint8_t)now.time().minute();
    rtc.second     = (uint8_t)now.time().second();
    runCommand(vento_set_rtc(m_client, &rtc));
}

void DeviceWorker::runCommand(int status)
{
    if (status == (int)Ok)
        emit commandDone();
    else
        emit error(QString::fromUtf8(vento_last_error()));
}

DeviceStateSnapshot DeviceWorker::snapshotFromC(const void *raw) const
{
    const auto &s = *static_cast<const VentoDeviceState *>(raw);
    DeviceStateSnapshot snap;
    snap.connected              = true;
    snap.deviceId               = QString::fromUtf8(s.device_id);
    snap.ip                     = QString::fromUtf8(s.ip);
    snap.unitType               = s.unit_type;

    snap.powerValid             = s.power_valid;              snap.power              = s.power;
    snap.speedValid             = s.speed_valid;              snap.speed              = s.speed;
    snap.manualSpeedValid       = s.manual_speed_valid;       snap.manualSpeed        = s.manual_speed;
    snap.operationModeValid     = s.operation_mode_valid;     snap.operationMode      = s.operation_mode;
    snap.boostActiveValid       = s.boost_active_valid;       snap.boostActive        = s.boost_active;
    snap.boostDelayValid        = s.boost_delay_valid;        snap.boostDelayMinutes  = s.boost_delay_minutes;
    snap.timerModeValid         = s.timer_mode_valid;         snap.timerMode          = s.timer_mode;
    snap.humiditySensorValid    = s.humidity_sensor_valid;    snap.humiditySensor     = s.humidity_sensor;
    snap.humidityThresholdValid = s.humidity_threshold_valid; snap.humidityThreshold  = s.humidity_threshold;
    snap.currentHumidityValid   = s.current_humidity_valid;   snap.currentHumidity    = s.current_humidity;
    snap.fan1RpmValid           = s.fan1_rpm_valid;           snap.fan1Rpm            = s.fan1_rpm;
    snap.fan2RpmValid           = s.fan2_rpm_valid;           snap.fan2Rpm            = s.fan2_rpm;
    snap.filterNeedsReplacementValid = s.filter_needs_replacement_valid;
    snap.filterNeedsReplacement = s.filter_needs_replacement;
    snap.alarmStatusValid       = s.alarm_status_valid;       snap.alarmStatus        = s.alarm_status;
    snap.firmwareValid          = s.firmware_valid;
    snap.firmwareMajor          = s.firmware_major;
    snap.firmwareMinor          = s.firmware_minor;
    snap.weeklyScheduleEnabledValid = s.weekly_schedule_enabled_valid;
    snap.weeklyScheduleEnabled  = s.weekly_schedule_enabled;
    snap.cloudPermittedValid    = s.cloud_permitted_valid;    snap.cloudPermitted     = s.cloud_permitted;
    return snap;
}
