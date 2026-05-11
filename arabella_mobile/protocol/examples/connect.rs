/// Phase 1 step 7 — end-to-end validation against a real fan or simulator.
///
/// Usage:
///   cargo run --example connect -- <ip> <device_id> <password>
///   cargo run --example connect -- 127.0.0.1 SIMFAN0000000001 1111
///
/// Runs: get_state, turn_on, set_speed 2, set_mode ventilation, turn_off.
/// Prints the full device state before and after each command.

use arabella_protocol::{VentoClient, VentoError};
use std::env;

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 4 {
        eprintln!("Usage: {} <ip> <device_id> <password>", args[0]);
        eprintln!("  e.g. {} 127.0.0.1 SIMFAN0000000001 1111", args[0]);
        std::process::exit(1);
    }

    let ip = &args[1];
    let device_id = &args[2];
    let password = &args[3];

    println!("=== Arabella Protocol — Phase 1 end-to-end validation ===");
    println!("Connecting to {} (id={}, pwd={})\n", ip, device_id, password);

    let client = VentoClient::new(ip, device_id, password);

    // --- 1. Read initial state ---
    println!("── Initial state ──────────────────────────────────────────");
    match client.get_state() {
        Ok(state) => print_state(&state),
        Err(e) => { eprintln!("get_state failed: {}", e); std::process::exit(1); }
    }

    // --- 2. Turn on ---
    println!("\n── turn_on ────────────────────────────────────────────────");
    run("turn_on", client.turn_on());
    match client.get_state() {
        Ok(state) => print_state(&state),
        Err(e) => eprintln!("get_state failed: {}", e),
    }

    // --- 3. Set speed 2 ---
    println!("\n── set_speed(2) ───────────────────────────────────────────");
    run("set_speed(2)", client.set_speed(2));
    match client.get_state() {
        Ok(state) => print_state(&state),
        Err(e) => eprintln!("get_state failed: {}", e),
    }

    // --- 4. Set manual speed 128 ---
    println!("\n── set_manual_speed(128) ──────────────────────────────────");
    run("set_manual_speed(128)", client.set_manual_speed(128));
    match client.get_state() {
        Ok(state) => print_state(&state),
        Err(e) => eprintln!("get_state failed: {}", e),
    }

    // --- 5. Set mode ventilation ---
    println!("\n── set_ventilation() ──────────────────────────────────────");
    run("set_ventilation", client.set_ventilation());

    // --- 6. Set humidity threshold ---
    println!("\n── set_humidity_threshold(60) ─────────────────────────────");
    run("set_humidity_threshold(60)", client.set_humidity_threshold(60));

    // --- 7. Enable schedule ---
    println!("\n── enable_weekly_schedule(true) ───────────────────────────");
    run("enable_weekly_schedule", client.enable_weekly_schedule(true));

    // --- 8. Set a schedule period ---
    println!("\n── set_schedule_period(day=1 period=1 speed=2 end=08:00) ──");
    run("set_schedule_period", client.set_schedule_period(1, 1, 2, 8, 0));

    // --- 9. Read the schedule period back ---
    println!("\n── get_schedule_period(day=1 period=1) ────────────────────");
    match client.get_schedule_period(1, 1) {
        Ok(p) => println!("  Period {}: speed={} end={:02}:{:02}",
            p.period_number, p.speed, p.end_hours, p.end_minutes),
        Err(e) => eprintln!("  get_schedule_period failed: {}", e),
    }

    // --- 10. Turn off ---
    println!("\n── turn_off ───────────────────────────────────────────────");
    run("turn_off", client.turn_off());
    match client.get_state() {
        Ok(state) => print_state(&state),
        Err(e) => eprintln!("get_state failed: {}", e),
    }

    // --- 11. Validate rejection of bad values ---
    println!("\n── validation: bad speed, bad humidity threshold ──────────");
    match client.set_speed(5) {
        Err(VentoError::Value(msg)) => println!("  set_speed(5) correctly rejected: {}", msg),
        other => eprintln!("  set_speed(5) unexpected result: {:?}", other),
    }
    match client.set_humidity_threshold(99) {
        Err(VentoError::Value(msg)) => println!("  set_humidity_threshold(99) correctly rejected: {}", msg),
        other => eprintln!("  set_humidity_threshold(99) unexpected: {:?}", other),
    }

    println!("\n=== Validation complete ===");
}

fn run(label: &str, result: arabella_protocol::Result<()>) {
    match result {
        Ok(()) => println!("  {} → ok", label),
        Err(e) => eprintln!("  {} → ERROR: {}", label, e),
    }
}

fn print_state(s: &arabella_protocol::DeviceState) {
    println!("  device_id  : {}", s.device_id);
    println!("  unit_type  : {} ({})", s.unit_type, s.unit_type_name());
    println!("  power      : {:?}", s.power);
    println!("  speed      : {:?}", s.speed);
    println!("  manual_spd : {:?}", s.manual_speed);
    println!("  mode       : {} ({:?})", s.operation_mode_name(), s.operation_mode);
    println!("  boost      : {:?}", s.boost_active);
    println!("  humidity   : sensor={:?} threshold={:?} current={:?}",
        s.humidity_sensor, s.humidity_threshold, s.current_humidity);
    println!("  fan RPM    : {:?} / {:?}", s.fan1_rpm, s.fan2_rpm);
    println!("  schedule   : enabled={:?}", s.weekly_schedule_enabled);
    if let Some(fw) = &s.firmware {
        println!("  firmware   : {}.{} ({}-{:02}-{:02})", fw.major, fw.minor, fw.year, fw.month, fw.day);
    }
}
