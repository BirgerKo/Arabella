#pragma once
#include "protocol.h"
#include <string>

/**
 * StubProtocol — test double for the Rust FFI.
 *
 * Call reset() in every test setUp. Configure the desired behaviour before
 * exercising the code under test, then inspect the recorded calls afterward.
 */
namespace StubProtocol {
    // ── Configuration ─────────────────────────────────────────────────────

    /** State returned by vento_get_state (default: zero-initialised). */
    void setNextState(const VentoDeviceState &state);

    /** Make the next vento_client_new return null (simulates creation failure). */
    void setConnectFail(bool fail);

    /** Make vento_get_state return this error instead of the configured state. */
    void setGetStateError(VentoStatus status, const char *message);

    /** Make all write commands return this error. */
    void setCommandError(VentoStatus status, const char *message);

    /** Make vento_discover return no devices. */
    void setDiscoverEmpty(bool empty);

    // ── Observations ──────────────────────────────────────────────────────

    /** Total number of write-command calls (turn_on/off, set_speed, …). */
    int commandCount();

    /** Name of the most recent write command that was called. */
    std::string lastCommand();

    /** Number of times vento_get_state was called. */
    int getStateCount();

    // ── Lifecycle ─────────────────────────────────────────────────────────

    /** Reset all configuration and counters to defaults. Call in every setUp. */
    void reset();
}
