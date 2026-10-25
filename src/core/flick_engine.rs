//! Flick / tap / multi-tap state machine. Pure logic: feed it pointer events in
//! keyboard-pixel coordinates (plus a millisecond clock) and it returns what
//! to type. No I/O, so it is unit-tested on any OS.

#![allow(dead_code)]

use std::collections::HashMap;

use super::config::{Config, FlickCommit};
use super::keymap::{Cell, Common, Dir, FlickData, Preset, MODES};
use super::keys::*;

/// What the engine wants typed.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Output {
    /// Type text (kana or ASCII) as romaji keystrokes.
    Text(String),
    /// Erase the previous character, then type this (dakuten / multi-tap).
    Replace(String),
    /// A special key press.
    Key(Stroke),
}

/// Flick direction from a pen displacement. `Center` below the threshold.
/// Angle is `atan2(dy, dx)` with y pointing down: right ±45°, down 45..135°.
pub fn direction(dx: f64, dy: f64, threshold: f64) -> Dir {
    if dx.hypot(dy) < threshold {
        return Dir::Center;
    }
    let a = dy.atan2(dx).to_degrees();
    if (-45.0..=45.0).contains(&a) {
        Dir::Right
    } else if a > 45.0 && a <= 135.0 {
        Dir::Down
    } else if (-135.0..-45.0).contains(&a) {
        Dir::Up
    } else {
        Dir::Left
    }
}

struct Press {
    /// None for action cells (already fired on touch-down).
    key: Option<(String, Option<FlickData>)>,
    start: (f64, f64),
    dir: Dir,
    committed: bool,
}

struct Toggle {
    key: String,
    index: usize,
    deadline_ms: u64,
}

pub struct Engine {
    cfg: Config,
    preset: Preset,
    common: Common,
    mode: String,
    press: Option<Press>,
    toggle: Option<Toggle>,
    last_char: String,
    shift_latched: bool,
    ctrl_latched: bool,
}

impl Engine {
    pub fn new(cfg: Config, preset: Preset, common: Common) -> Result<Self, String> {
        let mode = cfg.mode.clone();
        if preset.grid(&mode).is_none() {
            return Err(format!("preset {} has no mode {mode}", preset.id));
        }
        Ok(Self {
            cfg,
            preset,
            common,
            mode,
            press: None,
            toggle: None,
            last_char: String::new(),
            shift_latched: false,
            ctrl_latched: false,
        })
    }

    pub fn mode(&self) -> &str {
        &self.mode
    }

    pub fn preset(&self) -> &Preset {
        &self.preset
    }

    pub fn set_mode(&mut self, mode: &str) -> bool {
        if self.preset.grid(mode).is_some() {
            self.mode = mode.to_string();
            self.toggle = None;
            true
        } else {
            false
        }
    }

    /// Direction of the pen in the current press (for drawing the guide).
    pub fn current_dir(&self) -> Dir {
        self.press.as_ref().map_or(Dir::Center, |p| p.dir)
    }

    /// Grid cell (row, col) under a keyboard-pixel point.
    pub fn cell_at(&self, x: f64, y: f64) -> Option<(usize, usize)> {
        let (w, h) = (self.cfg.keyboard_width, self.cfg.keyboard_height);
        if x < 0.0 || y < 0.0 || x > w || y > h {
            return None;
        }
        let col = ((x / w) * self.preset.cols as f64) as usize;
        let row = ((y / h) * self.preset.rows as f64) as usize;
        Some((row.min(self.preset.rows - 1), col.min(self.preset.cols - 1)))
    }

    fn cell(&self, row: usize, col: usize) -> Option<&Cell> {
        self.preset.grid(&self.mode)?.get(row)?.get(col)
    }

    // ---- pointer events -------------------------------------------------

    pub fn pointer_down(&mut self, x: f64, y: f64, now_ms: u64) -> Vec<Output> {
        let _ = now_ms;
        self.press = None;
        let Some((r, c)) = self.cell_at(x, y) else { return vec![] };
        let Some(cell) = self.cell(r, c).cloned() else { return vec![] };
        match cell {
            // Plain keys fire the instant the pen touches (no lift needed).
            Cell::Action { action, .. } => {
                self.press = Some(Press { key: None, start: (x, y), dir: Dir::Center, committed: true });
                self.fire_action(&action)
            }
            Cell::Flick { key, flick_data, .. } => {
                self.press = Some(Press {
                    key: Some((key, flick_data)),
                    start: (x, y),
                    dir: Dir::Center,
                    committed: false,
                });
                vec![]
            }
        }
    }

    pub fn pointer_move(&mut self, x: f64, y: f64, _now_ms: u64) -> Vec<Output> {
        let threshold = self.cfg.flick_threshold_px;
        let commit = self.cfg.flick_commit;
        let ch = {
            let Some(p) = self.press.as_mut() else { return vec![] };
            if p.committed {
                return vec![];
            }
            p.dir = direction(x - p.start.0, y - p.start.1, threshold);
            if commit == FlickCommit::Threshold && p.dir != Dir::Center {
                let ch = p
                    .key
                    .as_ref()
                    .and_then(|(_, fd)| fd.as_ref())
                    .and_then(|fd| fd.get(p.dir))
                    .map(str::to_string);
                if ch.is_some() {
                    p.committed = true;
                }
                ch
            } else {
                None
            }
        };
        match ch {
            Some(ch) => {
                self.toggle = None;
                vec![self.type_char(ch)]
            }
            None => vec![],
        }
    }

    pub fn pointer_up(&mut self, now_ms: u64) -> Vec<Output> {
        let Some(p) = self.press.take() else { return vec![] };
        if p.committed {
            return vec![];
        }
        let Some((key, fd)) = p.key else { return vec![] };
        if p.dir == Dir::Center {
            return self.tap(&key, fd.as_ref(), now_ms);
        }
        // Release-commit mode: use the last direction.
        match fd.as_ref().and_then(|fd| fd.get(p.dir)).map(str::to_string) {
            Some(ch) => {
                self.toggle = None;
                vec![self.type_char(ch)]
            }
            None => vec![],
        }
    }

    // ---- typing ---------------------------------------------------------

    fn type_char(&mut self, ch: String) -> Output {
        self.last_char = ch.clone();
        Output::Text(ch)
    }

    fn replace_char(&mut self, ch: String) -> Output {
        self.last_char = ch.clone();
        Output::Replace(ch)
    }

    /// Tap on a flick key: multi-tap cycle (あ→い→う…) or the center char.
    fn tap(&mut self, key: &str, fd: Option<&FlickData>, now_ms: u64) -> Vec<Output> {
        let timeout = self.cfg.toggle_timeout_ms;
        if let Some(cycle) = self.common.toggle_cycles.get(key).cloned() {
            if cycle.is_empty() {
                return vec![];
            }
            let again = matches!(&self.toggle, Some(t) if t.key == key && now_ms < t.deadline_ms);
            if again {
                let t = self.toggle.as_mut().expect("checked above");
                t.index = (t.index + 1) % cycle.len();
                t.deadline_ms = now_ms + timeout;
                let ch = cycle[t.index].clone();
                return vec![self.replace_char(ch)];
            }
            self.toggle = Some(Toggle { key: key.to_string(), index: 0, deadline_ms: now_ms + timeout });
            return vec![self.type_char(cycle[0].clone())];
        }
        self.toggle = None;
        let ch = fd.and_then(|f| f.get(Dir::Center)).unwrap_or(key).to_string();
        vec![self.type_char(ch)]
    }

    fn nav_key(&self, code: u16) -> Output {
        Output::Key(Stroke { code, shift: self.shift_latched, ctrl: self.ctrl_latched })
    }

    fn fire_action(&mut self, action: &str) -> Vec<Output> {
        self.toggle = None;
        let plain = |code| vec![Output::Key(Stroke::plain(code))];
        match action {
            "backspace" => {
                self.last_char.clear();
                plain(KEY_BACKSPACE)
            }
            "next" => plain(KEY_RIGHT),
            "space" | "convert" => {
                self.last_char.clear();
                plain(KEY_SPACE)
            }
            "enter" => {
                self.last_char.clear();
                plain(KEY_ENTER)
            }
            "left" => vec![self.nav_key(KEY_LEFT)],
            "right" => vec![self.nav_key(KEY_RIGHT)],
            "up" => vec![self.nav_key(KEY_UP)],
            "down" => vec![self.nav_key(KEY_DOWN)],
            "home" => vec![self.nav_key(KEY_HOME)],
            "end" => vec![self.nav_key(KEY_END)],
            "page_up" => vec![self.nav_key(KEY_PAGEUP)],
            "page_down" => vec![self.nav_key(KEY_PAGEDOWN)],
            "tab" => {
                let s = Stroke { code: KEY_TAB, shift: self.shift_latched, ctrl: false };
                self.shift_latched = false;
                vec![Output::Key(s)]
            }
            "shift_tab" => vec![Output::Key(Stroke::shifted(KEY_TAB))],
            "esc" => plain(KEY_ESC),
            "delete" => plain(KEY_DELETE),
            "shift" => {
                self.shift_latched = !self.shift_latched;
                vec![]
            }
            "ctrl" => {
                self.ctrl_latched = !self.ctrl_latched;
                vec![]
            }
            "dakuten" => self.apply_dakuten(),
            "mode" => {
                let i = MODES.iter().position(|m| *m == self.mode).unwrap_or(0);
                let next = MODES[(i + 1) % MODES.len()];
                self.set_mode(next);
                vec![]
            }
            "number" => {
                let m = if self.mode == "number" { "kana" } else { "number" };
                self.set_mode(m);
                vec![]
            }
            "alpha" => {
                self.set_mode("alpha");
                vec![]
            }
            "kana" => {
                self.set_mode("kana");
                vec![]
            }
            "symbol" => {
                let m = if self.mode == "alpha" { "kana" } else { "alpha" };
                self.set_mode(m);
                vec![]
            }
            _ => vec![],
        }
    }

    fn apply_dakuten(&mut self) -> Vec<Output> {
        let map: &HashMap<String, String> = &self.common.dakuten_map;
        match map.get(&self.last_char).cloned() {
            Some(toggled) => vec![self.replace_char(toggled)],
            None => vec![],
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::core::keymap::{load_common, load_preset};

    fn engine_with(commit: FlickCommit) -> Engine {
        let cfg = Config { flick_commit: commit, ..Config::default() };
        Engine::new(cfg, load_preset("google", None).unwrap(), load_common().unwrap()).unwrap()
    }

    fn engine() -> Engine {
        engine_with(FlickCommit::Threshold)
    }

    // Google kana: 4 rows x 5 cols on 600x480 → cells 120x120.
    // Row 0: [mode, あ, か, さ, ⌫]
    const A: (f64, f64) = (180.0, 60.0); // あ
    const KA: (f64, f64) = (300.0, 60.0); // か
    const MODE: (f64, f64) = (60.0, 60.0);
    const BS: (f64, f64) = (540.0, 60.0);
    const DAKU: (f64, f64) = (180.0, 420.0); // row 3, col 1

    fn text(s: &str) -> Vec<Output> {
        vec![Output::Text(s.into())]
    }

    fn tap(e: &mut Engine, p: (f64, f64), now: u64) -> Vec<Output> {
        let mut o = e.pointer_down(p.0, p.1, now);
        o.extend(e.pointer_up(now));
        o
    }

    #[test]
    fn direction_quadrants_and_boundaries() {
        assert_eq!(direction(5.0, 5.0, 18.0), Dir::Center);
        assert_eq!(direction(30.0, 0.0, 18.0), Dir::Right);
        assert_eq!(direction(-30.0, 0.0, 18.0), Dir::Left);
        assert_eq!(direction(0.0, 30.0, 18.0), Dir::Down);
        assert_eq!(direction(0.0, -30.0, 18.0), Dir::Up);
        // exactly ±45° belongs to Right
        assert_eq!(direction(30.0, 30.0, 18.0), Dir::Right);
        assert_eq!(direction(30.0, -30.0, 18.0), Dir::Right);
        // just past 45° tips to Down / Up
        assert_eq!(direction(29.0, 30.0, 18.0), Dir::Down);
        assert_eq!(direction(29.0, -30.0, 18.0), Dir::Up);
        // -135° belongs to Up (per spec -135°..=-45°), past -135° tips to Left
        assert_eq!(direction(-30.0, 30.0, 18.0), Dir::Down);
        assert_eq!(direction(-30.0, -30.0, 18.0), Dir::Up);
        assert_eq!(direction(-31.0, -30.0, 18.0), Dir::Left);
        // threshold is inclusive
        assert_eq!(direction(18.0, 0.0, 18.0), Dir::Right);
        assert_eq!(direction(17.9, 0.0, 18.0), Dir::Center);
    }

    #[test]
    fn flick_commits_on_threshold_without_release() {
        let mut e = engine();
        assert!(e.pointer_down(A.0, A.1, 0).is_empty());
        assert!(e.pointer_move(A.0 - 10.0, A.1, 1).is_empty()); // below threshold
        assert_eq!(e.pointer_move(A.0 - 20.0, A.1, 2), text("い")); // left
        // further motion / release add nothing
        assert!(e.pointer_move(A.0 - 40.0, A.1, 3).is_empty());
        assert!(e.pointer_up(4).is_empty());
    }

    #[test]
    fn flick_all_directions() {
        for (dx, dy, want) in [(0.0, -25.0, "う"), (25.0, 0.0, "え"), (0.0, 25.0, "お")] {
            let mut e = engine();
            e.pointer_down(A.0, A.1, 0);
            assert_eq!(e.pointer_move(A.0 + dx, A.1 + dy, 1), text(want));
        }
    }

    #[test]
    fn release_mode_commits_on_lift_with_last_direction() {
        let mut e = engine_with(FlickCommit::Release);
        e.pointer_down(A.0, A.1, 0);
        assert!(e.pointer_move(A.0 + 25.0, A.1, 1).is_empty());
        assert_eq!(e.pointer_up(2), text("え"));
        // moving back to center before lifting turns it into a tap
        e.pointer_down(KA.0, KA.1, 10);
        e.pointer_move(KA.0 + 25.0, KA.1, 11);
        e.pointer_move(KA.0 + 2.0, KA.1, 12);
        assert_eq!(e.pointer_up(13), text("か"));
    }

    #[test]
    fn small_motion_is_a_tap() {
        let mut e = engine();
        e.pointer_down(A.0, A.1, 0);
        assert!(e.pointer_move(A.0 + 8.0, A.1 + 8.0, 1).is_empty());
        assert_eq!(e.pointer_up(2), text("あ"));
    }

    #[test]
    fn multi_tap_cycles_then_times_out() {
        let mut e = engine();
        assert_eq!(tap(&mut e, A, 0), text("あ"));
        assert_eq!(tap(&mut e, A, 200), vec![Output::Replace("い".into())]);
        assert_eq!(tap(&mut e, A, 400), vec![Output::Replace("う".into())]);
        // window restarts from the last tap: 400 + 500 = 900
        assert_eq!(tap(&mut e, A, 899), vec![Output::Replace("え".into())]);
        // expired → new character
        assert_eq!(tap(&mut e, A, 1500), text("あ"));
        // different key resets the cycle
        assert_eq!(tap(&mut e, KA, 1600), text("か"));
        assert_eq!(tap(&mut e, A, 1700), text("あ"));
    }

    #[test]
    fn cycle_wraps_around() {
        let mut e = engine();
        let mut t = 0;
        tap(&mut e, A, t);
        for _ in 0..4 {
            t += 100;
            tap(&mut e, A, t);
        }
        t += 100;
        assert_eq!(tap(&mut e, A, t), vec![Output::Replace("あ".into())]);
    }

    #[test]
    fn flick_cancels_multi_tap() {
        let mut e = engine();
        tap(&mut e, A, 0);
        e.pointer_down(A.0, A.1, 100);
        e.pointer_move(A.0, A.1 - 30.0, 101); // う
        e.pointer_up(102);
        assert_eq!(tap(&mut e, A, 200), text("あ"));
    }

    #[test]
    fn action_keys_fire_on_touch_down() {
        let mut e = engine();
        let down = e.pointer_down(BS.0, BS.1, 0);
        assert_eq!(down, vec![Output::Key(Stroke::plain(KEY_BACKSPACE))]);
        assert!(e.pointer_move(BS.0, BS.1 + 40.0, 1).is_empty());
        assert!(e.pointer_up(2).is_empty());
    }

    #[test]
    fn dakuten_replaces_last_char_and_cycles() {
        let mut e = engine();
        assert!(tap(&mut e, DAKU, 0).is_empty()); // nothing typed yet
        tap(&mut e, KA, 10);
        assert_eq!(tap(&mut e, DAKU, 20), vec![Output::Replace("が".into())]);
        assert_eq!(tap(&mut e, DAKU, 30), vec![Output::Replace("か".into())]);
        // backspace clears the memory
        tap(&mut e, BS, 40);
        assert!(tap(&mut e, DAKU, 50).is_empty());
    }

    #[test]
    fn mode_button_cycles_modes() {
        let mut e = engine();
        assert_eq!(e.mode(), "kana");
        tap(&mut e, MODE, 0);
        assert_eq!(e.mode(), "katakana");
        assert_eq!(tap(&mut e, A, 10), text("ア"));
        tap(&mut e, MODE, 20);
        assert_eq!(e.mode(), "alpha");
        tap(&mut e, MODE, 30);
        assert_eq!(e.mode(), "number");
        tap(&mut e, MODE, 40);
        assert_eq!(e.mode(), "nav");
        // in nav mode, the mode cycle button is at row 0, col 0 (MODE)
        tap(&mut e, MODE, 50);
        assert_eq!(e.mode(), "kana");
    }


    #[test]
    fn touches_outside_keyboard_are_ignored() {
        let mut e = engine();
        assert!(e.pointer_down(-5.0, 10.0, 0).is_empty());
        assert!(e.pointer_down(10.0, 9999.0, 0).is_empty());
        assert!(e.pointer_up(1).is_empty());
    }

    #[test]
    fn cell_at_edges() {
        let e = engine();
        assert_eq!(e.cell_at(0.0, 0.0), Some((0, 0)));
        assert_eq!(e.cell_at(600.0, 480.0), Some((3, 4)));
        assert_eq!(e.cell_at(119.9, 119.9), Some((0, 0)));
        assert_eq!(e.cell_at(120.0, 120.0), Some((1, 1)));
    }

    #[test]
    fn tenkey_nav_shift_latch() {
        let cfg = Config { layout: "tenkey".into(), mode: "nav".into(), ..Config::default() };
        let mut e = Engine::new(cfg, load_preset("tenkey", None).unwrap(), load_common().unwrap()).unwrap();
        // 5 rows x 4 cols on 600x480 → 150 x 96. Row 3 col 0 = Shift, row 2 col 0 = ◀ 左
        let shift = (75.0, 3.0 * 96.0 + 48.0);
        let left = (75.0, 2.0 * 96.0 + 48.0);
        assert!(tap(&mut e, shift, 0).is_empty());
        assert_eq!(tap(&mut e, left, 1), vec![Output::Key(Stroke { code: KEY_LEFT, shift: true, ctrl: false })]);
        tap(&mut e, shift, 2);
        assert_eq!(tap(&mut e, left, 3), vec![Output::Key(Stroke::plain(KEY_LEFT))]);
    }

    #[test]
    fn alpha_multi_tap_and_case_toggle() {
        let cfg = Config { mode: "alpha".into(), ..Config::default() };
        let mut e = Engine::new(cfg, load_preset("google", None).unwrap(), load_common().unwrap()).unwrap();
        // alpha row 0: [mode, @, abc, def, ⌫]; abc at col 2
        let abc = (300.0, 60.0);
        assert_eq!(tap(&mut e, abc, 0), text("a"));
        assert_eq!(tap(&mut e, abc, 100), vec![Output::Replace("b".into())]);
        // dakuten (a/A) toggles case of the last char
        assert_eq!(tap(&mut e, DAKU, 200), vec![Output::Replace("B".into())]);
    }
}
