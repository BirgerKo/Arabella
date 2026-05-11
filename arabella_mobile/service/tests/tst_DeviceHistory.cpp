#include "DeviceHistory.h"
#include <QSignalSpy>
#include <QStandardPaths>
#include <QTest>

class tst_DeviceHistory : public QObject {
    Q_OBJECT

private slots:
    void initTestCase() { QStandardPaths::setTestModeEnabled(true); }

    void init() { QFile::remove(historyPath()); }

    void recordAndRetrieve() {
        DeviceHistory h;
        h.recordConnection("DEV001", "192.168.1.10", "1234");
        QCOMPARE(h.entries().size(), 1);
        QCOMPARE(h.entries()[0].deviceId, QString("DEV001"));
        QCOMPARE(h.entries()[0].ip,       QString("192.168.1.10"));
        QCOMPARE(h.entries()[0].password, QString("1234"));
    }

    void moveToFront() {
        DeviceHistory h;
        h.recordConnection("DEV001", "192.168.1.10", "1111");
        h.recordConnection("DEV002", "192.168.1.11", "2222");
        h.recordConnection("DEV001", "192.168.1.10", "1111");  // reconnect
        QCOMPARE(h.entries().size(), 2);
        QCOMPARE(h.entries()[0].deviceId, QString("DEV001"));  // must be at front
    }

    void maxEntriesEnforced() {
        DeviceHistory h;
        for (int i = 0; i < DeviceHistory::kMaxEntries + 2; ++i)
            h.recordConnection(QStringLiteral("DEV%1").arg(i),
                               "192.168.1.1", "pwd");
        QCOMPARE(h.entries().size(), DeviceHistory::kMaxEntries);
    }

    void setLabelPersists() {
        DeviceHistory h;
        h.recordConnection("DEV001", "192.168.1.10", "1111");
        h.setLabel("DEV001", "Living Room Fan");

        DeviceHistory reload;
        QCOMPARE(reload.entries()[0].label, QString("Living Room Fan"));
    }

    void removeEntry() {
        DeviceHistory h;
        h.recordConnection("DEV001", "192.168.1.10", "1111");
        h.recordConnection("DEV002", "192.168.1.11", "2222");
        h.removeEntry("DEV001");
        QCOMPARE(h.entries().size(), 1);
        QCOMPARE(h.entries()[0].deviceId, QString("DEV002"));
    }

    void dataChangedEmittedOnRecord() {
        DeviceHistory h;
        QSignalSpy spy(&h, &DeviceHistory::dataChanged);
        h.recordConnection("DEV001", "192.168.1.10", "pwd");
        QCOMPARE(spy.count(), 1);
    }

private:
    static QString historyPath() {
        return QStandardPaths::writableLocation(QStandardPaths::AppDataLocation)
               + QStringLiteral("/device_history.json");
    }
};

QTEST_MAIN(tst_DeviceHistory)
#include "tst_DeviceHistory.moc"
