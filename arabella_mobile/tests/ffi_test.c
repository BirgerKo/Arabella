/*
 * Phase 1 Step 9 — C FFI integration test.
 *
 * Exercises every major operation through the C ABI against a live fan
 * or the Python simulator:
 *   cargo run --example connect -- 127.0.0.1 SIMFAN0000000001 1111
 *
 * Usage:
 *   ./ffi_test <ip> <device_id> <password>
 *   ./ffi_test 127.0.0.1 SIMFAN0000000001 1111
 *
 * Exit 0 on full success, 1 on any unexpected failure.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "protocol.h"

/* ── Helpers ──────────────────────────────────────────────────────────────── */

static int g_failures = 0;

static void check_ok(VentoStatus st, const char *op)
{
    if (st == Ok) {
        printf("  %-40s ok\n", op);
    } else {
        fprintf(stderr, "  %-40s FAILED (%d): %s\n", op, (int)st, vento_last_error());
        g_failures++;
    }
}

static void check_err_value(VentoStatus st, const char *op)
{
    if (st == ErrValue) {
        printf("  %-40s correctly rejected: %s\n", op, vento_last_error());
    } else {
        fprintf(stderr, "  %-40s expected ErrValue, got %d\n", op, (int)st);
        g_failures++;
    }
}

static void print_state(const VentoDeviceState *s)
{
    printf("    device_id : %s\n", s->device_id);
    printf("    ip        : %s\n", s->ip);
    printf("    unit_type : %u\n", (unsigned)s->unit_type);

    if (s->power_valid)
        printf("    power     : %s\n", s->power ? "on" : "off");
    if (s->speed_valid)
        printf("    speed     : %u\n", (unsigned)s->speed);
    if (s->manual_speed_valid)
        printf("    manual_sp : %u\n", (unsigned)s->manual_speed);
    if (s->operation_mode_valid)
        printf("    mode      : %u\n", (unsigned)s->operation_mode);
    if (s->humidity_threshold_valid)
        printf("    hum_thr   : %u %%RH\n", (unsigned)s->humidity_threshold);
    if (s->fan1_rpm_valid)
        printf("    fan1_rpm  : %u\n", (unsigned)s->fan1_rpm);
    if (s->fan2_rpm_valid)
        printf("    fan2_rpm  : %u\n", (unsigned)s->fan2_rpm);
    if (s->weekly_schedule_enabled_valid)
        printf("    schedule  : %s\n",
               s->weekly_schedule_enabled ? "enabled" : "disabled");
    if (s->firmware_valid)
        printf("    firmware  : %u.%u\n",
               (unsigned)s->firmware_major, (unsigned)s->firmware_minor);
}

/* ── Main ─────────────────────────────────────────────────────────────────── */

int main(int argc, char *argv[])
{
    if (argc < 4) {
        fprintf(stderr, "Usage: %s <ip> <device_id> <password>\n", argv[0]);
        fprintf(stderr, "  e.g. %s 127.0.0.1 SIMFAN0000000001 1111\n", argv[0]);
        return 1;
    }

    const char *ip        = argv[1];
    const char *device_id = argv[2];
    const char *password  = argv[3];

    printf("=== Arabella FFI C driver — Phase 1 Step 9 ===\n");
    printf("Connecting to %s  id=%s  pwd=%s\n\n", ip, device_id, password);

    /* ── Client creation ──────────────────────────────────────────────────── */
    VentoClient *c = vento_client_new(ip, device_id, password);
    if (!c) {
        fprintf(stderr, "vento_client_new returned null\n");
        return 1;
    }
    printf("  %-40s ok\n", "vento_client_new");

    VentoDeviceState   state;
    VentoSchedulePeriod period;
    VentoStatus        st;

    /* ── 1. Initial state ─────────────────────────────────────────────────── */
    printf("\n── Initial state ──────────────────────────────────────────────\n");
    st = vento_get_state(c, &state);
    check_ok(st, "get_state");
    if (st == Ok) print_state(&state);

    /* ── 2. Turn on ───────────────────────────────────────────────────────── */
    printf("\n── turn_on ────────────────────────────────────────────────────\n");
    check_ok(vento_turn_on(c), "turn_on");
    if (vento_get_state(c, &state) == Ok) print_state(&state);

    /* ── 3. Set speed 2 ───────────────────────────────────────────────────── */
    printf("\n── set_speed(2) ───────────────────────────────────────────────\n");
    check_ok(vento_set_speed(c, 2), "set_speed(2)");
    if (vento_get_state(c, &state) == Ok) print_state(&state);

    /* ── 4. Set manual speed 128 ──────────────────────────────────────────── */
    printf("\n── set_manual_speed(128) ──────────────────────────────────────\n");
    check_ok(vento_set_manual_speed(c, 128), "set_manual_speed(128)");
    if (vento_get_state(c, &state) == Ok) print_state(&state);

    /* ── 5. Set mode ventilation ──────────────────────────────────────────── */
    printf("\n── set_mode(0 = ventilation) ──────────────────────────────────\n");
    check_ok(vento_set_mode(c, 0), "set_mode(0)");

    /* ── 6. Set humidity threshold ────────────────────────────────────────── */
    printf("\n── set_humidity_threshold(60) ─────────────────────────────────\n");
    check_ok(vento_set_humidity_threshold(c, 60), "set_humidity_threshold(60)");

    /* ── 7. Enable weekly schedule ────────────────────────────────────────── */
    printf("\n── enable_weekly_schedule(1) ──────────────────────────────────\n");
    check_ok(vento_enable_weekly_schedule(c, 1), "enable_weekly_schedule(1)");

    /* ── 8. Write schedule period ─────────────────────────────────────────── */
    printf("\n── set_schedule_period(day=1 period=1 speed=2 end=08:00) ──────\n");
    check_ok(vento_set_schedule_period(c, 1, 1, 2, 8, 0),
             "set_schedule_period(1,1,2,8,0)");

    /* ── 9. Read schedule period back ────────────────────────────────────── */
    printf("\n── get_schedule_period(day=1 period=1) ────────────────────────\n");
    st = vento_get_schedule_period(c, 1, 1, &period);
    check_ok(st, "get_schedule_period(1,1)");
    if (st == Ok) {
        printf("    period %u: speed=%u end=%02u:%02u\n",
               (unsigned)period.period_number, (unsigned)period.speed,
               (unsigned)period.end_hours, (unsigned)period.end_minutes);
    }

    /* ── 10. Turn off ─────────────────────────────────────────────────────── */
    printf("\n── turn_off ───────────────────────────────────────────────────\n");
    check_ok(vento_turn_off(c), "turn_off");
    if (vento_get_state(c, &state) == Ok) print_state(&state);

    /* ── 11. Validate rejection of out-of-range values ────────────────────── */
    printf("\n── validation: out-of-range inputs ───────────────────────────\n");
    check_err_value(vento_set_speed(c, 5),                "set_speed(5)");
    check_err_value(vento_set_humidity_threshold(c, 99),  "set_humidity_threshold(99)");
    check_err_value(vento_set_boost_delay(c, 61),         "set_boost_delay(61)");
    check_err_value(vento_set_mode(c, 5),                 "set_mode(5)");

    /* ── 12. Null safety: client_new with null args ────────────────────────── */
    printf("\n── null safety ────────────────────────────────────────────────\n");
    {
        VentoClient *null_client = vento_client_new(NULL, NULL, NULL);
        if (!null_client) {
            printf("  %-40s ok (returned null)\n", "client_new(NULL,NULL,NULL)");
        } else {
            fprintf(stderr, "  %-40s expected null\n", "client_new(NULL,NULL,NULL)");
            vento_client_free(null_client);
            g_failures++;
        }
    }

    /* ── Cleanup ──────────────────────────────────────────────────────────── */
    vento_client_free(c);
    printf("  %-40s ok\n", "vento_client_free");

    /* ── Result ───────────────────────────────────────────────────────────── */
    printf("\n");
    if (g_failures == 0) {
        printf("=== All checks passed ===\n");
        return 0;
    } else {
        fprintf(stderr, "=== %d check(s) FAILED ===\n", g_failures);
        return 1;
    }
}
