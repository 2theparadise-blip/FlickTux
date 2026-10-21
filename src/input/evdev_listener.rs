//! Raw evdev tablet listener for Linux.
//! Detects pen tablets (Stylus pen + Finger touch/multitouch) and translates
//! raw evdev packets into `PenEvent`s.

use std::fs;
use std::io;
use std::path::{Path, PathBuf};

use evdev::{AbsoluteAxisCode, Device, EventType, KeyCode};

use crate::input::mapper::{PenEvent, PenMapper, RawPen, TabletInfo};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DeviceKind {
    /// EMR / Active stylus with tip pressure (e.g. Wacom Stylus)
    Stylus,
    /// Capacitive finger touch / multitouch surface (e.g. Wacom Touch / Trackpad)
    Touch,
    /// Embedded small touchscreen (e.g. Raspberry Pi official, Waveshare, Goodix, FT5406, XPT2046)
    Touchscreen,
    /// Device supporting both pen and touch
    Hybrid,
}

/// Candidate device info found on the system.
#[derive(Debug, Clone)]
pub struct DeviceCandidate {
    pub path: PathBuf,
    pub name: String,
    pub kind: Option<DeviceKind>,
    pub info: Option<TabletInfo>,
}

/// Enumerate all `/dev/input/event*` devices.
pub fn list_devices() -> io::Result<Vec<DeviceCandidate>> {
    let mut list = Vec::new();
    let entries = match fs::read_dir("/dev/input") {
        Ok(e) => e,
        Err(err) => return Err(err),
    };

    for entry in entries.flatten() {
        let path = entry.path();
        if let Some(fname) = path.file_name().and_then(|n| n.to_str()) {
            if fname.starts_with("event") {
                if let Ok(dev) = Device::open(&path) {
                    let name = dev.name().unwrap_or("Unknown").to_string();
                    let (kind, info) = inspect_device(&dev);
                    list.push(DeviceCandidate {
                        path,
                        name,
                        kind,
                        info,
                    });
                }
            }
        }
    }
    list.sort_by(|a, b| a.path.cmp(&b.path));
    Ok(list)
}

/// Check if a device has stylus or touch properties.
pub fn inspect_device(dev: &Device) -> (Option<DeviceKind>, Option<TabletInfo>) {
    let axes = dev.supported_absolute_axes();
    let keys = dev.supported_keys();

    let has_abs_x = axes.map_or(false, |a| a.contains(AbsoluteAxisCode::ABS_X));
    let has_abs_y = axes.map_or(false, |a| a.contains(AbsoluteAxisCode::ABS_Y));
    let has_mt_x = axes.map_or(false, |a| a.contains(AbsoluteAxisCode::ABS_MT_POSITION_X));
    let has_mt_y = axes.map_or(false, |a| a.contains(AbsoluteAxisCode::ABS_MT_POSITION_Y));

    if (!has_abs_x || !has_abs_y) && (!has_mt_x || !has_mt_y) {
        return (None, None);
    }

    let has_pen_btn = keys.map_or(false, |k| k.contains(KeyCode::BTN_TOOL_PEN));
    let has_touch_btn = keys.map_or(false, |k| k.contains(KeyCode::BTN_TOUCH));
    let has_finger_btn = keys.map_or(false, |k| k.contains(KeyCode::BTN_TOOL_FINGER));
    let has_pressure = axes.map_or(false, |a| a.contains(AbsoluteAxisCode::ABS_PRESSURE));

    let dev_name = dev.name().unwrap_or("").to_lowercase();
    let is_screen_by_name = dev_name.contains("touchscreen")
        || dev_name.contains("ft5406")
        || dev_name.contains("goodix")
        || dev_name.contains("waveshare")
        || dev_name.contains("raspberrypi-ts")
        || dev_name.contains("ads7846")
        || dev_name.contains("xpt2046");

    let is_stylus = has_pen_btn || (has_touch_btn && has_pressure && !is_screen_by_name);
    let is_touchscreen = is_screen_by_name || (has_touch_btn && !has_pen_btn && !has_finger_btn && !has_pressure);
    let is_touch = has_mt_x || has_finger_btn || (has_touch_btn && !has_pen_btn && !has_pressure);

    let kind = match (is_stylus, is_touchscreen, is_touch) {
        (true, _, true) => Some(DeviceKind::Hybrid),
        (true, _, false) => Some(DeviceKind::Stylus),
        (false, true, _) => Some(DeviceKind::Touchscreen),
        (false, false, true) => Some(DeviceKind::Touch),
        _ => None,
    };

    if kind.is_none() {
        return (None, None);
    }

    let abs_state = match dev.get_abs_state() {
        Ok(s) => s,
        Err(_) => return (kind, None),
    };

    // Use MT axes if regular ABS_X/Y are not available, or vice versa
    let (x_info, y_info) = if has_abs_x && has_abs_y {
        (
            abs_state.get(AbsoluteAxisCode::ABS_X.0 as usize),
            abs_state.get(AbsoluteAxisCode::ABS_Y.0 as usize),
        )
    } else {
        (
            abs_state.get(AbsoluteAxisCode::ABS_MT_POSITION_X.0 as usize),
            abs_state.get(AbsoluteAxisCode::ABS_MT_POSITION_Y.0 as usize),
        )
    };

    let p_info = abs_state.get(AbsoluteAxisCode::ABS_PRESSURE.0 as usize);

    let (x_min, x_max) = x_info.map_or((0, 32767), |i| (i.minimum, i.maximum));
    let (y_min, y_max) = y_info.map_or((0, 32767), |i| (i.minimum, i.maximum));
    // For finger touch / touchscreen with no pressure axis, default to 1000 so mapper treats contact as 100%
    let pressure_max = p_info.map_or(if is_touch || is_touchscreen { 1000 } else { 0 }, |i| i.maximum);

    let info = TabletInfo {
        x_min,
        x_max,
        y_min,
        y_max,
        pressure_max,
    };

    (kind, Some(info))
}

/// Automatically find the best tablet or touchscreen devices.
pub fn find_tablet_devices() -> io::Result<Vec<(PathBuf, DeviceKind, TabletInfo)>> {
    let devices = list_devices()?;
    let mut found = Vec::new();

    // 1. Direct detection by capabilities
    for d in &devices {
        if let (Some(kind), Some(info)) = (d.kind, d.info) {
            found.push((d.path.clone(), kind, info));
        }
    }

    if !found.is_empty() {
        return Ok(found);
    }

    // 2. Fallback: by name
    for d in &devices {
        let name_lower = d.name.to_lowercase();
        if name_lower.contains("wacom")
            || name_lower.contains("tablet")
            || name_lower.contains("stylus")
            || name_lower.contains("pen")
            || name_lower.contains("touch")
            || name_lower.contains("ft5406")
            || name_lower.contains("goodix")
            || name_lower.contains("waveshare")
            || name_lower.contains("raspberrypi-ts")
            || name_lower.contains("ads7846")
            || name_lower.contains("xpt2046")
        {
            if let Some(info) = d.info {
                let kind = d.kind.unwrap_or(DeviceKind::Touchscreen);
                found.push((d.path.clone(), kind, info));
            }
        }
    }

    if !found.is_empty() {
        Ok(found)
    } else {
        Err(io::Error::new(
            io::ErrorKind::NotFound,
            "No pen tablet or touch device found in /dev/input/event*. Use --device <path>.",
        ))
    }
}

pub struct EvdevTabletListener {
    device: Device,
    mapper: PenMapper,
    raw_pen: RawPen,
    is_touch_device: bool,
    current_slot: i32,
    active_tracking_id: i32,
}

impl EvdevTabletListener {
    pub fn open(path: &Path, mapper: PenMapper, kind: DeviceKind) -> io::Result<Self> {
        let device = Device::open(path)?;
        Ok(Self {
            device,
            mapper,
            raw_pen: RawPen::default(),
            is_touch_device: kind == DeviceKind::Touch,
            current_slot: 0,
            active_tracking_id: -1,
        })
    }

    /// Read incoming events from the device. Calls `on_event` for each complete `PenEvent`.
    pub fn process_events<F>(&mut self, mut on_event: F) -> io::Result<()>
    where
        F: FnMut(PenEvent),
    {
        for event in self.device.fetch_events()? {
            let ev_type = event.event_type();
            let code = event.code();
            let value = event.value();

            if ev_type == EventType::ABSOLUTE {
                if code == AbsoluteAxisCode::ABS_X.0 {
                    self.raw_pen.x = value;
                } else if code == AbsoluteAxisCode::ABS_Y.0 {
                    self.raw_pen.y = value;
                } else if code == AbsoluteAxisCode::ABS_PRESSURE.0 {
                    self.raw_pen.pressure = value;
                } else if code == AbsoluteAxisCode::ABS_MT_SLOT.0 {
                    self.current_slot = value;
                } else if code == AbsoluteAxisCode::ABS_MT_TRACKING_ID.0 {
                    if self.current_slot == 0 {
                        self.active_tracking_id = value;
                        if value >= 0 {
                            // Touch down
                            self.raw_pen.btn_touch = true;
                            self.raw_pen.pressure = 1000;
                        } else {
                            // Touch up
                            self.raw_pen.btn_touch = false;
                            self.raw_pen.pressure = 0;
                        }
                    }
                } else if code == AbsoluteAxisCode::ABS_MT_POSITION_X.0 {
                    if self.current_slot == 0 {
                        self.raw_pen.x = value;
                    }
                } else if code == AbsoluteAxisCode::ABS_MT_POSITION_Y.0 {
                    if self.current_slot == 0 {
                        self.raw_pen.y = value;
                    }
                }
            } else if ev_type == EventType::KEY {
                if code == KeyCode::BTN_TOUCH.0 {
                    self.raw_pen.btn_touch = value != 0;
                    if self.is_touch_device {
                        self.raw_pen.pressure = if value != 0 { 1000 } else { 0 };
                    }
                }
            } else if ev_type == EventType::SYNCHRONIZATION {
                // SYN_REPORT: end of one frame
                if code == 0 {
                    if let Some(pen_ev) = self.mapper.frame(&self.raw_pen) {
                        on_event(pen_ev);
                    }
                }
            }
        }
        Ok(())
    }
}
