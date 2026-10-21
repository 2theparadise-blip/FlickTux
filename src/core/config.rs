//! Settings (`configs/config.json`). Every field has a default, so a partial
//! or missing file is fine.

#![allow(dead_code)]

use std::path::Path;

use serde::{Deserialize, Serialize};

/// When a flick character is committed.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum FlickCommit {
    /// As soon as the pen travels past the threshold (fastest).
    Threshold,
    /// When the pen is lifted, using the last direction (correctable).
    Release,
}

/// Region of the tablet used as the keyboard, as fractions (0.0..=1.0).
#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
#[serde(default)]
pub struct Area {
    pub x: f64,
    pub y: f64,
    pub w: f64,
    pub h: f64,
}

impl Default for Area {
    fn default() -> Self {
        Self { x: 0.0, y: 0.0, w: 1.0, h: 1.0 }
    }
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
#[serde(default)]
pub struct PenConfig {
    /// Pen counts as touching at/above this fraction of max pressure.
    pub press_threshold: f64,
    /// ...and as lifted below this (lower than press → no chatter).
    pub release_threshold: f64,
    /// Position smoothing 0..=1 (1.0 = off, smaller = smoother but laggier).
    pub smoothing: f64,
}

impl Default for PenConfig {
    fn default() -> Self {
        Self { press_threshold: 0.03, release_threshold: 0.015, smoothing: 1.0 }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct Config {
    pub layout: String,
    pub mode: String,
    /// Virtual keyboard size in px (cells are width/cols x height/rows).
    pub keyboard_width: f64,
    pub keyboard_height: f64,
    /// Travel (in keyboard px) needed to count as a flick.
    pub flick_threshold_px: f64,
    pub flick_commit: FlickCommit,
    /// Multi-tap (garakei-style) window.
    pub toggle_timeout_ms: u64,
    pub tablet_area: Area,
    pub pen: PenConfig,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            layout: "google".into(),
            mode: "kana".into(),
            keyboard_width: 600.0,
            keyboard_height: 480.0,
            flick_threshold_px: 18.0,
            flick_commit: FlickCommit::Threshold,
            toggle_timeout_ms: 500,
            tablet_area: Area::default(),
            pen: PenConfig::default(),
        }
    }
}

impl Config {
    pub fn load(path: &Path) -> Result<Self, String> {
        let text = std::fs::read_to_string(path).map_err(|e| format!("{}: {e}", path.display()))?;
        serde_json::from_str(&text).map_err(|e| format!("{}: {e}", path.display()))
    }

    /// Load if the file exists, otherwise defaults.
    pub fn load_or_default(path: &Path) -> Result<Self, String> {
        if path.is_file() {
            Self::load(path)
        } else {
            Ok(Self::default())
        }
    }

    pub fn load_default() -> Self {
        Self::load_or_default(Path::new("configs/config.json")).unwrap_or_default()
    }

    pub fn save(&self, path: &Path) -> Result<(), String> {
        if let Some(parent) = path.parent() {
            let _ = std::fs::create_dir_all(parent);
        }
        let text = serde_json::to_string_pretty(self).map_err(|e| format!("serialize config: {e}"))?;
        std::fs::write(path, text).map_err(|e| format!("write config {}: {e}", path.display()))
    }

    pub fn save_default(&self) -> Result<(), String> {
        self.save(Path::new("configs/config.json"))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn partial_json_uses_defaults() {
        let c: Config = serde_json::from_str(r#"{"flick_threshold_px": 25, "flick_commit": "release"}"#).unwrap();
        assert_eq!(c.flick_threshold_px, 25.0);
        assert_eq!(c.flick_commit, FlickCommit::Release);
        assert_eq!(c.toggle_timeout_ms, 500);
        assert_eq!(c.layout, "google");
    }
}
