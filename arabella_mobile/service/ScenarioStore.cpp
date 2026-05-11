#include "ScenarioStore.h"
#include <QDir>
#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QStandardPaths>

static constexpr int kFileVersion = 2;

ScenarioStore::ScenarioStore(QObject *parent) : QObject(parent)
{
    load();
}

QList<ScenarioEntry> ScenarioStore::scenarios() const
{
    QList<ScenarioEntry> result;
    for (const QJsonObject &obj : m_scenarios) {
        ScenarioEntry e = fromJson(obj);
        if (!e.name.isEmpty())
            result.append(e);
    }
    return result;
}

void ScenarioStore::saveScenario(const ScenarioEntry &entry)
{
    QJsonObject newObj = toJson(entry);

    for (int i = 0; i < m_scenarios.size(); ++i) {
        if (m_scenarios[i]["name"].toString() == entry.name) {
            m_scenarios[i] = newObj;
            save();
            emit dataChanged();
            return;
        }
    }

    if (m_scenarios.size() >= kMaxScenarios) {
        const QString evicted = m_scenarios.takeFirst()["name"].toString();
        for (QStringList &slotList : m_quickSlots) {
            for (QString &slot : slotList) {
                if (slot == evicted) slot.clear();
            }
        }
    }

    m_scenarios.append(newObj);
    save();
    emit dataChanged();
}

void ScenarioStore::deleteScenario(const QString &name)
{
    m_scenarios.removeIf([&](const QJsonObject &o) { return o["name"].toString() == name; });
    for (QStringList &slotList : m_quickSlots) {
        for (QString &slot : slotList) {
            if (slot == name) slot.clear();
        }
    }
    save();
    emit dataChanged();
}

QStringList ScenarioStore::quickSlots(const QString &deviceId) const
{
    QStringList result = m_quickSlots.value(deviceId);
    while (result.size() < kQuickSlots) result.append(QString{});
    return result.mid(0, kQuickSlots);
}

void ScenarioStore::setQuickSlots(const QString &deviceId, const QStringList &slotNames)
{
    m_quickSlots[deviceId] = slotNames.mid(0, kQuickSlots);
    save();
}

QString ScenarioStore::storePath() const
{
    const QString dir = QStandardPaths::writableLocation(QStandardPaths::AppDataLocation);
    return dir + QStringLiteral("/scenarios.json");
}

void ScenarioStore::load()
{
    QFile f(storePath());
    if (!f.open(QIODevice::ReadOnly)) return;

    QJsonDocument doc = QJsonDocument::fromJson(f.readAll());
    if (doc.isNull()) return;
    QJsonObject root = doc.object();

    const int version = root["version"].toInt(1);
    if (version < kFileVersion) {
        // Migrate v1: per-device → global list
        QJsonObject devices = root["devices"].toObject();
        for (const QString &devId : devices.keys()) {
            QJsonObject bucket = devices[devId].toObject();
            for (const QJsonValue &sv : bucket["scenarios"].toArray()) {
                QJsonObject s = sv.toObject();
                QJsonObject fan;
                fan["device_id"] = devId;
                fan["settings"]  = s["settings"];
                QJsonArray fans;
                fans.append(fan);
                QJsonObject entry;
                entry["name"] = s["name"];
                entry["fans"] = fans;
                m_scenarios.append(entry);
            }
            QJsonArray qs = bucket["quick_slots"].toArray();
            QStringList slotList;
            for (const QJsonValue &v : qs) slotList.append(v.toString());
            m_quickSlots[devId] = slotList;
        }
        return;
    }

    for (const QJsonValue &v : root["scenarios"].toArray())
        m_scenarios.append(v.toObject());

    QJsonObject qs = root["quick_slots"].toObject();
    for (const QString &key : qs.keys()) {
        QStringList slotList;
        for (const QJsonValue &v : qs[key].toArray()) slotList.append(v.toString());
        m_quickSlots[key] = slotList;
    }
}

void ScenarioStore::save() const
{
    const QString path = storePath();
    QDir().mkpath(QFileInfo(path).absolutePath());

    QJsonArray scenariosArr;
    for (const QJsonObject &o : m_scenarios) scenariosArr.append(o);

    QJsonObject quickSlotsObj;
    for (auto it = m_quickSlots.begin(); it != m_quickSlots.end(); ++it) {
        QJsonArray arr;
        for (const QString &s : it.value()) arr.append(s);
        quickSlotsObj[it.key()] = arr;
    }

    QJsonObject root;
    root["version"]     = kFileVersion;
    root["scenarios"]   = scenariosArr;
    root["quick_slots"] = quickSlotsObj;

    QFile f(path);
    if (f.open(QIODevice::WriteOnly))
        f.write(QJsonDocument(root).toJson());
}

QJsonObject ScenarioStore::toJson(const ScenarioEntry &entry)
{
    QJsonArray fansArr;
    for (const FanSettings &fan : entry.fans) {
        const ScenarioSettings &s = fan.settings;
        QJsonObject settings;
        if (s.powerSet)             settings["power"]              = s.power;
        if (s.speedSet)             settings["speed"]              = s.speed;
        if (s.manualSpeedSet)       settings["manual_speed"]       = s.manualSpeed;
        if (s.operationModeSet)     settings["operation_mode"]     = s.operationMode;
        if (s.boostActiveSet)       settings["boost_active"]       = s.boostActive;
        if (s.humiditySensorSet)    settings["humidity_sensor"]    = s.humiditySensor;
        if (s.humidityThresholdSet) settings["humidity_threshold"] = s.humidityThreshold;

        QJsonObject fanObj;
        fanObj["device_id"] = fan.deviceId;
        fanObj["settings"]  = settings;
        fansArr.append(fanObj);
    }
    QJsonObject obj;
    obj["name"] = entry.name;
    obj["fans"] = fansArr;
    return obj;
}

ScenarioEntry ScenarioStore::fromJson(const QJsonObject &obj)
{
    ScenarioEntry entry;
    entry.name = obj["name"].toString();
    for (const QJsonValue &v : obj["fans"].toArray()) {
        QJsonObject fanObj = v.toObject();
        QJsonObject s = fanObj["settings"].toObject();

        ScenarioSettings settings;
        if (s.contains("power"))              { settings.powerSet = true;             settings.power              = s["power"].toBool(); }
        if (s.contains("speed"))              { settings.speedSet = true;             settings.speed              = s["speed"].toInt(); }
        if (s.contains("manual_speed"))       { settings.manualSpeedSet = true;       settings.manualSpeed        = s["manual_speed"].toInt(); }
        if (s.contains("operation_mode"))     { settings.operationModeSet = true;     settings.operationMode      = s["operation_mode"].toInt(); }
        if (s.contains("boost_active"))       { settings.boostActiveSet = true;       settings.boostActive        = s["boost_active"].toBool(); }
        if (s.contains("humidity_sensor"))    { settings.humiditySensorSet = true;    settings.humiditySensor     = s["humidity_sensor"].toInt(); }
        if (s.contains("humidity_threshold")) { settings.humidityThresholdSet = true; settings.humidityThreshold  = s["humidity_threshold"].toInt(); }

        entry.fans.append({fanObj["device_id"].toString(), settings});
    }
    return entry;
}
