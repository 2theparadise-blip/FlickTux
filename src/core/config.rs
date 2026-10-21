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
pub struct HookTriggerConfig {
    pub enabled: bool,
    pub input_device: Option<String>,
    pub key_code: String,
    pub on_offhook: String,
    pub on_onhook: String,
}

impl Default for HookTriggerConfig {
    fn default() -> Self {
        Self {
            enabled: false,
            input_device: None,
            key_code: "KEY_PHONE".into(),
            on_offhook: "xdg-open 'https://gemini.google.com'".into(),
            on_onhook: "".into(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct TabletConfig {
    pub device_name: String,
    pub vendor: String,
    pub pressure_curve_level: u32,
    pub threshold: f64,
    pub smoothing: f64,
    pub aspect_ratio_correction: bool,
}

impl Default for TabletConfig {
    fn default() -> Self {
        Self {
            device_name: "auto".into(),
            vendor: "auto".into(),
            pressure_curve_level: 3,
            threshold: 12.0,
            smoothing: 4.0,
            aspect_ratio_correction: true,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct NumpadDeviceConfig {
    pub enabled: bool,
    pub device_path: Option<String>,
    pub exclusive_grab: bool,
    pub mapping_preset: String,
}

impl Default for NumpadDeviceConfig {
    fn default() -> Self {
        Self {
            enabled: false,
            device_path: None,
            exclusive_grab: false,
            mapping_preset: "push_phone".into(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct WeylusConfig {
    pub enabled: bool,
    pub target_device: String,
    pub model: String,
    pub aspect_ratio_4_3: bool,
    pub palm_rejection: bool,
    pub ui_scale: f64,
}

impl Default for WeylusConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            target_device: "Weylus Stylus".into(),
            model: "ipad".into(),
            aspect_ratio_4_3: true,
            palm_rejection: true,
            ui_scale: 1.0,
        }
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
    pub hook_trigger: HookTriggerConfig,
    pub tablet: TabletConfig,
    pub numpad_device: NumpadDeviceConfig,
    pub weylus: WeylusConfig,
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
            hook_trigger: HookTriggerConfig::default(),
            tablet: TabletConfig::default(),
            numpad_device: NumpadDeviceConfig::default(),
            weylus: WeylusConfig::default(),
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
