#include "DeviceService.h"

DeviceService::DeviceService(QObject *parent) : QObject(parent), m_worker(new DeviceWorker)
{
    m_worker->moveToThread(&m_thread);
    m_thread.start();

    // Worker → service
    connect(m_worker, &DeviceWorker::connected,        this, &DeviceService::onConnected);
    connect(m_worker, &DeviceWorker::connectionFailed, this, &DeviceService::onConnectionFailed);
    connect(m_worker, &DeviceWorker::stateUpdated,     this, &DeviceService::onStateUpdated);
    connect(m_worker, &DeviceWorker::scheduleLoaded,   this, &DeviceService::scheduleLoaded);
    connect(m_worker, &DeviceWorker::commandDone,      this, &DeviceService::onCommandDone);
    connect(m_worker, &DeviceWorker::error,            this, &DeviceService::onWorkerError);

    // Service → worker (queued, crosses thread boundary)
    connect(this, &DeviceService::_sigConnect,          m_worker, &DeviceWorker::doConnect,           Qt::QueuedConnection);
    connect(this, &DeviceService::_sigDisconnect,       m_worker, &DeviceWorker::doDisconnect,        Qt::QueuedConnection);
    connect(this, &DeviceService::_sigPoll,             m_worker, &DeviceWorker::doPoll,              Qt::QueuedConnection);
    connect(this, &DeviceService::_sigSetPower,         m_worker, &DeviceWorker::doSetPower,          Qt::QueuedConnection);
    connect(this, &DeviceService::_sigSetSpeed,         m_worker, &DeviceWorker::doSetSpeed,          Qt::QueuedConnection);
    connect(this, &DeviceService::_sigSetManualSpeed,   m_worker, &DeviceWorker::doSetManualSpeed,    Qt::QueuedConnection);
    connect(this, &DeviceService::_sigSetMode,          m_worker, &DeviceWorker::doSetMode,           Qt::QueuedConnection);
    connect(this, &DeviceService::_sigSetBoostStatus,   m_worker, &DeviceWorker::doSetBoostStatus,    Qt::QueuedConnection);
    connect(this, &DeviceService::_sigSetBoostDelay,    m_worker, &DeviceWorker::doSetBoostDelay,     Qt::QueuedConnection);
    connect(this, &DeviceService::_sigSetHumiditySensor,m_worker, &DeviceWorker::doSetHumiditySensor, Qt::QueuedConnection);
    connect(this, &DeviceService::_sigSetHumidityThreshold, m_worker, &DeviceWorker::doSetHumidityThreshold, Qt::QueuedConnection);
    connect(this, &DeviceService::_sigSetScheduleEnabled, m_worker, &DeviceWorker::doSetScheduleEnabled, Qt::QueuedConnection);
    connect(this, &DeviceService::_sigSetSchedulePeriod,m_worker, &DeviceWorker::doSetSchedulePeriod, Qt::QueuedConnection);
    connect(this, &DeviceService::_sigLoadFullSchedule, m_worker, &DeviceWorker::doGetFullSchedule,   Qt::QueuedConnection);
    connect(this, &DeviceService::_sigSyncRtc,          m_worker, &DeviceWorker::doSyncRtc,           Qt::QueuedConnection);
    connect(this, &DeviceService::_sigResetAlarms,      m_worker, &DeviceWorker::doResetAlarms,       Qt::QueuedConnection);
    connect(this, &DeviceService::_sigResetFilterTimer, m_worker, &DeviceWorker::doResetFilterTimer,  Qt::QueuedConnection);

    connect(&m_pollTimer, &QTimer::timeout, this, [this] { emit _sigPoll(); });
}

DeviceService::~DeviceService()
{
    m_pollTimer.stop();
    m_thread.quit();
    m_thread.wait();
    delete m_worker;
}

void DeviceService::connectToDevice(const QString &host, const QString &deviceId, const QString &password)
{
    m_pollTimer.stop();
    m_connected = false;
    emit _sigConnect(host, deviceId, password);
}

void DeviceService::disconnectFromDevice()
{
    m_pollTimer.stop();
    m_connected = false;
    emit _sigDisconnect();
}

void DeviceService::setPower(bool on)                   { emit _sigSetPower(on); }
void DeviceService::setSpeed(int s)                     { emit _sigSetSpeed(s); }
void DeviceService::setManualSpeed(int v)               { emit _sigSetManualSpeed(v); }
void DeviceService::setMode(int m)                      { emit _sigSetMode(m); }
void DeviceService::setBoostStatus(bool on)             { emit _sigSetBoostStatus(on); }
void DeviceService::setBoostDelay(int min)              { emit _sigSetBoostDelay(min); }
void DeviceService::setHumiditySensor(int s)            { emit _sigSetHumiditySensor(s); }
void DeviceService::setHumidityThreshold(int rh)        { emit _sigSetHumidityThreshold(rh); }
void DeviceService::setScheduleEnabled(bool e)          { emit _sigSetScheduleEnabled(e); }
void DeviceService::setSchedulePeriod(int d, int p, int s, int h, int m) { emit _sigSetSchedulePeriod(d, p, s, h, m); }
void DeviceService::loadFullSchedule()                  { emit _sigLoadFullSchedule(); }
void DeviceService::syncRtc()                           { emit _sigSyncRtc(); }
void DeviceService::resetAlarms()                       { emit _sigResetAlarms(); }
void DeviceService::resetFilterTimer()                  { emit _sigResetFilterTimer(); }

void DeviceService::onConnected(DeviceStateSnapshot state)
{
    m_connected = true;
    m_lastState = state;
    m_pollTimer.start(kPollIntervalMs);
    emit connectedToDevice(state);
}

void DeviceService::onConnectionFailed(QString message)
{
    m_connected = false;
    emit connectionFailed(message);
}

void DeviceService::onStateUpdated(DeviceStateSnapshot state)
{
    m_lastState = state;
    emit stateUpdated(state);
}

void DeviceService::onCommandDone()
{
    emit commandDone();
    emit _sigPoll();
}

void DeviceService::onWorkerError(QString message)
{
    emit serviceError(message);
}
