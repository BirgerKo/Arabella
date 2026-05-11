#include "ScenarioStore.h"
#include <QStandardPaths>
#include <QTest>

class tst_ScenarioStore : public QObject {
    Q_OBJECT

private slots:
    void initTestCase() { QStandardPaths::setTestModeEnabled(true); }

    void init() {
        // Start each test with a clean store by deleting any leftover file.
        QFile::remove(storePath());
    }

    void saveAndLoad() {
        ScenarioStore store;
        ScenarioEntry e;
        e.name = "Night";
        ScenarioSettings s;
        s.powerSet = true; s.power = false;
        s.speedSet = true; s.speed = 1;
        e.fans = {{"DEV001", s}};
        store.saveScenario(e);

        ScenarioStore reload;
        const auto scenarios = reload.scenarios();
        QCOMPARE(scenarios.size(), 1);
        QCOMPARE(scenarios[0].name, QString("Night"));
        QCOMPARE(scenarios[0].fans.size(), 1);
        QVERIFY(scenarios[0].fans[0].settings.powerSet);
        QCOMPARE(scenarios[0].fans[0].settings.power, false);
        QCOMPARE(scenarios[0].fans[0].settings.speed, 1);
    }

    void overwriteByName() {
        ScenarioStore store;
        ScenarioEntry e;
        e.name = "Day";
        ScenarioSettings s1; s1.speedSet = true; s1.speed = 1;
        e.fans = {{"DEV001", s1}};
        store.saveScenario(e);

        ScenarioSettings s2; s2.speedSet = true; s2.speed = 3;
        e.fans = {{"DEV001", s2}};
        store.saveScenario(e);  // same name → overwrite

        const auto scenarios = store.scenarios();
        QCOMPARE(scenarios.size(), 1);
        QCOMPARE(scenarios[0].fans[0].settings.speed, 3);
    }

    void capEnforcedAt10() {
        ScenarioStore store;
        for (int i = 0; i < ScenarioStore::kMaxScenarios + 1; ++i) {
            ScenarioEntry e;
            e.name = QStringLiteral("S%1").arg(i);
            store.saveScenario(e);
        }
        QCOMPARE(store.scenarios().size(), ScenarioStore::kMaxScenarios);
    }

    void evictsOldestOnCap() {
        ScenarioStore store;
        // Fill to cap
        for (int i = 0; i < ScenarioStore::kMaxScenarios; ++i) {
            ScenarioEntry e; e.name = QStringLiteral("S%1").arg(i);
            store.saveScenario(e);
        }
        // One more should evict "S0"
        ScenarioEntry extra; extra.name = "Extra";
        store.saveScenario(extra);
        const auto names = store.scenarios();
        QVERIFY(std::none_of(names.begin(), names.end(),
            [](const ScenarioEntry &e){ return e.name == "S0"; }));
        QCOMPARE(names.last().name, QString("Extra"));
    }

    void deleteRemovesEntry() {
        ScenarioStore store;
        ScenarioEntry e; e.name = "ToDelete";
        store.saveScenario(e);
        store.deleteScenario("ToDelete");
        QVERIFY(store.scenarios().isEmpty());
    }

    void deleteRemovesFromQuickSlots() {
        ScenarioStore store;
        ScenarioEntry e; e.name = "Quick";
        store.saveScenario(e);
        store.setQuickSlots("DEV001", {"Quick", "", ""});
        store.deleteScenario("Quick");
        const auto slotNames = store.quickSlots("DEV001");
        QVERIFY(slotNames[0].isEmpty());
    }

    void quickSlotsRoundTrip() {
        ScenarioStore store;
        store.setQuickSlots("DEV001", {"Morning", "Night", ""});
        const auto slotNames = store.quickSlots("DEV001");
        QCOMPARE(slotNames.size(), ScenarioStore::kQuickSlots);
        QCOMPARE(slotNames[0], QString("Morning"));
        QCOMPARE(slotNames[1], QString("Night"));
        QVERIFY(slotNames[2].isEmpty());
    }

    void v1MigrationLoadsEntries() {
        // Write a v1-format file and verify it migrates.
        const QString path = storePath();
        QDir().mkpath(QFileInfo(path).absolutePath());
        QFile f(path);
        QVERIFY(f.open(QIODevice::WriteOnly));
        const QByteArray v1 = R"({
            "version": 1,
            "devices": {
                "DEV001": {
                    "scenarios": [{"name":"OldScenario","settings":{"speed":2}}],
                    "quick_slots": ["OldScenario", null, null]
                }
            }
        })";
        f.write(v1);
        f.close();

        ScenarioStore store;
        const auto scenarios = store.scenarios();
        QCOMPARE(scenarios.size(), 1);
        QCOMPARE(scenarios[0].name, QString("OldScenario"));
    }

private:
    static QString storePath() {
        return QStandardPaths::writableLocation(QStandardPaths::AppDataLocation)
               + QStringLiteral("/scenarios.json");
    }
};

QTEST_MAIN(tst_ScenarioStore)
#include "tst_ScenarioStore.moc"
