#include "stub_protocol.h"
#include <atomic>
#include <cstring>
#include <mutex>
#include <string>

// ── VentoClient definition (opaque in production; defined here for stub) ─────

struct VentoClient { int id; };

// ── Global stub state ─────────────────────────────────────────────────────────

namespace {
    std::mutex          g_mu;
    VentoDeviceState    g_state         = {};
    bool                g_connectFail   = false;
    bool                g_getStateError = false;
    VentoStatus         g_getStateStatus= ErrConnection;
    bool                g_commandError  = false;
    VentoStatus         g_commandStatus = ErrConnection;
    char                g_errorMsg[256] = {};
    bool                g_discoverEmpty = false;

    std::atomic<int>    g_commandCount{0};
    std::atomic<int>    g_getStateCount{0};
    std::string         g_lastCommand;

    void recordCommand(const char *name) {
        std::lock_guard<std::mutex> lk(g_mu);
        g_lastCommand = name;
        ++g_commandCount;
    }

    VentoStatus commandResult() {
        std::lock_guard<std::mutex> lk(g_mu);
        if (g_commandError)
            return g_commandStatus;
        return Ok;
    }
}

// ── StubProtocol API ─────────────────────────────────────────────────────────

void StubProtocol::setNextState(const VentoDeviceState &state) {
    std::lock_guard<std::mutex> lk(g_mu);
    g_state = state;
    g_getStateError = false;
}

void StubProtocol::setConnectFail(bool fail) {
    std::lock_guard<std::mutex> lk(g_mu);
    g_connectFail = fail;
}

void StubProtocol::setGetStateError(VentoStatus status, const char *msg) {
    std::lock_guard<std::mutex> lk(g_mu);
    g_getStateError = true;
    g_getStateStatus = status;
    strncpy(g_errorMsg, msg, sizeof(g_errorMsg) - 1);
}

void StubProtocol::setCommandError(VentoStatus status, const char *msg) {
    std::lock_guard<std::mutex> lk(g_mu);
    g_commandError = true;
    g_commandStatus = status;
    strncpy(g_errorMsg, msg, sizeof(g_errorMsg) - 1);
}

void StubProtocol::setDiscoverEmpty(bool empty) {
    std::lock_guard<std::mutex> lk(g_mu);
    g_discoverEmpty = empty;
}

int StubProtocol::commandCount()        { return g_commandCount.load(); }
int StubProtocol::getStateCount()       { return g_getStateCount.load(); }
std::string StubProtocol::lastCommand() { std::lock_guard<std::mutex> lk(g_mu); return g_lastCommand; }

void StubProtocol::reset() {
    std::lock_guard<std::mutex> lk(g_mu);
    g_state         = {};
    g_connectFail   = false;
    g_getStateError = false;
    g_commandError  = false;
    g_discoverEmpty = false;
    g_errorMsg[0]   = '\0';
    g_lastCommand.clear();
    g_commandCount.store(0);
    g_getStateCount.store(0);
}

// ── FFI symbol implementations ────────────────────────────────────────────────

const char *vento_last_error() { return g_errorMsg; }

VentoClient *vento_client_new(const char *host, const char *device_id, const char *password)
{
    if (!host || !device_id || !password) return nullptr;
    std::lock_guard<std::mutex> lk(g_mu);
    if (g_connectFail) return nullptr;
    return new VentoClient{1};
}

void vento_client_free(VentoClient *c) { delete c; }

VentoStatus vento_get_state(const VentoClient *, VentoDeviceState *out)
{
    ++g_getStateCount;
    std::lock_guard<std::mutex> lk(g_mu);
    if (g_getStateError) return g_getStateStatus;
    *out = g_state;
    return Ok;
}

// Power
VentoStatus vento_turn_on(const VentoClient *)    { recordCommand("turn_on");    return commandResult(); }
VentoStatus vento_turn_off(const VentoClient *)   { recordCommand("turn_off");   return commandResult(); }
VentoStatus vento_toggle_power(const VentoClient*){ recordCommand("toggle");     return commandResult(); }

// Speed
VentoStatus vento_set_speed(const VentoClient *, uint8_t)        { recordCommand("set_speed");        return commandResult(); }
VentoStatus vento_set_manual_speed(const VentoClient *, uint8_t) { recordCommand("set_manual_speed"); return commandResult(); }
VentoStatus vento_speed_up(const VentoClient *)                  { recordCommand("speed_up");         return commandResult(); }
VentoStatus vento_speed_down(const VentoClient *)                { recordCommand("speed_down");       return commandResult(); }

// Mode
VentoStatus vento_set_mode(const VentoClient *, uint8_t) { recordCommand("set_mode"); return commandResult(); }

// Boost
VentoStatus vento_set_boost_status(const VentoClient *, uint8_t) { recordCommand("set_boost_status"); return commandResult(); }
VentoStatus vento_set_boost_delay(const VentoClient *, uint8_t)  { recordCommand("set_boost_delay");  return commandResult(); }

// Timer
VentoStatus vento_set_timer_mode(const VentoClient *, uint8_t)          { recordCommand("set_timer_mode");  return commandResult(); }
VentoStatus vento_set_night_timer(const VentoClient *, uint8_t, uint8_t){ recordCommand("set_night_timer"); return commandResult(); }
VentoStatus vento_set_party_timer(const VentoClient *, uint8_t, uint8_t){ recordCommand("set_party_timer"); return commandResult(); }

// Humidity
VentoStatus vento_set_humidity_sensor(const VentoClient *, uint8_t)    { recordCommand("set_humidity_sensor");    return commandResult(); }
VentoStatus vento_set_humidity_threshold(const VentoClient *, uint8_t) { recordCommand("set_humidity_threshold"); return commandResult(); }

// Schedule
VentoStatus vento_enable_weekly_schedule(const VentoClient *, uint8_t) { recordCommand("enable_weekly_schedule"); return commandResult(); }
VentoStatus vento_set_schedule_period(const VentoClient *, uint8_t, uint8_t, uint8_t, uint8_t, uint8_t)
{
    recordCommand("set_schedule_period");
    return commandResult();
}
VentoStatus vento_get_schedule_period(const VentoClient *, uint8_t day, uint8_t period, VentoSchedulePeriod *out)
{
    out->period_number = period;
    out->speed      = 1;
    out->end_hours  = (uint8_t)(day * 3 % 24);
    out->end_minutes= 0;
    return Ok;
}

// RTC
VentoStatus vento_set_rtc(const VentoClient *, const VentoRtcInput *) { recordCommand("set_rtc"); return commandResult(); }

// Filter / alarms
VentoStatus vento_reset_filter_timer(const VentoClient *) { recordCommand("reset_filter_timer"); return commandResult(); }
VentoStatus vento_reset_alarms(const VentoClient *)       { recordCommand("reset_alarms");       return commandResult(); }

// Admin
VentoStatus vento_set_cloud_permission(const VentoClient *, uint8_t) { recordCommand("set_cloud_permission"); return commandResult(); }
VentoStatus vento_factory_reset(const VentoClient *)                  { recordCommand("factory_reset");        return commandResult(); }

// Discovery
VentoStatus vento_discover(const char *, uint16_t, double, uint32_t max, VentoDeviceList *out)
{
    std::lock_guard<std::mutex> lk(g_mu);
    if (g_discoverEmpty || max == 0) {
        out->devices = nullptr;
        out->count   = 0;
        return Ok;
    }
    auto *d = new VentoDiscoveredDevice{};
    strncpy(d->ip, "127.0.0.1", 63);
    strncpy(d->device_id, "STUBFAN000000001", 63);
    strncpy(d->unit_type_name, "Stub Fan", 127);
    d->unit_type = 3;
    out->devices = d;
    out->count   = 1;
    return Ok;
}

void vento_device_list_free(VentoDeviceList *list)
{
    if (list && list->devices) {
        delete[] list->devices;
        list->devices = nullptr;
        list->count   = 0;
    }
}
