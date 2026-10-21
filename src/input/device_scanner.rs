//! Device Scanner for FlickTux.
//! Discovers pen tablets (Wacom, XP-Pen, Huion, Gaomon, Xencelabs, Weylus),
//! and DIY keypads / 10-key devices (Arduino, Raspberry Pi Pico, Teensy, QMK).

#![allow(dead_code)]

#[cfg(target_os = "linux")]
use std::fs;
use std::io;
#[cfg(target_os = "linux")]
use std::path::PathBuf;

use serde::{Deserialize, Serialize};

#[cfg(target_os = "linux")]
use evdev::{AbsoluteAxisCode, Device, KeyCode};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum DeviceCategory {
    TabletStylus,
    TabletTouch,
    DiyKeypad,
    StandardKeyboard,
    Other,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DiscoveredDevice {
    pub path: String,
    pub name: String,
    pub vendor_id: u16,
    pub product_id: u16,
    pub category: DeviceCategory,
    pub is_recommended: bool,
    pub description: String,
}

/// Known microcontroller Vendor IDs frequently used in DIY keypads & push-phone adapters.
const DIY_VENDORS: &[(u16, &str)] = &[
    (0x2341, "Arduino SA"),
    (0x1b4f, "SparkFun"),
    (0x239a, "Adafruit"),
    (0x2e8a, "Raspberry Pi (Pico/RP2040)"),
    (0x16c0, "PJRC (Teensy)"),
    (0x303a, "Espressif (ESP32)"),
    (0xfeed, "QMK Firmware"),
    (0x4653, "QMK / VIA Keypad"),
];

/// Known graphics tablet vendors.
const TABLET_VENDORS: &[(u16, &str)] = &[
    (0x056a, "Wacom"),
    (0x28bd, "XP-Pen"),
    (0x256c, "Huion"),
    (0x5543, "UC-Logic / Gaomon"),
    (0x0b57, "Hanvon"),
    (0x2e2c, "Xencelabs"),
];

/// Scan the system for connected tablets and DIY 10-key devices.
pub fn scan_devices() -> io::Result<Vec<DiscoveredDevice>> {
    #[cfg(target_os = "linux")]
    {
        let mut results = Vec::new();

        // 1. Scan /dev/input/by-id first for stable symbolic links
        let by_id_dir = PathBuf::from("/dev/input/by-id");
        let mut visited_paths = std::collections::HashSet::new();

        if let Ok(entries) = fs::read_dir(&by_id_dir) {
            for entry in entries.flatten() {
                let path = entry.path();
                if let Ok(dev) = Device::open(&path) {
                    if let Ok(canonical) = fs::canonicalize(&path) {
                        visited_paths.insert(canonical);
                    }
                    if let Some(discovered) = inspect_evdev_device(&dev, path.to_string_lossy().into_owned()) {
                        results.push(discovered);
                    }
                }
            }
        }

        // 2. Scan remaining /dev/input/event*
        if let Ok(entries) = fs::read_dir("/dev/input") {
            for entry in entries.flatten() {
                let path = entry.path();
                if let Some(fname) = path.file_name().and_then(|n| n.to_str()) {
                    if fname.starts_with("event") {
                        if let Ok(canonical) = fs::canonicalize(&path) {
                            if !visited_paths.contains(&canonical) {
                                if let Ok(dev) = Device::open(&path) {
                                    if let Some(discovered) = inspect_evdev_device(&dev, path.to_string_lossy().into_owned()) {
                                        results.push(discovered);
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        results.sort_by(|a, b| {
            b.is_recommended.cmp(&a.is_recommended)
                .then_with(|| a.name.cmp(&b.name))
        });

        Ok(results)
    }

    #[cfg(not(target_os = "linux"))]
    {
        Ok(Vec::new())
    }
}

#[cfg(target_os = "linux")]
fn inspect_evdev_device(dev: &Device, path: String) -> Option<DiscoveredDevice> {
    let name = dev.name().unwrap_or("Unknown").to_string();
    let name_lower = name.to_lowercase();
    let id = dev.input_id();
    let vid = id.vendor();
    let pid = id.product();

    let axes = dev.supported_absolute_axes();
    let keys = dev.supported_keys();

    let has_pressure = axes.map_or(false, |a| a.contains(AbsoluteAxisCode::ABS_PRESSURE));
    let has_pen_btn = keys.map_or(false, |k| k.contains(KeyCode::BTN_TOOL_PEN));
    let has_touch_btn = keys.map_or(false, |k| k.contains(KeyCode::BTN_TOUCH));
    let has_mt = axes.map_or(false, |a| a.contains(AbsoluteAxisCode::ABS_MT_POSITION_X));

    // Numpad key detection
    let has_numpad_keys = keys.map_or(false, |k| {
        k.contains(KeyCode::KEY_KP0)
            || k.contains(KeyCode::KEY_KP1)
            || k.contains(KeyCode::KEY_KPENTER)
            || k.contains(KeyCode::KEY_KPASTERISK)
    });

    let has_regular_keys = keys.map_or(false, |k| {
        k.contains(KeyCode::KEY_A) || k.contains(KeyCode::KEY_SPACE) || k.contains(KeyCode::KEY_1)
    });

    let is_diy_vendor = DIY_VENDORS.iter().any(|(v, _)| *v == vid);
    let is_tablet_vendor = TABLET_VENDORS.iter().any(|(v, _)| *v == vid)
        || name_lower.contains("wacom")
        || name_lower.contains("xp-pen")
        || name_lower.contains("huion")
        || name_lower.contains("gaomon")
        || name_lower.contains("xencelabs")
        || name_lower.contains("ugee")
        || name_lower.contains("veikk")
        || name_lower.contains("parblo")
        || name_lower.contains("weylus");

    // Check for Weylus
    if name_lower.contains("weylus stylus") {
        return Some(DiscoveredDevice {
            path,
            name,
            vendor_id: vid,
            product_id: pid,
            category: DeviceCategory::TabletStylus,
            is_recommended: true,
            description: "Weylus iPad / iPad mini 仮想スタイラス (Apple Pencil)".into(),
        });
    }

    if name_lower.contains("weylus touch") {
        return Some(DiscoveredDevice {
            path,
            name,
            vendor_id: vid,
            product_id: pid,
            category: DeviceCategory::TabletTouch,
            is_recommended: true,
            description: "Weylus iPad / iPad mini 仮想マルチタッチ".into(),
        });
    }

    // Tablet Stylus
    if has_pen_btn || (has_pressure && (is_tablet_vendor || has_touch_btn)) {
        let vendor_label = TABLET_VENDORS.iter()
            .find(|(v, _)| *v == vid)
            .map(|(_, name)| *name)
            .unwrap_or(if is_tablet_vendor { "サードパーティ製液タブ" } else { "スタイラス" });

        return Some(DiscoveredDevice {
            path,
            name: name.clone(),
            vendor_id: vid,
            product_id: pid,
            category: DeviceCategory::TabletStylus,
            is_recommended: true,
            description: format!("{vendor_label} ペン入力 (筆圧検知対応)"),
        });
    }

    // DIY Keypad / Push-phone
    if is_diy_vendor
        || name_lower.contains("arduino")
        || name_lower.contains("pico")
        || name_lower.contains("teensy")
        || name_lower.contains("keypad")
        || name_lower.contains("numpad")
        || name_lower.contains("qmk")
        || name_lower.contains("dialpad")
        || (has_numpad_keys && !has_regular_keys)
    {
        let desc = if is_diy_vendor {
            let vname = DIY_VENDORS.iter().find(|(v, _)| *v == vid).map(|(_, n)| *n).unwrap_or("マイコン");
            format!("{vname} 自作キーパッド / テンキーデバイス (推奨)")
        } else if has_numpad_keys {
            "外付けテンキー / ダイヤルパッドデバイス".into()
        } else {
            "自作USB入力デバイス".into()
        };

        return Some(DiscoveredDevice {
            path,
            name,
            vendor_id: vid,
            product_id: pid,
            category: DeviceCategory::DiyKeypad,
            is_recommended: true,
            description: desc,
        });
    }

    // Touchpad or Touchscreen
    if has_mt || has_touch_btn {
        return Some(DiscoveredDevice {
            path,
            name,
            vendor_id: vid,
            product_id: pid,
            category: DeviceCategory::TabletTouch,
            is_recommended: false,
            description: "タッチサーフェス / トラックパッド".into(),
        });
    }

    // Regular keyboard
    if has_regular_keys {
        return Some(DiscoveredDevice {
            path,
            name,
            vendor_id: vid,
            product_id: pid,
            category: DeviceCategory::StandardKeyboard,
            is_recommended: false,
            description: "標準キーボード".into(),
        });
    }

    None
}
