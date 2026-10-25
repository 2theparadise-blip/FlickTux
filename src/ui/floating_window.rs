//! Floating Window GUI for FlickTux (Phase 3).
//! Provides a non-focus stealing, transparent, floating on-screen flick keyboard
//! with stylus pen and multitouch support, cell span combining, and zero-allocation cross flick guide.

#[cfg(feature = "gui")]
pub mod native_gtk {
    use std::cell::RefCell;
    use std::rc::Rc;
    use std::sync::{Arc, Mutex};
    use std::time::{SystemTime, UNIX_EPOCH};

    use cairo::Context;
    use gdk::prelude::*;
    use gtk::glib;
    use gtk::prelude::*;
    use gtk::{
        Application, ApplicationWindow, Box as GtkBox, Button, ComboBoxText, CssProvider, DrawingArea,
        EventBox, Grid, Label, Orientation, Overlay, StyleContext,
    };

    use crate::core::config::{Config, FlickCommit};
    use crate::core::flick_engine::{direction, Output};
    use crate::core::keymap::{load_common, load_preset, Cell, Dir, FlickData, Preset, PRESET_IDS};
    use crate::core::keys::*;
    #[cfg(target_os = "linux")]
    use crate::uinput::emitter::VirtualKeyboard;

    const CSS: &str = r#"
    window {
        background-color: rgba(32, 33, 36, 0.95);
        border-radius: 12px;
        border: 1px solid rgba(95, 99, 104, 0.6);
    }
    .edge-frame {
        border-radius: 12px;
    }
    .header-bar {
        background-color: #202124;
        border-bottom: 1px solid #3c4043;
        padding: 4px 6px;
        border-radius: 12px 12px 0 0;
    }
    .layout-combo {
        background-color: #2b2c2f;
        color: #8ab4f8;
        border: 1px solid #5f6368;
        border-radius: 6px;
        font-size: 11px;
        font-weight: bold;
    }
    .layout-combo button {
        background: transparent;
        border: none;
        color: #e8eaed;
        font-size: 11px;
    }
    .tab-btn {
        background: transparent;
        border: 1px solid transparent;
        border-radius: 5px;
        color: #9aa0a6;
        font-size: 11px;
        font-weight: bold;
        padding: 3px 6px;
    }
    .tab-btn:hover {
        background-color: #303134;
        color: #e8eaed;
    }
    .tab-btn.active {
        background-color: #3c4043;
        color: #8ab4f8;
        border-color: #5f6368;
    }
    .key-cell {
        background-color: #303134;
        border-radius: 8px;
        border: 2px solid #202124;
        color: #e8eaed;
    }
    .key-cell:hover {
        background-color: #383a3d;
        border: 2px solid #8ab4f8;
    }
    .key-cell.key-pressed {
        background-color: #8ab4f8;
        border: 2px solid #8ab4f8;
        color: #202124;
    }
    .action-cell {
        background-color: #3c4043;
        border-radius: 8px;
        border: 2px solid #202124;
        color: #e8eaed;
    }
    .action-cell:hover {
        background-color: #484b50;
        border: 2px solid #a8c7fa;
    }
    .action-cell.key-pressed {
        background-color: #5f6368;
        border: 2px solid #a8c7fa;
    }
    .enter-cell {
        background-color: #8ab4f8;
        border-radius: 8px;
        border: 2px solid #202124;
        color: #202124;
        font-weight: bold;
    }
    .enter-cell:hover {
        background-color: #aecbfa;
        border: 2px solid #aecbfa;
    }
    .enter-cell.key-pressed {
        background-color: #d2e3fc;
        border: 2px solid #d2e3fc;
    }
    "#;

    #[derive(Clone)]
    pub struct FlickActiveState {
        pub center_x: f64,
        pub center_y: f64,
        pub start_x: f64,
        pub start_y: f64,
        pub flick_data: FlickData,
        pub current_dir: Dir,
        pub committed: bool,
    }

    pub struct FloatingWindow {
        pub window: ApplicationWindow,
        pub config: Rc<RefCell<Config>>,
        pub preset: Rc<RefCell<Preset>>,
        pub current_mode: Rc<RefCell<String>>,
        pub grid: Grid,
        pub overlay: Overlay,
        pub guide_area: DrawingArea,
        pub active_flick: Rc<RefCell<Option<FlickActiveState>>>,
        pub last_char: Rc<RefCell<String>>,
        pub tab_buttons: Rc<RefCell<Vec<(String, Button)>>>,
        #[cfg(target_os = "linux")]
        pub keyboard: Arc<Mutex<Option<VirtualKeyboard>>>,
    }

    impl FloatingWindow {
        pub fn new(app: &Application, config: Config) -> Self {
            let window = ApplicationWindow::new(app);

            // 1. Critical Window Properties for non-focus stealing virtual keyboard
            window.set_title("FlickTux");
            window.set_decorated(false);
            window.set_keep_above(true);
            window.set_skip_taskbar_hint(true);
            window.set_skip_pager_hint(true);
            window.set_accept_focus(false); // CRITICAL: Focus remains on target app (e.g. Krita/Editor)
            window.set_focus_on_map(false);
            window.set_type_hint(gdk::WindowTypeHint::Utility);
            window.set_resizable(false);
            window.set_support_multidevice(true); // Stylus + Multitouch support

            // Load CSS styling
            let provider = CssProvider::new();
            if provider.load_from_data(CSS.as_bytes()).is_ok() {
                StyleContext::add_provider_for_screen(
                    &gdk::Screen::default().expect("GDK screen"),
                    &provider,
                    gtk::STYLE_PROVIDER_PRIORITY_APPLICATION,
                );
            }

            let preset = load_preset(&config.layout, None).unwrap_or_else(|_| {
                load_preset("google", None).expect("google preset must be embedded")
            });
            let initial_mode = config.mode.clone();

            #[cfg(target_os = "linux")]
            let keyboard = Arc::new(Mutex::new(VirtualKeyboard::new().ok()));

            let config_rc = Rc::new(RefCell::new(config.clone()));
            let preset_rc = Rc::new(RefCell::new(preset));
            let current_mode_rc = Rc::new(RefCell::new(initial_mode));
            let active_flick_rc = Rc::new(RefCell::new(None));
            let last_char_rc = Rc::new(RefCell::new(String::new()));
            let tab_buttons_rc = Rc::new(RefCell::new(Vec::new()));

            let main_box = GtkBox::new(Orientation::Vertical, 0);
            main_box.style_context().add_class("edge-frame");

            let overlay = Overlay::new();
            let grid = Grid::new();
            grid.set_row_homogeneous(true);
            grid.set_column_homogeneous(true);

            // Header Bar (Dedicated Move Drag Handle)
            let header_eb = EventBox::new();
            header_eb.add_events(gdk::EventMask::BUTTON_PRESS_MASK);
            let header = GtkBox::new(Orientation::Horizontal, 2);
            header.style_context().add_class("header-bar");
            header_eb.add(&header);

            // Drag window to move via Header Bar
            let win_weak = window.downgrade();
            header_eb.connect_button_press_event(move |_widget, event| {
                if event.button() == 1 {
                    if let Some(win) = win_weak.upgrade() {
                        win.begin_move_drag(
                            event.button() as i32,
                            event.root().0 as i32,
                            event.root().1 as i32,
                            event.time(),
                        );
                        return Inhibit(true);
                    }
                }
                Inhibit(false)
            });

            // Unified Layout Selector (Single button / dropdown)
            let layout_combo = ComboBoxText::new();
            layout_combo.style_context().add_class("layout-combo");
            layout_combo.set_can_focus(false);

            let display_names = [
                ("google", "⌨ Google (Gboard 20キー)"),
                ("iphone", "⌨ iPhone (iOS 19キー)"),
                ("galaxy", "⌨ Galaxy (Samsung 20キー)"),
                ("tenkey", "⌨ 10キー (電卓式 20キー)"),
                ("push_phone", "⌨ プッシュボタン (電話式 12キー)"),
                ("garakei", "⌨ ガラケー (連打トグル 20キー)"),
            ];

            for (id, label) in &display_names {
                layout_combo.append(Some(id), label);
            }

            // Scan user custom keymaps
            let custom_dirs = [
                std::path::PathBuf::from("configs/keymaps/custom"),
                glib::home_dir().join(".config/flktux/custom"),
            ];
            for cdir in &custom_dirs {
                if let Ok(entries) = std::fs::read_dir(cdir) {
                    for entry in entries.flatten() {
                        let path = entry.path();
                        if path.extension().and_then(|s| s.to_str()) == Some("json") {
                            if let Some(stem) = path.file_stem().and_then(|s| s.to_str()) {
                                layout_combo.append(Some(stem), &format!("★ {stem} (カスタム)"));
                            }
                        }
                    }
                }
            }

            layout_combo.set_active_id(Some(&config.layout));

            let preset_c = preset_rc.clone();
            let grid_c = grid.clone();
            let mode_c = current_mode_rc.clone();
            let config_c = config_rc.clone();
            let active_c = active_flick_rc.clone();
            let overlay_c = overlay.clone();
            let guide_c = DrawingArea::new();
            let last_c = last_char_rc.clone();

            #[cfg(target_os = "linux")]
            let kb_c = keyboard.clone();

            layout_combo.connect_changed(move |combo| {
                if let Some(lid) = combo.active_id() {
                    let p_str = lid.as_str();
                    let custom_dirs = [
                        std::path::PathBuf::from("configs/keymaps/custom"),
                        glib::home_dir().join(".config/flktux/custom"),
                    ];
                    let mut found_preset = None;
                    for cdir in &custom_dirs {
                        if cdir.is_dir() {
                            if let Ok(p) = load_preset(p_str, Some(cdir)) {
                                found_preset = Some(p);
                                break;
                            }
                        }
                    }
                    if found_preset.is_none() {
                        found_preset = load_preset(p_str, None).ok();
                    }

                    if let Some(new_preset) = found_preset {
                        *preset_c.borrow_mut() = new_preset;
                        config_c.borrow_mut().layout = p_str.to_string();
                        Self::rebuild_keys_internal(
                            &grid_c,
                            &preset_c,
                            &mode_c,
                            &config_c,
                            &active_c,
                            &overlay_c,
                            &guide_c,
                            &last_c,
                            #[cfg(target_os = "linux")]
                            &kb_c,
                        );
                    }
                }
            });

            header.pack_start(&layout_combo, false, false, 2);

            // Close button
            let close_btn = Button::with_label("✕");
            close_btn.style_context().add_class("tab-btn");
            close_btn.set_can_focus(false);
            let win_c = window.clone();
            close_btn.connect_clicked(move |_| {
                win_c.close();
            });
            header.pack_end(&close_btn, false, false, 1);

            main_box.pack_start(&header_eb, false, false, 0);

            // Cross-Flick Preview Guide Overlay (Zero-allocation DrawingArea)
            let guide_area = DrawingArea::new();
            guide_area.set_no_show_all(true);
            let active_flick_c = active_flick_rc.clone();

            guide_area.connect_draw(move |_widget, cr| {
                if let Some(ref state) = *active_flick_c.borrow() {
                    Self::draw_cross_guide(
                        cr,
                        state.center_x,
                        state.center_y,
                        &state.flick_data,
                        state.current_dir,
                    );
                }
                Inhibit(false)
            });

            overlay.add(&grid);
            overlay.add_overlay(&guide_area);
            main_box.pack_start(&overlay, true, true, 4);
            window.add(&main_box);

            // Edge frame drag movement (allowing drag from keyboard edges)
            let win_weak_edge = window.downgrade();
            main_box.connect_button_press_event(move |_widget, event| {
                if event.button() == 3 {
                    // Right-click drag anywhere on frame to reposition
                    if let Some(win) = win_weak_edge.upgrade() {
                        win.begin_move_drag(
                            event.button() as i32,
                            event.root().0 as i32,
                            event.root().1 as i32,
                            event.time(),
                        );
                    }
                }
                Inhibit(false)
            });

            // Rebuild initial keys
            Self::rebuild_keys_internal(
                &grid,
                &preset_rc,
                &current_mode_rc,
                &config_rc,
                &active_flick_rc,
                &overlay,
                &guide_area,
                &last_char_rc,
                #[cfg(target_os = "linux")]
                &keyboard,
            );

            // Set size from config
            window.set_default_size(config.keyboard_width as i32, config.keyboard_height as i32);
            if config.keyboard_x >= 0.0 && config.keyboard_y >= 0.0 {
                window.move_(config.keyboard_x as i32, config.keyboard_y as i32);
            }

            // Window position persistence on move
            let config_persist = config_rc.clone();
            let win_weak_persist = window.downgrade();
            window.connect_configure_event(move |_win, _event| {
                if let Some(win) = win_weak_persist.upgrade() {
                    let (x, y) = win.position();
                    let mut cfg = config_persist.borrow_mut();
                    cfg.keyboard_x = x as f64;
                    cfg.keyboard_y = y as f64;
                    let _ = cfg.save_default();
                }
                false
            });

            Self {
                window,
                config: config_rc,
                preset: preset_rc,
                current_mode: current_mode_rc,
                grid,
                overlay,
                guide_area,
                active_flick: active_flick_rc,
                last_char: last_char_rc,
                tab_buttons: tab_buttons_rc,
                #[cfg(target_os = "linux")]
                keyboard,
            }
        }

        pub fn show(&self) {
            self.window.show_all();
        }

        /// Rebuild the grid buttons based on current preset and mode.
        #[allow(clippy::too_many_arguments)]
        fn rebuild_keys_internal(
            grid: &Grid,
            preset_rc: &Rc<RefCell<Preset>>,
            mode_rc: &Rc<RefCell<String>>,
            config_rc: &Rc<RefCell<Config>>,
            active_flick_rc: &Rc<RefCell<Option<FlickActiveState>>>,
            overlay: &Overlay,
            guide_area: &DrawingArea,
            last_char_rc: &Rc<RefCell<String>>,
            #[cfg(target_os = "linux")] keyboard: &Arc<Mutex<Option<VirtualKeyboard>>>,
        ) {
            // Remove existing children
            for child in grid.children() {
                grid.remove(&child);
            }

            let preset = preset_rc.borrow().clone();
            let mode = mode_rc.borrow().clone();
            let Some(matrix) = preset.grid(&mode) else { return };

            for (r, row) in matrix.iter().enumerate() {
                for (c, cell) in row.iter().enumerate() {
                    let event_box = EventBox::new();
                    event_box.set_visible_window(true);
                    event_box.add_events(
                        gdk::EventMask::BUTTON_PRESS_MASK
                            | gdk::EventMask::BUTTON_RELEASE_MASK
                            | gdk::EventMask::POINTER_MOTION_MASK
                            | gdk::EventMask::TOUCH_MASK,
                    );

                    let label = Label::new(None);
                    label.set_use_markup(true);

                    let cell_clone = cell.clone();
                    let col_span = cell.col_span() as i32;
                    let row_span = cell.row_span() as i32;

                    match &cell_clone {
                        Cell::Flick { key, num, .. } => {
                            event_box.style_context().add_class("key-cell");
                            if let Some(n) = num {
                                label.set_markup(&format!(
                                    "<span size='8500' color='#8ab4f8'>{}</span> <span size='14000' weight='bold' color='#ffffff'>{}</span>",
                                    glib::markup_escape_text(n),
                                    glib::markup_escape_text(key)
                                ));
                            } else {
                                label.set_markup(&format!(
                                    "<span size='15000' weight='bold' color='#ffffff'>{}</span>",
                                    glib::markup_escape_text(key)
                                ));
                            }
                        }
                        Cell::Action { label: lbl_text, action, style, .. } => {
                            let cls = style.as_deref().unwrap_or(if action == "enter" {
                                "enter-cell"
                            } else {
                                "action-cell"
                            });
                            event_box.style_context().add_class(cls);
                            let color = if cls == "enter-cell" { "#202124" } else { "#e8eaed" };
                            let font_size = if lbl_text.len() > 3 { "10000" } else { "12000" };
                            label.set_markup(&format!(
                                "<span size='{}' weight='bold' color='{}'>{}</span>",
                                font_size,
                                color,
                                glib::markup_escape_text(lbl_text)
                            ));
                        }
                    }

                    event_box.add(&label);

                    // Setup events
                    let eb_c = event_box.clone();
                    let overlay_c = overlay.clone();
                    let guide_c = guide_area.clone();
                    let active_c = active_flick_rc.clone();
                    let config_c = config_rc.clone();
                    let cell_for_press = cell_clone.clone();
                    let cell_for_motion = cell_clone.clone();
                    let cell_for_release = cell_clone.clone();
                    let mode_for_action = mode_rc.clone();
                    let preset_for_action = preset_rc.clone();
                    let grid_for_action = grid.clone();
                    let last_char_c = last_char_rc.clone();

                    #[cfg(target_os = "linux")]
                    let kb_c1 = keyboard.clone();
                    #[cfg(target_os = "linux")]
                    let kb_c2 = keyboard.clone();
                    #[cfg(target_os = "linux")]
                    let kb_c3 = keyboard.clone();

                    // 1. Button / Touch Press
                    event_box.connect_button_press_event(move |_widget, event| {
                        eb_c.style_context().add_class("key-pressed");
                        let (root_x, root_y) = (event.root().0, event.root().1);
                        let alloc = eb_c.allocation();
                        let (cx, cy) = eb_c
                            .translate_coordinates(&overlay_c, alloc.width() / 2, alloc.height() / 2)
                            .unwrap_or((alloc.width() / 2, alloc.height() / 2));

                        match &cell_for_press {
                            Cell::Flick { flick_data, .. } => {
                                let fd = flick_data.clone().unwrap_or_default();
                                *active_c.borrow_mut() = Some(FlickActiveState {
                                    center_x: cx as f64,
                                    center_y: cy as f64,
                                    start_x: root_x,
                                    start_y: root_y,
                                    flick_data: fd,
                                    current_dir: Dir::Center,
                                    committed: false,
                                });
                                guide_c.show();
                                guide_c.queue_draw();
                            }
                            Cell::Action { action, .. } => {
                                Self::execute_action(
                                    action,
                                    &mode_for_action,
                                    &preset_for_action,
                                    &grid_for_action,
                                    &config_c,
                                    &active_c,
                                    &overlay_c,
                                    &guide_c,
                                    &last_char_c,
                                    #[cfg(target_os = "linux")]
                                    &kb_c1,
                                );
                            }
                        }
                        Inhibit(true)
                    });

                    // 2. Motion (Pen / Finger Drag)
                    let eb_motion = event_box.clone();
                    let guide_motion = guide_area.clone();
                    let active_motion = active_flick_rc.clone();
                    let config_motion = config_rc.clone();
                    let last_char_motion = last_char_rc.clone();

                    event_box.connect_motion_notify_event(move |_widget, event| {
                        let (root_x, root_y) = (event.root().0, event.root().1);
                        if let Cell::Flick { .. } = &cell_for_motion {
                            let mut state_opt = active_motion.borrow_mut();
                            if let Some(ref mut state) = *state_opt {
                                let dx = root_x - state.start_x;
                                let dy = root_y - state.start_y;
                                let threshold = config_motion.borrow().flick_threshold_px;
                                let new_dir = direction(dx, dy, threshold);

                                if new_dir != state.current_dir {
                                    state.current_dir = new_dir;
                                    guide_motion.queue_draw();
                                }

                                // Instant Threshold Commit
                                if config_motion.borrow().flick_commit == FlickCommit::Threshold
                                    && !state.committed
                                    && new_dir != Dir::Center
                                {
                                    if let Some(ch) = state.flick_data.get(new_dir) {
                                        state.committed = true;
                                        *last_char_motion.borrow_mut() = ch.to_string();
                                        Self::emit_character(
                                            ch,
                                            #[cfg(target_os = "linux")]
                                            &kb_c2,
                                        );
                                    }
                                }
                            }
                        }
                        Inhibit(true)
                    });

                    // 3. Button / Touch Release
                    let eb_release = event_box.clone();
                    let guide_release = guide_area.clone();
                    let active_release = active_flick_rc.clone();
                    let last_char_release = last_char_rc.clone();

                    event_box.connect_button_release_event(move |_widget, _event| {
                        eb_release.style_context().remove_class("key-pressed");
                        guide_release.hide();

                        let state_opt = active_release.borrow_mut().take();
                        if let Some(state) = state_opt {
                            if !state.committed {
                                if let Some(ch) = state.flick_data.get(state.current_dir) {
                                    *last_char_release.borrow_mut() = ch.to_string();
                                    Self::emit_character(
                                        ch,
                                        #[cfg(target_os = "linux")]
                                        &kb_c3,
                                    );
                                }
                            }
                        }
                        Inhibit(true)
                    });

                    grid.attach(&event_box, c as i32, r as i32, col_span, row_span);
                }
            }
            grid.show_all();
        }

        /// Execute action button event (mode switch, enter, backspace, dakuten, etc.)
        #[allow(clippy::too_many_arguments)]
        fn execute_action(
            action: &str,
            mode_rc: &Rc<RefCell<String>>,
            preset_rc: &Rc<RefCell<Preset>>,
            grid: &Grid,
            config_rc: &Rc<RefCell<Config>>,
            active_flick_rc: &Rc<RefCell<Option<FlickActiveState>>>,
            overlay: &Overlay,
            guide_area: &DrawingArea,
            last_char_rc: &Rc<RefCell<String>>,
            #[cfg(target_os = "linux")] keyboard: &Arc<Mutex<Option<VirtualKeyboard>>>,
        ) {
            match action {
                "mode" => {
                    let next_mode = match mode_rc.borrow().as_str() {
                        "kana" => "katakana",
                        "katakana" => "alpha",
                        "alpha" => "number",
                        "number" => "nav",
                        _ => "kana",
                    };
                    *mode_rc.borrow_mut() = next_mode.to_string();
                    Self::rebuild_keys_internal(
                        grid,
                        preset_rc,
                        mode_rc,
                        config_rc,
                        active_flick_rc,
                        overlay,
                        guide_area,
                        last_char_rc,
                        #[cfg(target_os = "linux")]
                        keyboard,
                    );
                }
                "number" => {
                    let current = mode_rc.borrow().clone();
                    *mode_rc.borrow_mut() = if current == "number" {
                        "kana".to_string()
                    } else {
                        "number".to_string()
                    };
                    Self::rebuild_keys_internal(
                        grid,
                        preset_rc,
                        mode_rc,
                        config_rc,
                        active_flick_rc,
                        overlay,
                        guide_area,
                        last_char_rc,
                        #[cfg(target_os = "linux")]
                        keyboard,
                    );
                }
                "alpha" => {
                    *mode_rc.borrow_mut() = "alpha".to_string();
                    Self::rebuild_keys_internal(
                        grid,
                        preset_rc,
                        mode_rc,
                        config_rc,
                        active_flick_rc,
                        overlay,
                        guide_area,
                        last_char_rc,
                        #[cfg(target_os = "linux")]
                        keyboard,
                    );
                }
                "kana" => {
                    *mode_rc.borrow_mut() = "kana".to_string();
                    Self::rebuild_keys_internal(
                        grid,
                        preset_rc,
                        mode_rc,
                        config_rc,
                        active_flick_rc,
                        overlay,
                        guide_area,
                        last_char_rc,
                        #[cfg(target_os = "linux")]
                        keyboard,
                    );
                }
                "symbol" => {
                    let current = mode_rc.borrow().clone();
                    *mode_rc.borrow_mut() = if current == "nav" {
                        "kana".to_string()
                    } else {
                        "nav".to_string()
                    };
                    Self::rebuild_keys_internal(
                        grid,
                        preset_rc,
                        mode_rc,
                        config_rc,
                        active_flick_rc,
                        overlay,
                        guide_area,
                        last_char_rc,
                        #[cfg(target_os = "linux")]
                        keyboard,
                    );
                }
                "dakuten" => {
                    let common = load_common().unwrap_or(crate::core::keymap::Common {
                        toggle_cycles: std::collections::HashMap::new(),
                        dakuten_map: std::collections::HashMap::new(),
                    });
                    let prev = last_char_rc.borrow().clone();
                    if let Some(next_ch) = common.dakuten_map.get(&prev) {
                        *last_char_rc.borrow_mut() = next_ch.clone();
                        Self::emit_replace(
                            next_ch,
                            #[cfg(target_os = "linux")]
                            keyboard,
                        );
                    }
                }
                "enter" => {
                    Self::emit_key(
                        KEY_ENTER,
                        false,
                        false,
                        #[cfg(target_os = "linux")]
                        keyboard,
                    );
                }
                "backspace" => {
                    Self::emit_key(
                        KEY_BACKSPACE,
                        false,
                        false,
                        #[cfg(target_os = "linux")]
                        keyboard,
                    );
                }
                "space" => {
                    Self::emit_key(
                        KEY_SPACE,
                        false,
                        false,
                        #[cfg(target_os = "linux")]
                        keyboard,
                    );
                }
                "left" => {
                    Self::emit_key(
                        KEY_LEFT,
                        false,
                        false,
                        #[cfg(target_os = "linux")]
                        keyboard,
                    );
                }
                "right" => {
                    Self::emit_key(
                        KEY_RIGHT,
                        false,
                        false,
                        #[cfg(target_os = "linux")]
                        keyboard,
                    );
                }
                "up" => {
                    Self::emit_key(
                        KEY_UP,
                        false,
                        false,
                        #[cfg(target_os = "linux")]
                        keyboard,
                    );
                }
                "down" => {
                    Self::emit_key(
                        KEY_DOWN,
                        false,
                        false,
                        #[cfg(target_os = "linux")]
                        keyboard,
                    );
                }
                "esc" => {
                    Self::emit_key(
                        KEY_ESC,
                        false,
                        false,
                        #[cfg(target_os = "linux")]
                        keyboard,
                    );
                }
                "tab" => {
                    Self::emit_key(
                        KEY_TAB,
                        false,
                        false,
                        #[cfg(target_os = "linux")]
                        keyboard,
                    );
                }
                "delete" => {
                    Self::emit_key(
                        KEY_DELETE,
                        false,
                        false,
                        #[cfg(target_os = "linux")]
                        keyboard,
                    );
                }
                _ => {}
            }
        }

        fn emit_character(
            ch: &str,
            #[cfg(target_os = "linux")] keyboard: &Arc<Mutex<Option<VirtualKeyboard>>>,
        ) {
            #[cfg(target_os = "linux")]
            {
                if let Ok(mut lock) = keyboard.lock() {
                    if let Some(ref mut kb) = *lock {
                        let is_kana = ch.chars().any(|c| ('\u{3040}'..='\u{30FF}').contains(&c));
                        if is_kana {
                            let _ = kb.emit_kana(ch);
                        } else {
                            let _ = kb.emit_text(ch);
                        }
                    }
                }
            }
            #[cfg(not(target_os = "linux"))]
            {
                let _ = ch;
            }
        }

        fn emit_replace(
            ch: &str,
            #[cfg(target_os = "linux")] keyboard: &Arc<Mutex<Option<VirtualKeyboard>>>,
        ) {
            #[cfg(target_os = "linux")]
            {
                if let Ok(mut lock) = keyboard.lock() {
                    if let Some(ref mut kb) = *lock {
                        let _ = kb.emit_key(&Stroke::new(KEY_BACKSPACE, false, false));
                        let is_kana = ch.chars().any(|c| ('\u{3040}'..='\u{30FF}').contains(&c));
                        if is_kana {
                            let _ = kb.emit_kana(ch);
                        } else {
                            let _ = kb.emit_text(ch);
                        }
                    }
                }
            }
            #[cfg(not(target_os = "linux"))]
            {
                let _ = ch;
            }
        }

        fn emit_key(
            keycode: u16,
            shift: bool,
            ctrl: bool,
            #[cfg(target_os = "linux")] keyboard: &Arc<Mutex<Option<VirtualKeyboard>>>,
        ) {
            #[cfg(target_os = "linux")]
            {
                if let Ok(mut lock) = keyboard.lock() {
                    if let Some(ref mut kb) = *lock {
                        let _ = kb.emit_key(&Stroke::new(keycode, shift, ctrl));
                    }
                }
            }
            #[cfg(not(target_os = "linux"))]
            {
                let _ = (keycode, shift, ctrl);
            }
        }

        /// Render cross flick preview guide with smooth Cairo graphics.
        pub fn draw_cross_guide(cr: &Context, cx: f64, cy: f64, fd: &FlickData, sel_dir: Dir) {
            let arm_len = 44.0;
            let radius = 24.0;

            // Semi-transparent background disc
            cr.set_source_rgba(0.12, 0.13, 0.15, 0.90);
            let _ = cr.arc(cx, cy, arm_len + radius + 4.0, 0.0, 2.0 * std::f64::consts::PI);
            let _ = cr.fill();

            // Draw petals for each direction
            let dirs = [
                (Dir::Center, cx, cy, fd.get(Dir::Center)),
                (Dir::Up, cx, cy - arm_len, fd.get(Dir::Up)),
                (Dir::Down, cx, cy + arm_len, fd.get(Dir::Down)),
                (Dir::Left, cx - arm_len, cy, fd.get(Dir::Left)),
                (Dir::Right, cx + arm_len, cy, fd.get(Dir::Right)),
            ];

            for (dir, x, y, char_opt) in dirs {
                if let Some(ch) = char_opt {
                    let is_sel = dir == sel_dir;
                    if is_sel {
                        cr.set_source_rgb(0.54, 0.71, 0.97); // Google Blue #8ab4f8
                    } else {
                        cr.set_source_rgba(0.24, 0.25, 0.27, 0.95);
                    }
                    let _ = cr.arc(x, y, radius, 0.0, 2.0 * std::f64::consts::PI);
                    let _ = cr.fill();

                    // Text
                    if is_sel {
                        cr.set_source_rgb(0.12, 0.13, 0.15);
                    } else {
                        cr.set_source_rgb(0.95, 0.95, 0.95);
                    }
                    cr.select_font_face("Sans", cairo::FontSlant::Normal, cairo::FontWeight::Bold);
                    cr.set_font_size(17.0);

                    if let Ok(ext) = cr.text_extents(ch) {
                        cr.move_to(
                            x - ext.width() / 2.0 - ext.x_bearing(),
                            y - ext.height() / 2.0 - ext.y_bearing(),
                        );
                        let _ = cr.show_text(ch);
                    }
                }
            }
        }
    }
}

/// Fallback / CLI launcher for Floating UI
pub fn launch_ui() -> Result<(), Box<dyn std::error::Error>> {
    #[cfg(feature = "gui")]
    {
        use gtk::prelude::*;
        use gtk::Application;
        let app = Application::new(Some("org.flicktux.keyboard"), Default::default());
        app.connect_activate(|app| {
            let cfg = crate::core::config::Config::default();
            let win = native_gtk::FloatingWindow::new(app, cfg);
            win.show();
        });
        app.run();
        Ok(())
    }
    #[cfg(not(feature = "gui"))]
    {
        println!("FlickTux Floating GUI");
        let mut cmd = std::process::Command::new("python3");
        cmd.env("PYTHONPATH", "/opt/flicktux");
        cmd.args(&[
            "-c",
            "import sys; sys.path.insert(0, '/opt/flicktux'); from flktux.ui import main; main()",
        ]);

        let status = cmd.status();
        match status {
            Ok(s) => {
                if !s.success() {
                    eprintln!("UI exited with status: {s}");
                }
                Ok(())
            }
            Err(e) => {
                Err(format!("Could not launch UI: {e}").into())
            }
        }
    }
}
