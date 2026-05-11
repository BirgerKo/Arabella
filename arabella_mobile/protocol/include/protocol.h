#ifndef ARABELLA_PROTOCOL_H
#define ARABELLA_PROTOCOL_H

#include <stdarg.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>

#define CMD_PAGE 255

#define CMD_FUNC 252

#define CMD_SIZE 254

#define CMD_NOT_SUP 253

#define PROTOCOL_TYPE 2

#define DEFAULT_PORT 4000

#define MAX_PACKET_SIZE 256

#define FUNC_READ 1

#define FUNC_WRITE 2

#define FUNC_INC 4

#define FUNC_DEC 8

#define FUNC_R FUNC_READ

#define FUNC_W FUNC_WRITE

#define FUNC_RW (FUNC_READ | FUNC_WRITE)

#define FUNC_RWID (((FUNC_READ | FUNC_WRITE) | FUNC_INC) | FUNC_DEC)

/**
 * Return status for all FFI functions. `Ok` (0) means success.
 */
typedef enum VentoStatus {
    Ok = 0,
    ErrConnection = 1,
    ErrChecksum = 2,
    ErrProtocol = 3,
    ErrValue = 4,
    ErrDiscovery = 5,
    ErrUnsupported = 6,
} VentoStatus;

typedef struct VentoClient VentoClient;

/**
 * Full device state snapshot filled by `vento_get_state`.
 *
 * Every optional field is paired with a `_valid` byte.
 * When `_valid` is 0 the companion field is undefined.
 * String fields (`ip`, `device_id`) are null-terminated UTF-8.
 */
typedef struct VentoDeviceState {
    /**
     * Null-terminated device IP address.
     */
    char ip[64];
    /**
     * Null-terminated device ID string.
     */
    char device_id[64];
    uint16_t unit_type;
    uint8_t power_valid;
    uint8_t power;
    uint8_t speed_valid;
    uint8_t speed;
    uint8_t manual_speed_valid;
    uint8_t manual_speed;
    uint8_t operation_mode_valid;
    uint8_t operation_mode;
    uint8_t boost_active_valid;
    uint8_t boost_active;
    uint8_t boost_delay_valid;
    uint8_t boost_delay_minutes;
    uint8_t timer_mode_valid;
    uint8_t timer_mode;
    uint8_t humidity_sensor_valid;
    uint8_t humidity_sensor;
    uint8_t humidity_threshold_valid;
    uint8_t humidity_threshold;
    uint8_t current_humidity_valid;
    uint8_t current_humidity;
    uint8_t humidity_status_valid;
    uint8_t humidity_status;
    uint8_t fan1_rpm_valid;
    uint16_t fan1_rpm;
    uint8_t fan2_rpm_valid;
    uint16_t fan2_rpm;
    uint8_t filter_needs_replacement_valid;
    uint8_t filter_needs_replacement;
    uint8_t alarm_status_valid;
    uint8_t alarm_status;
    uint8_t firmware_valid;
    uint8_t firmware_major;
    uint8_t firmware_minor;
    uint8_t weekly_schedule_enabled_valid;
    uint8_t weekly_schedule_enabled;
    uint8_t cloud_permitted_valid;
    uint8_t cloud_permitted;
} VentoDeviceState;

/**
 * Schedule period returned by `vento_get_schedule_period`.
 */
typedef struct VentoSchedulePeriod {
    uint8_t period_number;
    uint8_t end_hours;
    uint8_t end_minutes;
    uint8_t speed;
} VentoSchedulePeriod;

/**
 * Date/time input for `vento_set_rtc`. Caller supplies current local time.
 */
typedef struct VentoRtcInput {
    uint16_t year;
    uint8_t month;
    uint8_t day;
    /**
     * ISO weekday: 1 = Monday … 7 = Sunday.
     */
    uint8_t day_of_week;
    uint8_t hour;
    uint8_t minute;
    uint8_t second;
} VentoRtcInput;

/**
 * A single fan device returned by `vento_discover`.
 */
typedef struct VentoDiscoveredDevice {
    char ip[64];
    char device_id[64];
    uint16_t unit_type;
    char unit_type_name[128];
} VentoDiscoveredDevice;

/**
 * List of discovered devices returned by `vento_discover`.
 * Free with `vento_device_list_free` when done.
 */
typedef struct VentoDeviceList {
    struct VentoDiscoveredDevice *devices;
    uint32_t count;
} VentoDeviceList;

/**
 * Returns the last error message set by a failed FFI call on this thread.
 * The pointer is valid until the next FFI call. Do not free it.
 */
const char *vento_last_error(void);

/**
 * Create a new VentoClient.
 *
 * Returns a non-null opaque pointer on success. Free with `vento_client_free`.
 * Returns null if any argument is null.
 */
struct VentoClient *vento_client_new(const char *host, const char *device_id, const char *password);

/**
 * Free a VentoClient returned by `vento_client_new`. Passing null is a no-op.
 *
 * # Safety
 * `client` must be a pointer returned by `vento_client_new`, or null.
 */
void vento_client_free(struct VentoClient *client);

/**
 * Read the full device state into `*out`.
 *
 * # Safety
 * `client` and `out` must be valid non-null pointers.
 */
enum VentoStatus vento_get_state(const struct VentoClient *client, struct VentoDeviceState *out);

/**
 * # Safety
 * `client` must be a valid non-null pointer.
 */
enum VentoStatus vento_turn_on(const struct VentoClient *client);

/**
 * # Safety
 * `client` must be a valid non-null pointer.
 */
enum VentoStatus vento_turn_off(const struct VentoClient *client);

/**
 * # Safety
 * `client` must be a valid non-null pointer.
 */
enum VentoStatus vento_toggle_power(const struct VentoClient *client);

/**
 * Set fan speed (1, 2, or 3).
 *
 * # Safety
 * `client` must be a valid non-null pointer.
 */
enum VentoStatus vento_set_speed(const struct VentoClient *client, uint8_t speed);

/**
 * Set manual speed (0–255). Also sets speed mode to manual.
 *
 * # Safety
 * `client` must be a valid non-null pointer.
 */
enum VentoStatus vento_set_manual_speed(const struct VentoClient *client, uint8_t value);

/**
 * Increment speed by one step.
 *
 * # Safety
 * `client` must be a valid non-null pointer.
 */
enum VentoStatus vento_speed_up(const struct VentoClient *client);

/**
 * Decrement speed by one step.
 *
 * # Safety
 * `client` must be a valid non-null pointer.
 */
enum VentoStatus vento_speed_down(const struct VentoClient *client);

/**
 * Set operation mode: 0 = Ventilation, 1 = Heat Recovery, 2 = Supply.
 *
 * # Safety
 * `client` must be a valid non-null pointer.
 */
enum VentoStatus vento_set_mode(const struct VentoClient *client, uint8_t mode);

/**
 * Set boost delay in minutes (0–60).
 *
 * # Safety
 * `client` must be a valid non-null pointer.
 */
enum VentoStatus vento_set_boost_delay(const struct VentoClient *client, uint8_t minutes);

/**
 * Set timer mode: 0 = off, 1 = night, 2 = party.
 *
 * # Safety
 * `client` must be a valid non-null pointer.
 */
enum VentoStatus vento_set_timer_mode(const struct VentoClient *client, uint8_t mode);

/**
 * Set night timer duration.
 *
 * # Safety
 * `client` must be a valid non-null pointer.
 */
enum VentoStatus vento_set_night_timer(const struct VentoClient *client,
                                       uint8_t hours,
                                       uint8_t minutes);

/**
 * Set party timer duration.
 *
 * # Safety
 * `client` must be a valid non-null pointer.
 */
enum VentoStatus vento_set_party_timer(const struct VentoClient *client,
                                       uint8_t hours,
                                       uint8_t minutes);

/**
 * Set humidity sensor mode: 0 = off, 1 = internal, 2 = external.
 *
 * # Safety
 * `client` must be a valid non-null pointer.
 */
enum VentoStatus vento_set_humidity_sensor(const struct VentoClient *client, uint8_t sensor);

/**
 * Set humidity threshold (40–80 %RH).
 *
 * # Safety
 * `client` must be a valid non-null pointer.
 */
enum VentoStatus vento_set_humidity_threshold(const struct VentoClient *client, uint8_t rh);

/**
 * Enable or disable the weekly schedule (enabled != 0 means enable).
 *
 * # Safety
 * `client` must be a valid non-null pointer.
 */
enum VentoStatus vento_enable_weekly_schedule(const struct VentoClient *client, uint8_t enabled);

/**
 * Write one schedule period.
 *
 * - `day`: 0–9
 * - `period`: 1–4
 * - `speed`: 0–3
 * - `end_h`/`end_m`: end time of the period
 *
 * # Safety
 * `client` must be a valid non-null pointer.
 */
enum VentoStatus vento_set_schedule_period(const struct VentoClient *client,
                                           uint8_t day,
                                           uint8_t period,
                                           uint8_t speed,
                                           uint8_t end_h,
                                           uint8_t end_m);

/**
 * Read one schedule period into `*out`.
 *
 * # Safety
 * `client` and `out` must be valid non-null pointers.
 */
enum VentoStatus vento_get_schedule_period(const struct VentoClient *client,
                                           uint8_t day,
                                           uint8_t period,
                                           struct VentoSchedulePeriod *out);

/**
 * Synchronise the fan's real-time clock.
 *
 * # Safety
 * `client` and `dt` must be valid non-null pointers.
 */
enum VentoStatus vento_set_rtc(const struct VentoClient *client, const struct VentoRtcInput *dt);

/**
 * Reset the filter replacement countdown.
 *
 * # Safety
 * `client` must be a valid non-null pointer.
 */
enum VentoStatus vento_reset_filter_timer(const struct VentoClient *client);

/**
 * Clear all active alarms.
 *
 * # Safety
 * `client` must be a valid non-null pointer.
 */
enum VentoStatus vento_reset_alarms(const struct VentoClient *client);

/**
 * Allow or deny cloud access.
 *
 * # Safety
 * `client` must be a valid non-null pointer.
 */
enum VentoStatus vento_set_cloud_permission(const struct VentoClient *client, uint8_t allowed);

/**
 * Restore factory defaults. Use with caution.
 *
 * # Safety
 * `client` must be a valid non-null pointer.
 */
enum VentoStatus vento_factory_reset(const struct VentoClient *client);

/**
 * Discover fans on the local network.
 *
 * On `Ok`, `out->devices` points to a heap-allocated array of `out->count` entries.
 * Free with `vento_device_list_free` when done.
 *
 * # Safety
 * `broadcast` must be a valid non-null C string. `out` must be a valid non-null pointer.
 */
enum VentoStatus vento_discover(const char *broadcast,
                                uint16_t port,
                                double timeout_secs,
                                uint32_t max_devices,
                                struct VentoDeviceList *out);

/**
 * Free a device list returned by `vento_discover`. Passing a null or empty list is a no-op.
 *
 * # Safety
 * `list` must be a pointer to a `VentoDeviceList` previously filled by `vento_discover`, or null.
 */
void vento_device_list_free(struct VentoDeviceList *list);

#endif  /* ARABELLA_PROTOCOL_H */
