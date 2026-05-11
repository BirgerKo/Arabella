#pragma once
#include <QJsonObject>
#include <QList>
#include <QObject>
#include <QString>
#include <QStringList>

// ── Domain types ──────────────────────────────────────────────────────────────

struct ScenarioSettings {
    // Tri-state: invalid means "not captured", use isValid() to check.
    bool    powerSet            = false;  bool    power           = false;
    bool    speedSet            = false;  int     speed           = 1;
    bool    manualSpeedSet      = false;  int     manualSpeed     = 0;
    bool    operationModeSet    = false;  int     operationMode   = 0;
    bool    boostActiveSet      = false;  bool    boostActive     = false;
    bool    humiditySensorSet   = false;  int     humiditySensor  = 0;
    bool    humidityThresholdSet= false;  int     humidityThreshold = 60;
};

struct FanSettings {
    QString          deviceId;
    ScenarioSettings settings;
};

struct ScenarioEntry {
    QString           name;
    QList<FanSettings> fans;
};

Q_DECLARE_METATYPE(ScenarioSettings)
Q_DECLARE_METATYPE(FanSettings)
Q_DECLARE_METATYPE(ScenarioEntry)

// ── ScenarioStore ─────────────────────────────────────────────────────────────

/**
 * ScenarioStore — persists fan scenarios to QStandardPaths::AppDataLocation.
 *
 * JSON format (v2) is identical to the Python desktop app so files can be
 * shared between platforms.
 */
class ScenarioStore : public QObject {
    Q_OBJECT
public:
    static constexpr int kMaxScenarios = 10;
    static constexpr int kQuickSlots   = 3;

    explicit ScenarioStore(QObject *parent = nullptr);

    QList<ScenarioEntry> scenarios() const;
    void saveScenario(const ScenarioEntry &entry);
    void deleteScenario(const QString &name);

    QStringList quickSlots(const QString &deviceId) const;
    void setQuickSlots(const QString &deviceId, const QStringList &slots);

signals:
    void dataChanged();

private:
    QList<QJsonObject>          m_scenarios;
    QMap<QString, QStringList>  m_quickSlots;

    QString storePath() const;
    void load();
    void save() const;

    static QJsonObject toJson(const ScenarioEntry &entry);
    static ScenarioEntry fromJson(const QJsonObject &obj);
};
