//! FlickTux (`flktux`) — Rust port.
//! Floating Japanese Flick Keyboard for Pen Tablets & Linux.

use flktux::{core, server, ui};
#[cfg(target_os = "linux")]
use flktux::{input, uinput};

use std::path::PathBuf;
#[cfg(target_os = "linux")]
use std::time::{SystemTime, UNIX_EPOCH};

use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(name = "flktux", version, about = "FlickTux: flick keyboard for pen tablets")]
struct Cli {
    #[command(subcommand)]
    cmd: Option<Cmd>,
}

#[derive(Subcommand)]
enum Cmd {
    /// Toggle FlickTux floating keyboard (Start if not running, Stop if running)
    Toggle {
        /// Also start the embedded Web Matrix Editor server
        #[arg(long)]
        web: bool,
        /// Port for the Web Matrix Editor (default: 8080)
        #[arg(long, default_value_t = 8080)]
        port: u16,
    },
    /// Launch the floating on-screen flick keyboard GUI (Default)
    Ui {
        /// Also start the embedded Web Matrix Editor server
        #[arg(long)]
        web: bool,
        /// Port for the Web Matrix Editor (default: 8080)
        #[arg(long, default_value_t = 8080)]
        port: u16,
    },
    /// Start the embedded Web Matrix Editor server on http://<bind>:<port>/ (Phase 4)
    Web {
        /// Port to bind (default: 8080)
        #[arg(long, default_value_t = 8080)]
        port: u16,
        /// Host to bind (default: "0.0.0.0")
        #[arg(long, default_value = "0.0.0.0")]
        bind: String,
    },
    /// Inject keystrokes through a virtual keyboard (/dev/uinput)
    Emit {
        /// ASCII/romaji text, e.g. "konnichiha"
        #[arg(long)]
        text: Option<String>,
        /// Kana text converted to romaji keystrokes, e.g. "こんにちは"
        #[arg(long)]
        kana: Option<String>,
        /// Named key: enter, backspace, space, tab, esc, left, right, ...
        #[arg(long)]
        key: Option<String>,
        /// Seconds to wait before sending (time to focus the target window)
        #[arg(long, default_value_t = 2.0)]
        delay: f64,
    },
    /// Print the keystroke sequence for kana text without sending it
    Dry {
        kana: String,
    },
    /// List available keymap presets
    Presets,
    /// List input devices in /dev/input and show tablet detection status (Linux only)
    Devices,
    /// Run headless pen tablet flick engine: reads evdev pen and emits keystrokes (Linux only)
    Run {
        /// Evdev device path (e.g. /dev/input/event5). If omitted, automatically detects tablet.
        #[arg(long)]
        device: Option<PathBuf>,
        /// Keymap preset: google, galaxy, iphone, garakei, tenkey
        #[arg(long)]
        layout: Option<String>,
        /// Input mode: kana, katakana, alpha, number, nav
        #[arg(long)]
        mode: Option<String>,
        /// Path to config.json
        #[arg(long)]
        config: Option<PathBuf>,
        /// Also start the embedded Web Matrix Editor server
        #[arg(long)]
        web: bool,
        /// Port for the Web Matrix Editor (default: 8080)
        #[arg(long, default_value_t = 8080)]
        port: u16,
    },
}

#[cfg(target_os = "linux")]
fn now_millis() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis() as u64
}

fn main() {
    let cli = Cli::parse();
    if let Err(e) = run(cli) {
        eprintln!("flktux: {e}");
        std::process::exit(1);
    }
}

fn run(cli: Cli) -> Result<(), Box<dyn std::error::Error>> {
    let cmd = cli.cmd.unwrap_or(Cmd::Toggle { web: false, port: 8080 });
    match cmd {
        Cmd::Toggle { web, port } => toggle(web, port),
        Cmd::Ui { web, port } => {
            if web {
                server::web_editor::spawn_server(format!("0.0.0.0:{port}"));
            }
            ui::floating_window::launch_ui()
        }
        Cmd::Web { port, bind } => {
            let addr = format!("{bind}:{port}");
            server::web_editor::run_server(&addr)
        }
        Cmd::Dry { kana } => {
            let rom = core::romaji::kana_to_romaji(&kana)
                .map_err(|c| format!("unsupported character: {c:?}"))?;
            println!("{rom}");
            Ok(())
        }
        Cmd::Presets => {
            println!("Available presets:");
            for id in core::keymap::PRESET_IDS {
                let p = core::keymap::load_preset(id, None)?;
                println!("  - {:<10} ({}x{} grid, name: {:?})", p.id, p.rows, p.cols, p.name);
            }
            Ok(())
        }
        Cmd::Emit { text, kana, key, delay } => emit(text, kana, key, delay),
        Cmd::Devices => list_devices(),
        Cmd::Run { device, layout, mode, config, web, port } => {
            if web {
                server::web_editor::spawn_server(format!("0.0.0.0:{port}"));
            }
            run_engine(device, layout, mode, config)
        }
    }
}

fn pid_file_path() -> PathBuf {
    if let Ok(home) = std::env::var("HOME") {
        PathBuf::from(home).join(".config/flktux/flktux.pid")
    } else {
        PathBuf::from("/tmp/flktux.pid")
    }
}

fn is_process_running(pid: i32) -> bool {
    #[cfg(unix)]
    unsafe {
        libc::kill(pid, 0) == 0
    }
    #[cfg(not(unix))]
    false
}

fn toggle(web: bool, port: u16) -> Result<(), Box<dyn std::error::Error>> {
    let pid_path = pid_file_path();
    if pid_path.exists() {
        if let Ok(content) = std::fs::read_to_string(&pid_path) {
            if let Ok(pid) = content.trim().parse::<i32>() {
                if is_process_running(pid) {
                    println!("Stopping running FlickTux (PID: {pid})...");
                    #[cfg(unix)]
                    unsafe {
                        libc::kill(pid, libc::SIGTERM);
                    }
                    let _ = std::fs::remove_file(&pid_path);
                    return Ok(());
                }
            }
        }
        let _ = std::fs::remove_file(&pid_path);
    }

    println!("Starting FlickTux...");
    if let Some(parent) = pid_path.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    let my_pid = std::process::id();
    let _ = std::fs::write(&pid_path, my_pid.to_string());

    if web {
        server::web_editor::spawn_server(format!("0.0.0.0:{port}"));
    }

    struct PidGuard(PathBuf);
    impl Drop for PidGuard {
        fn drop(&mut self) {
            let _ = std::fs::remove_file(&self.0);
        }
    }
    let _guard = PidGuard(pid_path);

    ui::floating_window::launch_ui()
}

#[cfg(target_os = "linux")]
fn emit(
    text: Option<String>,
    kana: Option<String>,
    key: Option<String>,
    delay: f64,
) -> Result<(), Box<dyn std::error::Error>> {
    if text.is_none() && kana.is_none() && key.is_none() {
        return Err("specify one of --text / --kana / --key".into());
    }
    let mut kb = uinput::emitter::VirtualKeyboard::new().map_err(|e| {
        format!("cannot open /dev/uinput ({e}). Run ./setup_udev.sh and re-login.")
    })?;
    std::thread::sleep(std::time::Duration::from_secs_f64(delay.max(0.0)));
    if let Some(t) = text {
        kb.type_ascii(&t)?;
    }
    if let Some(k) = kana {
        kb.type_kana(&k)?;
    }
    if let Some(name) = key {
        let code = core::keys::code_for_name(&name)
            .ok_or_else(|| format!("unknown key name: {name}"))?;
        kb.tap_code(code)?;
    }
    Ok(())
}

#[cfg(not(target_os = "linux"))]
fn emit(
    _text: Option<String>,
    _kana: Option<String>,
    _key: Option<String>,
    _delay: f64,
) -> Result<(), Box<dyn std::error::Error>> {
    Err("`emit` requires Linux (/dev/uinput). Use `dry` to check conversion.".into())
}

#[cfg(target_os = "linux")]
fn list_devices() -> Result<(), Box<dyn std::error::Error>> {
    println!("Scanning /dev/input/event* devices:");
    let devs = input::evdev_listener::list_devices()?;
    if devs.is_empty() {
        println!("  (No event devices found. Check permissions or user in 'input' group)");
        return Ok(());
    }
    for d in devs {
        let tag = match d.kind {
            Some(input::evdev_listener::DeviceKind::Stylus) =>      "[PEN/STYLUS]  ",
            Some(input::evdev_listener::DeviceKind::Touch) =>       "[FINGER/TOUCH]",
            Some(input::evdev_listener::DeviceKind::Touchscreen) => "[TOUCHSCREEN] ",
            Some(input::evdev_listener::DeviceKind::Hybrid) =>      "[HYBRID]       ",
            None =>                                                 "              ",
        };
        println!("  {:<24} {} {:?}", d.path.display(), tag, d.name);
        if let Some(info) = d.info {
            println!(
                "      ABS_X: {}..{}, ABS_Y: {}..{}, PressureMax: {}",
                info.x_min, info.x_max, info.y_min, info.y_max, info.pressure_max
            );
        }
    }
    Ok(())
}

#[cfg(not(target_os = "linux"))]
fn list_devices() -> Result<(), Box<dyn std::error::Error>> {
    Err("`devices` is only supported on Linux via evdev.".into())
}

#[cfg(target_os = "linux")]
fn run_engine(
    device_path: Option<PathBuf>,
    layout: Option<String>,
    mode: Option<String>,
    config_path: Option<PathBuf>,
) -> Result<(), Box<dyn std::error::Error>> {
    let cfg_path = config_path.unwrap_or_else(|| PathBuf::from("configs/config.json"));
    let mut config = core::config::Config::load_or_default(&cfg_path)?;
    if let Some(l) = layout {
        config.layout = l;
    }
    if let Some(m) = mode {
        config.mode = m;
    }

    let preset = core::keymap::load_preset(&config.layout, None)?;
    let common = core::keymap::load_common()?;
    let mut engine = core::flick_engine::Engine::new(config.clone(), preset, common)?;

    let (dev_path, dev_kind, tablet_info) = match device_path {
        Some(p) => {
            let dev = evdev::Device::open(&p)?;
            let (kind, info) = input::evdev_listener::inspect_device(&dev);
            let info = info.ok_or_else(|| format!("{} does not report ABS_X/ABS_Y axes", p.display()))?;
            let kind = kind.unwrap_or(input::evdev_listener::DeviceKind::Stylus);
            (p, kind, info)
        }
        None => {
            let candidates = input::evdev_listener::find_tablet_devices()?;
            // Prefer stylus/hybrid if available, otherwise touchscreen or touch
            let chosen = candidates
                .iter()
                .find(|(_, k, _)| *k == input::evdev_listener::DeviceKind::Stylus || *k == input::evdev_listener::DeviceKind::Hybrid)
                .or_else(|| candidates.iter().find(|(_, k, _)| *k == input::evdev_listener::DeviceKind::Touchscreen))
                .or_else(|| candidates.first())
                .cloned()
                .ok_or_else(|| "No supported stylus, touchscreen, or touch device found")?;
            chosen
        }
    };

    println!("====================================================");
    println!("  FlickTux Engine (Rust) Starting");
    println!("  Device   : {} ({:?})", dev_path.display(), dev_kind);
    println!("  Layout   : {} ({})", engine.preset().name, engine.preset().id);
    println!("  Mode     : {}", engine.mode());
    println!("  Grid     : {} rows x {} cols", engine.preset().rows, engine.preset().cols);
    println!("  Threshold: {}px", config.flick_threshold_px);
    println!("  Smoothing: {}", config.pen.smoothing);
    println!("====================================================");

    let mapper = input::mapper::PenMapper::new(tablet_info, config);
    let mut listener = input::evdev_listener::EvdevTabletListener::open(&dev_path, mapper, dev_kind)?;
    let mut kb = uinput::emitter::VirtualKeyboard::new().map_err(|e| {
        format!("cannot open /dev/uinput ({e}). Run ./setup_udev.sh and re-login.")
    })?;

    println!("Ready! Touch tablet surface (Pen or Finger) to input...");

    loop {
        listener.process_events(|pen_ev| {
            let now = now_millis();
            let outputs = match pen_ev {
                input::mapper::PenEvent::Down(x, y) => engine.pointer_down(x, y, now),
                input::mapper::PenEvent::Move(x, y) => engine.pointer_move(x, y, now),
                input::mapper::PenEvent::Up => engine.pointer_up(now),
            };

            for out in outputs {
                match out {
                    core::flick_engine::Output::Text(t) => {
                        println!("[INPUT] Type: {t}");
                        let _ = kb.type_kana(&t);
                    }
                    core::flick_engine::Output::Replace(t) => {
                        println!("[INPUT] Replace: {t}");
                        let _ = kb.replace_kana(1, &t);
                    }
                    core::flick_engine::Output::Key(s) => {
                        println!("[INPUT] Key: code={}, shift={}, ctrl={}", s.code, s.shift, s.ctrl);
                        let _ = kb.tap(s);
                    }
                }
            }
        })?;
    }
}

#[cfg(not(target_os = "linux"))]
fn run_engine(
    _device_path: Option<PathBuf>,
    _layout: Option<String>,
    _mode: Option<String>,
    _config_path: Option<PathBuf>,
) -> Result<(), Box<dyn std::error::Error>> {
    Err("`run` requires Linux with evdev & /dev/uinput.".into())
}
