//! Pen input: tablet frames → press / move / release in keyboard pixels.
//! OS-independent (the evdev reading lives in `evdev_listener`).

#![allow(dead_code)]

use crate::core::config::Config;

/// Axis ranges of the tablet.
#[derive(Debug, Clone, Copy)]
pub struct TabletInfo {
    pub x_min: i32,
    pub x_max: i32,
    pub y_min: i32,
    pub y_max: i32,
    /// 0 if the device reports no pressure (BTN_TOUCH is used instead).
    pub pressure_max: i32,
}

/// One SYN-report worth of raw pen state.
#[derive(Debug, Clone, Copy, Default)]
pub struct RawPen {
    pub x: i32,
    pub y: i32,
    pub pressure: i32,
    pub btn_touch: bool,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum PenEvent {
    Down(f64, f64),
    Move(f64, f64),
    Up,
}

pub struct PenMapper {
    info: TabletInfo,
    cfg: Config,
    touching: bool,
    /// Touch started outside the keyboard area: ignore until lift.
    ignoring: bool,
    smoothed: Option<(f64, f64)>,
    last: Option<(f64, f64)>,
}

impl PenMapper {
    pub fn new(info: TabletInfo, cfg: Config) -> Self {
        Self { info, cfg, touching: false, ignoring: false, smoothed: None, last: None }
    }

    fn contact(&self, raw: &RawPen) -> bool {
        if self.info.pressure_max > 0 {
            let r = raw.pressure as f64 / self.info.pressure_max as f64;
            // Hysteresis: easier to keep touching than to start.
            let th = if self.touching { self.cfg.pen.release_threshold } else { self.cfg.pen.press_threshold };
            r >= th && r > 0.0
        } else {
            raw.btn_touch
        }
    }

    /// Tablet coords → (keyboard px, inside-area flag). Position is clamped.
    fn to_keyboard(&self, raw: &RawPen) -> ((f64, f64), bool) {
        let i = &self.info;
        let nx = (raw.x - i.x_min) as f64 / (i.x_max - i.x_min).max(1) as f64;
        let ny = (raw.y - i.y_min) as f64 / (i.y_max - i.y_min).max(1) as f64;
        let a = &self.cfg.tablet_area;
        let ax = (nx - a.x) / a.w.max(1e-6);
        let ay = (ny - a.y) / a.h.max(1e-6);
        let inside = (0.0..=1.0).contains(&ax) && (0.0..=1.0).contains(&ay);
        let px = ax.clamp(0.0, 1.0) * self.cfg.keyboard_width;
        let py = ay.clamp(0.0, 1.0) * self.cfg.keyboard_height;
        ((px, py), inside)
    }

    pub fn frame(&mut self, raw: &RawPen) -> Option<PenEvent> {
        let contact = self.contact(raw);
        let (pos, inside) = self.to_keyboard(raw);

        if !contact {
            let was = self.touching && !self.ignoring;
            self.touching = false;
            self.ignoring = false;
            self.smoothed = None;
            self.last = None;
            return was.then_some(PenEvent::Up);
        }

        if !self.touching {
            self.touching = true;
            self.ignoring = !inside;
            if self.ignoring {
                return None;
            }
            self.smoothed = Some(pos);
            self.last = Some(pos);
            return Some(PenEvent::Down(pos.0, pos.1));
        }
        if self.ignoring {
            return None;
        }

        let alpha = self.cfg.pen.smoothing.clamp(0.01, 1.0);
        let prev = self.smoothed.unwrap_or(pos);
        let s = (prev.0 + alpha * (pos.0 - prev.0), prev.1 + alpha * (pos.1 - prev.1));
        self.smoothed = Some(s);
        if self.last == Some(s) {
            return None;
        }
        self.last = Some(s);
        Some(PenEvent::Move(s.0, s.1))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::core::config::Area;

    const INFO: TabletInfo =
        TabletInfo { x_min: 0, x_max: 1000, y_min: 0, y_max: 1000, pressure_max: 1000 };

    fn pen(x: i32, y: i32, p: i32) -> RawPen {
        RawPen { x, y, pressure: p, btn_touch: p > 0 }
    }

    #[test]
    fn maps_full_tablet_to_keyboard() {
        let mut m = PenMapper::new(INFO, Config::default()); // 600x480
        assert_eq!(m.frame(&pen(500, 500, 500)), Some(PenEvent::Down(300.0, 240.0)));
        assert_eq!(m.frame(&pen(1000, 0, 500)), Some(PenEvent::Move(600.0, 0.0)));
        assert_eq!(m.frame(&pen(1000, 0, 0)), Some(PenEvent::Up));
    }

    #[test]
    fn pressure_hysteresis() {
        let mut m = PenMapper::new(INFO, Config::default()); // press 3%, release 1.5%
        assert_eq!(m.frame(&pen(100, 100, 20)), None); // 2% < 3%: hovering
        assert!(matches!(m.frame(&pen(100, 100, 40)), Some(PenEvent::Down(..))));
        // 2% is above release threshold: still touching (no chatter)
        assert!(!matches!(m.frame(&pen(100, 100, 20)), Some(PenEvent::Up)));
        assert_eq!(m.frame(&pen(100, 100, 10)), Some(PenEvent::Up));
    }

    #[test]
    fn button_only_device() {
        let info = TabletInfo { pressure_max: 0, ..INFO };
        let mut m = PenMapper::new(info, Config::default());
        let down = RawPen { x: 0, y: 0, pressure: 0, btn_touch: true };
        assert!(matches!(m.frame(&down), Some(PenEvent::Down(..))));
        assert_eq!(m.frame(&RawPen { btn_touch: false, ..down }), Some(PenEvent::Up));
    }

    #[test]
    fn area_selects_part_of_tablet_and_ignores_outside_start() {
        let cfg = Config { tablet_area: Area { x: 0.5, y: 0.5, w: 0.5, h: 0.5 }, ..Config::default() };
        let mut m = PenMapper::new(INFO, cfg);
        // starts outside: whole stroke ignored
        assert_eq!(m.frame(&pen(100, 100, 500)), None);
        assert_eq!(m.frame(&pen(800, 800, 500)), None);
        assert_eq!(m.frame(&pen(800, 800, 0)), None);
        // starts inside; center of the area is the keyboard center
        assert_eq!(m.frame(&pen(750, 750, 500)), Some(PenEvent::Down(300.0, 240.0)));
        // leaving the area clamps to the edge (allows overshooting flicks)
        assert_eq!(m.frame(&pen(0, 750, 500)), Some(PenEvent::Move(0.0, 240.0)));
    }

    #[test]
    fn smoothing_lags_behind_pen() {
        let mut cfg = Config::default();
        cfg.pen.smoothing = 0.5;
        let mut m = PenMapper::new(INFO, cfg);
        m.frame(&pen(0, 0, 500));
        // pen jumps to x=600px (1000 raw); smoothed moves halfway
        assert_eq!(m.frame(&pen(1000, 0, 500)), Some(PenEvent::Move(300.0, 0.0)));
    }

    #[test]
    fn unchanged_position_emits_nothing() {
        let mut m = PenMapper::new(INFO, Config::default());
        m.frame(&pen(10, 10, 500));
        assert_eq!(m.frame(&pen(10, 10, 600)), None);
    }
}
