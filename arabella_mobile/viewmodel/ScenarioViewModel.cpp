#include "ScenarioViewModel.h"

ScenarioViewModel::ScenarioViewModel(ScenarioStore *store,
                                     DeviceService *service,
                                     QObject *parent)
    : QAbstractListModel(parent), m_store(store), m_service(service)
{
    connect(m_store, &ScenarioStore::dataChanged, this, &ScenarioViewModel::onStoreChanged);
    refresh();
}

int ScenarioViewModel::rowCount(const QModelIndex &parent) const
{
    if (parent.isValid()) return 0;
    return m_entries.size();
}

QVariant ScenarioViewModel::data(const QModelIndex &index, int role) const
{
    if (!index.isValid() || index.row() >= m_entries.size()) return {};
    if (role == NameRole) return m_entries[index.row()].name;
    return {};
}

QHash<int, QByteArray> ScenarioViewModel::roleNames() const
{
    return {{ NameRole, "name" }};
}

QStringList ScenarioViewModel::quickSlots() const
{
    return m_store->quickSlots(m_currentDeviceId);
}

void ScenarioViewModel::setCurrentDeviceId(const QString &deviceId)
{
    m_currentDeviceId = deviceId;
    emit quickSlotsChanged();
}

void ScenarioViewModel::saveCurrentState(const QString &name,
                                         const QString &deviceId,
                                         const DeviceStateSnapshot &state)
{
    ScenarioSettings s;
    if (state.powerValid)             { s.powerSet = true;             s.power              = state.power; }
    if (state.speedValid)             { s.speedSet = true;             s.speed              = state.speed; }
    if (state.manualSpeedValid)       { s.manualSpeedSet = true;       s.manualSpeed        = state.manualSpeed; }
    if (state.operationModeValid)     { s.operationModeSet = true;     s.operationMode      = state.operationMode; }
    if (state.boostActiveValid)       { s.boostActiveSet = true;       s.boostActive        = state.boostActive; }
    if (state.humiditySensorValid)    { s.humiditySensorSet = true;    s.humiditySensor     = state.humiditySensor; }
    if (state.humidityThresholdValid) { s.humidityThresholdSet = true; s.humidityThreshold  = state.humidityThreshold; }

    ScenarioEntry entry;
    entry.name = name;
    entry.fans = {{ deviceId, s }};
    m_store->saveScenario(entry);
}

void ScenarioViewModel::applyScenario(const QString &name, const QString &deviceId)
{
    for (const ScenarioEntry &e : m_entries) {
        if (e.name == name) {
            for (const FanSettings &fan : e.fans) {
                if (fan.deviceId == deviceId) {
                    applySettings(fan.settings);
                    return;
                }
            }
        }
    }
}

void ScenarioViewModel::deleteScenario(const QString &name)
{
    m_store->deleteScenario(name);
}

void ScenarioViewModel::setQuickSlot(int slot, const QString &name)
{
    QStringList slots = m_store->quickSlots(m_currentDeviceId);
    if (slot >= 0 && slot < slots.size())
        slots[slot] = name;
    m_store->setQuickSlots(m_currentDeviceId, slots);
    emit quickSlotsChanged();
}

void ScenarioViewModel::applyQuickSlot(int slot, const QString &deviceId)
{
    const QStringList slots = m_store->quickSlots(deviceId);
    if (slot < 0 || slot >= slots.size()) return;
    const QString name = slots[slot];
    if (!name.isEmpty())
        applyScenario(name, deviceId);
}

void ScenarioViewModel::renameScenario(const QString &oldName, const QString &newName)
{
    for (ScenarioEntry &e : m_entries) {
        if (e.name == oldName) {
            m_store->deleteScenario(oldName);
            e.name = newName;
            m_store->saveScenario(e);
            return;
        }
    }
}

void ScenarioViewModel::applySettings(const ScenarioSettings &s)
{
    if (s.powerSet)             m_service->setPower(s.power);
    if (s.speedSet && s.speed != 255) m_service->setSpeed(s.speed);
    if (s.manualSpeedSet && s.speedSet && s.speed == 255) m_service->setManualSpeed(s.manualSpeed);
    if (s.operationModeSet)     m_service->setMode(s.operationMode);
    if (s.boostActiveSet)       m_service->setBoostStatus(s.boostActive);
    if (s.humiditySensorSet)    m_service->setHumiditySensor(s.humiditySensor);
    if (s.humidityThresholdSet) m_service->setHumidityThreshold(s.humidityThreshold);
}

void ScenarioViewModel::onStoreChanged()
{
    refresh();
    emit quickSlotsChanged();
}

void ScenarioViewModel::refresh()
{
    beginResetModel();
    m_entries = m_store->scenarios();
    endResetModel();
}
