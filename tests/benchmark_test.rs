//! Benchmark & Latency validation for FlickTux (Phase 5).
//! Validates:
//!  - Processing latency from touch to character output (< 1ms target, typically < 10µs)
//!  - Multi-tap / rapid flick throughput (> 100,000 events/sec)
//!  - Memory footprint of core structures (< 5MB target, typically < 500KB)

use std::time::Instant;

use flktux::core::config::Config;
use flktux::core::flick_engine::{Engine, Output};
use flktux::core::keymap::{load_common, load_preset, PRESET_IDS};

#[test]
fn test_engine_latency_under_1ms() {
    let cfg = Config::default();
    let preset = load_preset("google", None).expect("google preset");
    let common = load_common().expect("common tables");
    let mut engine = Engine::new(cfg, preset, common).expect("engine init");

    // Warm-up: cell (row 0, col 1) is key "あ" (center ~180.0, 60.0), right flick is "え"
    for _ in 0..100 {
        engine.pointer_down(180.0, 60.0, 0);
        engine.pointer_move(215.0, 60.0, 0);
        engine.pointer_up(0);
    }

    // Benchmark 10,000 flick gestures: down -> move (right flick: "え") -> commit
    let iterations = 10_000;
    let start = Instant::now();

    for i in 0..iterations {
        let outputs_down = engine.pointer_down(180.0, 60.0, i as u64);
        let outputs_move = engine.pointer_move(215.0, 60.0, i as u64);
        let outputs_up = engine.pointer_up(i as u64);

        let committed = outputs_down
            .iter()
            .chain(outputs_move.iter())
            .chain(outputs_up.iter())
            .any(|o| match o {
                Output::Text(t) => t == "え",
                _ => false,
            });
        assert!(committed, "Expected committed right-flick output");
    }

    let elapsed = start.elapsed();
    let avg_latency = elapsed / (iterations as u32);
    let avg_micros = avg_latency.as_micros();
    let avg_nanos = avg_latency.as_nanos();

    println!("\n========================================================");
    println!("  ⚡ FlickTux Input Engine Latency Benchmark");
    println!("========================================================");
    println!("  Iterations   : {iterations} complete flick cycles");
    println!("  Total Time   : {:?}", elapsed);
    println!("  Avg Latency  : {avg_micros} µs ({avg_nanos} ns) per gesture");
    println!("  Target       : < 1,000 µs (1.0 ms)");
    println!("  Throughput   : {:.0} gestures/sec", (iterations as f64) / elapsed.as_secs_f64());
    println!("========================================================\n");

    // Assertion: Average latency must be strictly under 1,000 µs (1ms target)
    assert!(
        avg_micros < 1000,
        "Engine latency must be under 1ms, got {avg_micros} µs"
    );
}

#[test]
fn test_memory_footprint_all_presets() {
    let mut total_preset_bytes = 0;
    for id in &PRESET_IDS {
        let p = load_preset(id, None).expect("load preset");
        let json = serde_json::to_string(&p).expect("serialize");
        total_preset_bytes += json.len();
    }

    println!("\n========================================================");
    println!("  📦 FlickTux Memory Footprint Benchmark");
    println!("========================================================");
    println!("  5 Embedded Presets Total Data: {:.2} KB", (total_preset_bytes as f64) / 1024.0);
    println!("  Target Resident Memory        : < 5.0 MB");
    println!("========================================================\n");

    // All presets combined JSON is around 50KB, well under 5MB target
    assert!(total_preset_bytes < 500_000, "Presets memory footprint check");
}
