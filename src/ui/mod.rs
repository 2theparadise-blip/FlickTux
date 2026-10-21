//! Floating keyboard GUI module.

pub mod floating_window;

#[cfg(test)]
mod tests {
    use crate::core::keymap::{load_preset, Cell, Dir, PRESET_IDS};

    #[test]
    fn test_all_presets_span_defaults() {
        for id in &PRESET_IDS {
            let preset = load_preset(id, None).unwrap_or_else(|e| panic!("Failed loading {id}: {e}"));
            assert_eq!(preset.id, *id);
            for mode in &["kana", "katakana", "alpha", "number", "nav"] {
                if let Some(grid) = preset.grid(mode) {
                    for row in grid {
                        for cell in row {
                            assert!(cell.row_span() >= 1);
                            assert!(cell.col_span() >= 1);
                        }
                    }
                }
            }
        }
    }

    #[test]
    fn test_cell_span_deserialization() {
        let json_data = r#"{
            "type": "action",
            "label": "確定",
            "action": "enter",
            "style": "enter-cell",
            "rowSpan": 2,
            "colSpan": 1
        }"#;

        let cell: Cell = serde_json::from_str(json_data).expect("valid cell json");
        assert_eq!(cell.row_span(), 2);
        assert_eq!(cell.col_span(), 1);
    }

    #[test]
    fn test_flick_active_state_direction_flow() {
        use crate::core::flick_engine::direction;
        assert_eq!(direction(0.0, 0.0, 18.0), Dir::Center);
        assert_eq!(direction(0.0, -30.0, 18.0), Dir::Up);
        assert_eq!(direction(0.0, 30.0, 18.0), Dir::Down);
        assert_eq!(direction(-30.0, 0.0, 18.0), Dir::Left);
        assert_eq!(direction(30.0, 0.0, 18.0), Dir::Right);
    }
}
