//! Keymap data model. Presets are exported from the Python layouts
//! (`scripts/export_presets.py`) and embedded into the binary; a file in a
//! custom directory with the same id takes priority.

use std::collections::HashMap;
use std::path::Path;

use serde::{Deserialize, Serialize};

/// Characters for each flick direction (all optional).
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct FlickData {
    #[serde(default)]
    pub center: Option<String>,
    #[serde(default)]
    pub left: Option<String>,
    #[serde(default)]
    pub up: Option<String>,
    #[serde(default)]
    pub right: Option<String>,
    #[serde(default)]
    pub down: Option<String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Dir {
    Center,
    Up,
    Down,
    Left,
    Right,
}

impl FlickData {
    pub fn get(&self, dir: Dir) -> Option<&str> {
        let s = match dir {
            Dir::Center => &self.center,
            Dir::Up => &self.up,
            Dir::Down => &self.down,
            Dir::Left => &self.left,
            Dir::Right => &self.right,
        };
        s.as_deref().filter(|s| !s.is_empty())
    }
}

/// One cell of the grid.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "lowercase")]
pub enum Cell {
    Flick {
        key: String,
        #[serde(default)]
        num: Option<String>,
        #[serde(default)]
        flick_data: Option<FlickData>,
        #[serde(default = "default_span", alias = "rowSpan")]
        row_span: usize,
        #[serde(default = "default_span", alias = "colSpan")]
        col_span: usize,
    },
    Action {
        label: String,
        action: String,
        #[serde(default)]
        num: Option<String>,
        #[serde(default)]
        style: Option<String>,
        #[serde(default = "default_span", alias = "rowSpan")]
        row_span: usize,
        #[serde(default = "default_span", alias = "colSpan")]
        col_span: usize,
    },
}

fn default_span() -> usize {
    1
}

impl Cell {
    #[allow(dead_code)]
    pub fn row_span(&self) -> usize {
        match self {
            Cell::Flick { row_span, .. } => *row_span,
            Cell::Action { row_span, .. } => *row_span,
        }
    }

    #[allow(dead_code)]
    pub fn col_span(&self) -> usize {
        match self {
            Cell::Flick { col_span, .. } => *col_span,
            Cell::Action { col_span, .. } => *col_span,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Preset {
    pub id: String,
    pub name: String,
    pub rows: usize,
    pub cols: usize,
    /// mode name (kana / katakana / alpha / number / nav) → rows of cells
    pub modes: HashMap<String, Vec<Vec<Cell>>>,
}

impl Preset {
    pub fn grid(&self, mode: &str) -> Option<&Vec<Vec<Cell>>> {
        self.modes.get(mode)
    }
}

/// Shared tables: tap-toggle cycles and dakuten / small-kana / case toggles.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Common {
    pub toggle_cycles: HashMap<String, Vec<String>>,
    pub dakuten_map: HashMap<String, String>,
}

pub const PRESET_IDS: [&str; 6] = ["google", "galaxy", "iphone", "garakei", "tenkey", "push_phone"];
pub const MODES: [&str; 5] = ["kana", "katakana", "alpha", "number", "nav"];

fn embedded(id: &str) -> Option<&'static str> {
    Some(match id {
        "google" => include_str!("../../configs/keymaps/presets/google.json"),
        "galaxy" => include_str!("../../configs/keymaps/presets/galaxy.json"),
        "iphone" => include_str!("../../configs/keymaps/presets/iphone.json"),
        "garakei" => include_str!("../../configs/keymaps/presets/garakei.json"),
        "tenkey" => include_str!("../../configs/keymaps/presets/tenkey.json"),
        "push_phone" => include_str!("../../configs/keymaps/presets/push_phone.json"),
        _ => return None,
    })
}

#[allow(dead_code)]
const COMMON_JSON: &str = include_str!("../../configs/keymaps/common.json");

/// Load a preset. `custom_dir/<id>.json` overrides the embedded one.
pub fn load_preset(id: &str, custom_dir: Option<&Path>) -> Result<Preset, String> {
    if let Some(dir) = custom_dir {
        let p = dir.join(format!("{id}.json"));
        if p.is_file() {
            let text = std::fs::read_to_string(&p).map_err(|e| format!("{}: {e}", p.display()))?;
            return serde_json::from_str(&text).map_err(|e| format!("{}: {e}", p.display()));
        }
    }
    let text = embedded(id).ok_or_else(|| format!("unknown preset: {id}"))?;
    serde_json::from_str(text).map_err(|e| format!("preset {id}: {e}"))
}

#[allow(dead_code)]
pub fn load_common() -> Result<Common, String> {
    serde_json::from_str(COMMON_JSON).map_err(|e| format!("common.json: {e}"))
}

/// Save a custom preset to disk.
pub fn save_custom_preset(preset: &Preset, custom_dir: Option<&Path>) -> Result<(), String> {
    let dir = match custom_dir {
        Some(d) => d.to_path_buf(),
        None => std::path::PathBuf::from("configs/keymaps/custom"),
    };
    std::fs::create_dir_all(&dir).map_err(|e| format!("create dir {}: {e}", dir.display()))?;
    let path = dir.join(format!("{}.json", preset.id));
    let text = serde_json::to_string_pretty(preset).map_err(|e| format!("serialize preset: {e}"))?;
    std::fs::write(&path, text).map_err(|e| format!("write {}: {e}", path.display()))?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn all_presets_parse_with_consistent_grids() {
        for id in PRESET_IDS {
            let p = load_preset(id, None).unwrap();
            for mode in MODES {
                let g = p.grid(mode).unwrap_or_else(|| panic!("{id}/{mode} missing"));
                assert_eq!(g.len(), p.rows, "{id}/{mode} rows");
                assert!(g.iter().all(|r| r.len() == p.cols), "{id}/{mode} cols");
            }
        }
    }

    #[test]
    fn google_kana_has_expected_cells() {
        let p = load_preset("google", None).unwrap();
        assert_eq!((p.rows, p.cols), (4, 5));
        match &p.grid("kana").unwrap()[0][1] {
            Cell::Flick { key, flick_data, .. } => {
                assert_eq!(key, "あ");
                assert_eq!(flick_data.as_ref().unwrap().get(Dir::Left), Some("い"));
            }
            _ => panic!("expected flick"),
        }
        let t = load_preset("tenkey", None).unwrap();
        assert_eq!((t.rows, t.cols), (5, 4));
    }

    #[test]
    fn common_tables() {
        let c = load_common().unwrap();
        assert_eq!(c.toggle_cycles["あ"], ["あ", "い", "う", "え", "お"]);
        assert_eq!(c.dakuten_map["は"], "ば");
        assert_eq!(c.dakuten_map["ぼ"], "ぽ");
    }
}
