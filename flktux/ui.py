#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
flktux.ui: Floating Multi-Mode Flick Keyboard UI
Supports 5 major layouts, 4 input modes (かな, カナ, 英語/ABC, 数字/123),
drag-to-move anywhere, position persistence, cross-flick guide, toggle typing,
and physical 10-key hardware integration.
"""

import os
import sys
PKG_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PKG_ROOT not in sys.path:
    sys.path.insert(0, PKG_ROOT)

import json
import math
import subprocess
import cairo
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib, Pango

try:
    from .xdo import XDO
    from .layouts import (
        get_layout,
        KANA_FLICKS,
        KATAKANA_FLICKS,
        ALPHA_FLICKS,
        NUMBER_FLICKS,
        TOGGLE_CYCLES,
        DAKUTEN_MAP,
    )
    from .numpad_listener import NumpadListener
    from .codepredict import CodePredictor, detect_active_window_mode
    from .handwriting import HandwritingPadWidget
except (ImportError, ValueError):
    from flktux.xdo import XDO
    from flktux.layouts import (
        get_layout,
        KANA_FLICKS,
        KATAKANA_FLICKS,
        ALPHA_FLICKS,
        NUMBER_FLICKS,
        TOGGLE_CYCLES,
        DAKUTEN_MAP,
    )
    from flktux.numpad_listener import NumpadListener
    from flktux.codepredict import CodePredictor, detect_active_window_mode
    from flktux.handwriting import HandwritingPadWidget

try:
    from Xlib import X, display as xdisplay
    HAS_XLIB = True
except Exception:
    HAS_XLIB = False


CONFIG_DIR = os.path.expanduser("~/.config/flktux")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
DEFAULT_TOGGLE_TIMEOUT_MS = 500  # 0.5s auto-commit
EDGE_MOVE_MARGIN = 12  # Outer edge margin width for window drag (12px per spec 3.3)

CSS_STYLE = b"""
window {
    background-color: transparent;
}
.edge-frame {
    background-color: #202124;
    border: 2px solid #3c4043;
    border-radius: 14px;
    padding: 4px;
}
.header-bar {
    background-color: #282a2d;
    padding: 2px 6px;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
}
.tab-btn {
    background-color: #35373a;
    color: #9aa0a6;
    border: 1px solid #484b50;
    border-radius: 6px;
    padding: 2px 6px;
    font-size: 10px;
    font-weight: bold;
    margin-right: 3px;
}
.tab-btn:hover {
    color: #ffffff;
    background-color: #404347;
}
.tab-btn-active {
    background-color: #8ab4f8;
    color: #202124;
    border: 1px solid #a8c7fa;
    border-radius: 6px;
    padding: 2px 6px;
    font-size: 10px;
    font-weight: bold;
    margin-right: 3px;
}
.layout-combo, .lang-combo {
    background-color: #2b2c2f;
    color: #8ab4f8;
    border: 1px solid #5f6368;
    border-radius: 6px;
    font-size: 10px;
    font-weight: bold;
}
.layout-combo button, .lang-combo button {
    background: transparent;
    border: none;
    color: #e8eaed;
    font-size: 10px;
}
.icon-btn {
    background: transparent;
    border: none;
    color: #9aa0a6;
    font-size: 12px;
    padding: 0 4px;
}
.icon-btn:hover {
    color: #8ab4f8;
}
.toggle-mode-btn {
    background-color: #35373a;
    color: #8ab4f8;
    border: 1px solid #5f6368;
    border-radius: 6px;
    font-size: 10px;
    font-weight: bold;
    padding: 1px 6px;
}
.toggle-mode-btn:hover {
    background-color: #8ab4f8;
    color: #202124;
}
.close-btn {
    background: transparent;
    border: none;
    color: #9aa0a6;
    font-size: 13px;
    padding: 0 4px;
}
.close-btn:hover {
    color: #f28b82;
}

/* ================= Prediction Strip ================= */
.pred-strip-box {
    background-color: #252629;
    padding: 1px 4px;
    border-radius: 6px;
    margin: 2px 4px 1px 4px;
}
.pred-btn {
    background-color: #303134;
    color: #a8c7fa;
    border: 1px solid #484b50;
    border-radius: 5px;
    padding: 1px 5px;
    font-size: 10px;
    font-family: monospace;
    font-weight: bold;
    margin: 1px 2px;
}
.pred-btn:hover {
    background-color: #8ab4f8;
    color: #202124;
}

/* ================= Text Display Bar ================= */
.display-bar {
    background-color: #17181a;
    border: 1px solid #3c4043;
    border-radius: 7px;
    padding: 3px 6px;
    margin: 1px 4px 2px 4px;
}
.display-text {
    font-size: 12px;
    font-family: sans-serif;
}
.display-action-btn {
    background: transparent;
    border: none;
    color: #9aa0a6;
    font-size: 11px;
    padding: 0 4px;
}
.display-action-btn:hover {
    color: #ffffff;
}

/* ================= Key Cells & Hover ================= */
.key-cell {
    background-color: #303134;
    border-radius: 7px;
    border: 2px solid #202124;
}
.key-cell:hover, .key-cell.key-hovered {
    background-color: #383a3d;
    border: 2px solid #8ab4f8;
}
.key-cell:active, .key-cell.key-pressed {
    background-color: #8ab4f8;
    border: 2px solid #8ab4f8;
}
.action-cell {
    background-color: #3c4043;
    border-radius: 7px;
    border: 2px solid #202124;
}
.action-cell:hover, .action-cell.key-hovered {
    background-color: #484b50;
    border: 2px solid #a8c7fa;
}
.action-cell:active, .action-cell.key-pressed {
    background-color: #5f6368;
    border: 2px solid #a8c7fa;
}
.enter-cell {
    background-color: #8ab4f8;
    border-radius: 7px;
    border: 2px solid #202124;
}
.enter-cell:hover {
    background-color: #aecbfa;
    border: 2px solid #aecbfa;
}
.enter-cell:active, .enter-cell.key-pressed {
    background-color: #d2e3fc;
    border: 2px solid #d2e3fc;
}

/* ================= Handwriting Pad UI ================= */
.handwriting-cand-bar {
    background-color: #252629;
    padding: 2px 4px;
    border-radius: 6px;
}
.cand-btn {
    background-color: #303134;
    color: #ffffff;
    border: 1px solid #5f6368;
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 13px;
    font-weight: bold;
}
.cand-btn:hover {
    background-color: #8ab4f8;
    color: #202124;
}
.cand-hint-label {
    color: #9aa0a6;
    font-size: 10px;
}
.stamp-btn {
    background-color: #1e8e3e;
    color: #ffffff;
    border: 1px solid #34a853;
    border-radius: 6px;
    font-size: 11px;
    font-weight: bold;
    padding: 3px 8px;
}
.stamp-btn:hover {
    background-color: #34a853;
}
.tool-btn {
    background-color: #35373a;
    color: #e8eaed;
    border: 1px solid #484b50;
    border-radius: 6px;
    font-size: 10px;
    padding: 3px 6px;
}
.tool-btn:hover {
    background-color: #484b50;
    color: #ffffff;
}
"""


class FlickOverlay(Gtk.DrawingArea):
    """フリック操作時に指・ペン先の上に浮き出る十字型プレビューガイド"""

    def __init__(self):
        super().__init__()
        self.set_halign(Gtk.Align.FILL)
        self.set_valign(Gtk.Align.FILL)
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.connect("draw", self.on_draw)
        self.active_data = None
        self.center_x = 0
        self.center_y = 0
        self.selected_dir = 'center'

    def show_guide(self, cx, cy, flick_data, selected_dir='center'):
        self.center_x = cx
        self.center_y = cy
        self.active_data = flick_data
        self.selected_dir = selected_dir
        self.show()
        self.queue_draw()

    def hide_guide(self):
        if self.active_data is not None:
            self.active_data = None
            self.queue_draw()

    def on_draw(self, widget, cr):
        if not self.active_data:
            return False

        cx, cy = self.center_x, self.center_y
        dist = 36
        r = 17

        bubbles = {
            'center': (cx, cy),
            'left':   (cx - dist, cy),
            'up':     (cx, cy - dist),
            'right':  (cx + dist, cy),
            'down':   (cx, cy + dist),
        }

        # Subtle cross backdrop
        cr.set_source_rgba(0.12, 0.13, 0.15, 0.75)
        cr.arc(cx, cy, dist + r + 2, 0, 2 * math.pi)
        cr.fill()

        for direction, (bx, by) in bubbles.items():
            char = self.active_data.get(direction)
            if not char:
                continue

            is_selected = (direction == self.selected_dir)
            if is_selected:
                cr.set_source_rgba(0.54, 0.71, 0.97, 0.95)
            else:
                cr.set_source_rgba(0.24, 0.25, 0.28, 0.88)
            cr.arc(bx, by, r, 0, 2 * math.pi)
            cr.fill()

            cr.set_source_rgba(0.6, 0.65, 0.7, 0.8)
            cr.set_line_width(1.5)
            cr.arc(bx, by, r, 0, 2 * math.pi)
            cr.stroke()

            if is_selected:
                cr.set_source_rgb(0.1, 0.1, 0.12)
            else:
                cr.set_source_rgb(1.0, 1.0, 1.0)

            cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            cr.set_font_size(18)
            extents = cr.text_extents(char)
            cr.move_to(bx - extents.width / 2 - extents.x_bearing, by - extents.height / 2 - extents.y_bearing)
            cr.show_text(char)

        return True


class FlickTuxWindow(Gtk.Window):
    """Floating Multi-Mode Flick Keyboard Window for Linux"""

    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)

        self.set_title("FlickTux")
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_accept_focus(False)  # CRITICAL: Keep focus on target app
        self.set_focus_on_map(False)
        self.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        self.set_resizable(False)
        self.set_app_paintable(True)
        self.set_support_multidevice(True)  # CRITICAL: Stylus pen & Multitouch support

        # Window icon (theme name first, then file fallbacks)
        try:
            self.set_icon_name("flicktux")
        except Exception:
            pass
        for icon_path in [
            "/usr/share/pixmaps/flicktux.png",
            "/opt/flicktux/assets/icon.png",
            "/opt/flicktux/assets/flicktux.png",
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "flicktux.png"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "icon.png"),
        ]:
            if os.path.exists(icon_path):
                try:
                    self.set_icon_from_file(icon_path)
                    break
                except Exception:
                    pass

        self.current_layout_name = "Google"
        self.input_mode = "kana"  # 'kana' | 'katakana' | 'alpha' | 'number' | 'nav'
        self.toggle_timeout_ms = DEFAULT_TOGGLE_TIMEOUT_MS
        self.saved_pos = None
        self.numpad_dev_path = None
        self.numpad_exclusive = False
        self.load_saved_config()

        self.last_char = ""
        self.drag_start = None
        self.active_cell = None
        self.press_button = 1
        self.current_dir = 'center'
        self.tab_buttons = {}
        self.current_matrix = []

        # Text Buffer State (Display Bar synchronization)
        self.committed_text = ""
        self.preedit_text = ""
        self.hover_tentative_char = ""
        self.hover_cell_widget = None

        # Code & Linux Command Predictor (Default: General mode)
        self.predictor = CodePredictor(mode="general")
        self.is_handwriting_mode = False

        # Modifiers State
        self.is_shift_latched = False
        self.is_ctrl_latched = False

        # Toggle state
        self.toggle_key = None
        self.toggle_index = 0
        self.toggle_timer_id = None

        # Numpad listener
        self.numpad_listener = NumpadListener(
            self.on_numpad_event,
            device_path=self.numpad_dev_path,
            exclusive_grab=self.numpad_exclusive
        )

        # Outer Edge Frame for 1-finger / 2-finger drag movement (Free moving, NO confinement)
        self.edge_frame = Gtk.EventBox()
        self.edge_frame.get_style_context().add_class("edge-frame")
        self.edge_frame.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.SCROLL_MASK
            | Gdk.EventMask.SMOOTH_SCROLL_MASK
        )
        self.edge_frame.connect("button-press-event", self.on_edge_press)
        self.edge_frame.connect("scroll-event", self.on_edge_scroll)
        self.add(self.edge_frame)

        # UI Layout Box inside edge frame
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.edge_frame.add(main_box)

        # ==================== 1. Header Bar (Dedicated Move Drag Handle) ====================
        header_eb = Gtk.EventBox()
        header_eb.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        header_eb.connect("button-press-event", self.on_header_press)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        header.get_style_context().add_class("header-bar")
        header_eb.add(header)

        # Unified Layout Selector (Plain text without emojis)
        self.layout_combo = Gtk.ComboBoxText()
        self.layout_combo.get_style_context().add_class("layout-combo")
        self.layout_combo.set_can_focus(False)

        self.layout_options = [
            ("Google", "Google"),
            ("iPhone", "iPhone"),
            ("Galaxy", "Galaxy"),
            ("10キー", "10キー"),
            ("プッシュボタン", "プッシュ"),
            ("ガラケー", "ガラケー"),
        ]

        custom_dir = os.path.expanduser("~/.config/flktux/custom")
        if os.path.isdir(custom_dir):
            for fname in sorted(os.listdir(custom_dir)):
                if fname.endswith(".json"):
                    cid = os.path.splitext(fname)[0]
                    self.layout_options.append((cid, cid))

        for lid, label in self.layout_options:
            self.layout_combo.append(lid, label)

        active_lid = self.current_layout_name if self.current_layout_name in [x[0] for x in self.layout_options] else "Google"
        self.layout_combo.set_active_id(active_lid)
        self.layout_combo.connect("changed", self.on_layout_combo_changed)
        header.pack_start(self.layout_combo, False, False, 1)

        # Mode / Language Selector (Plain text without emojis)
        self.lang_combo = Gtk.ComboBoxText()
        self.lang_combo.get_style_context().add_class("lang-combo")
        self.lang_combo.set_can_focus(False)
        for mid, mlabel in self.predictor.get_available_modes():
            self.lang_combo.append(mid, mlabel)
        self.lang_combo.set_active_id(self.predictor.mode)
        self.lang_combo.connect("changed", self.on_lang_combo_changed)
        header.pack_start(self.lang_combo, False, False, 1)

        header.pack_start(Gtk.Label(label=""), True, True, 0)  # Spacer

        # Handwriting / Keyboard Toggle Button (Plain text)
        self.handwriting_btn = Gtk.Button(label="手書き")
        self.handwriting_btn.get_style_context().add_class("toggle-mode-btn")
        self.handwriting_btn.set_tooltip_text("手書きパッドとキーボードを切り替え")
        self.handwriting_btn.connect("clicked", self.on_toggle_handwriting_mode)
        header.pack_end(self.handwriting_btn, False, False, 1)

        # Settings button
        settings_btn = Gtk.Button(label="設定")
        settings_btn.get_style_context().add_class("icon-btn")
        settings_btn.set_tooltip_text("ペンタブ感度・筆圧設定を開く")
        settings_btn.connect("clicked", self.on_open_settings)
        header.pack_end(settings_btn, False, False, 1)

        # Close button
        close_btn = Gtk.Button(label="✕")
        close_btn.get_style_context().add_class("close-btn")
        close_btn.connect("clicked", self.on_close_clicked)
        header.pack_end(close_btn, False, False, 1)

        main_box.pack_start(header_eb, False, False, 0)

        # ==================== 2. Code / Command Prediction Strip ====================
        self.pred_scroll = Gtk.ScrolledWindow()
        self.pred_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        self.pred_scroll.set_min_content_height(26)
        self.pred_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        self.pred_box.get_style_context().add_class("pred-strip-box")
        self.pred_scroll.add(self.pred_box)
        main_box.pack_start(self.pred_scroll, False, False, 1)

        # ==================== 3. Input String & Preedit Display Bar ====================
        self.display_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.display_bar.get_style_context().add_class("display-bar")

        self.display_icon = Gtk.Label(label="[入力]")
        self.display_bar.pack_start(self.display_icon, False, False, 2)

        self.display_label = Gtk.Label()
        self.display_label.set_use_markup(True)
        self.display_label.set_alignment(0.0, 0.5)
        self.display_label.set_ellipsize(Pango.EllipsizeMode.START)
        self.display_label.get_style_context().add_class("display-text")
        self.display_bar.pack_start(self.display_label, True, True, 2)

        # Backspace quick button in display bar
        btn_bs = Gtk.Button(label="⌫")
        btn_bs.get_style_context().add_class("display-action-btn")
        btn_bs.set_tooltip_text("1文字消去")
        btn_bs.connect("clicked", lambda w: self.handle_action("backspace"))
        self.display_bar.pack_end(btn_bs, False, False, 0)

        # Commit (Return) quick button in display bar
        btn_enter = Gtk.Button(label="↵")
        btn_enter.get_style_context().add_class("display-action-btn")
        btn_enter.set_tooltip_text("確定 (Enter)")
        btn_enter.connect("clicked", lambda w: self.handle_action("enter"))
        self.display_bar.pack_end(btn_enter, False, False, 0)

        # Clear display quick button
        btn_clear = Gtk.Button(label="✕")
        btn_clear.get_style_context().add_class("display-action-btn")
        btn_clear.set_tooltip_text("表示クリア")
        btn_clear.connect("clicked", self.on_clear_display_clicked)
        self.display_bar.pack_end(btn_clear, False, False, 0)

        main_box.pack_start(self.display_bar, False, False, 1)

        # ==================== 4. Main Body: Keyboard or Handwriting ====================
        self.body_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        main_box.pack_start(self.body_container, True, True, 0)

        # 4A. Keyboard Overlay
        self.overlay = Gtk.Overlay()
        self.grid = Gtk.Grid()
        self.grid.set_row_homogeneous(True)
        self.grid.set_column_homogeneous(True)
        self.grid.set_margin_start(4)
        self.grid.set_margin_end(4)
        self.grid.set_margin_bottom(4)
        self.overlay.add(self.grid)

        # Overlay Cross Guide
        self.flick_guide = FlickOverlay()
        self.overlay.add_overlay(self.flick_guide)
        self.overlay.set_overlay_pass_through(self.flick_guide, True)

        self.body_container.pack_start(self.overlay, True, True, 0)

        # 4B. Handwriting Pad Composite Widget
        self.handwriting_pad = HandwritingPadWidget(on_text_input=self.on_handwriting_input)
        self.handwriting_pad.set_no_show_all(True)
        self.body_container.pack_start(self.handwriting_pad, True, True, 0)

        # Apply CSS
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(CSS_STYLE)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self.rebuild_keys()
        self.update_display_bar()
        self.update_prediction_strip("")

        self.set_default_size(360, 290)
        if self.saved_pos:
            self.move(*self.saved_pos)
        else:
            self.position_at_bottom_right()

        self._pos_save_id = None
        self.connect("configure-event", self.on_configure)
        self.connect("destroy", self.on_window_destroy)

        if self.current_layout_name == "10キー":
            self.numpad_listener.start()

        # Background window auto-detector (every 2.5s)
        GLib.timeout_add(2500, self._auto_detect_window_mode)

    def on_window_destroy(self, widget):
        self._cancel_hover_timer()
        self._cancel_toggle_timer()

    def _auto_detect_window_mode(self):
        """アクティブウィンドウに応じてコマンド/言語モードを自動追従"""
        detected = detect_active_window_mode()
        if detected != self.predictor.mode:
            self.predictor.set_mode(detected)
            self.lang_combo.set_active_id(detected)
            self.update_prediction_strip(self.hover_tentative_char or self.preedit_text)
        return True

    def on_lang_combo_changed(self, combo):
        active_id = combo.get_active_id()
        if active_id:
            self.predictor.set_mode(active_id)
            self.update_prediction_strip(self.hover_tentative_char or self.preedit_text)

    def on_toggle_handwriting_mode(self, btn):
        self.is_handwriting_mode = not self.is_handwriting_mode
        if self.is_handwriting_mode:
            self.overlay.hide()
            self.handwriting_pad.show_all()
            self.handwriting_btn.set_label("⌨ キー")
            self.display_icon.set_text("✍")
        else:
            self.handwriting_pad.hide()
            self.overlay.show()
            self.handwriting_btn.set_label("✍ 手書き")
            self.display_icon.set_text("🔤")

    def on_handwriting_input(self, text: str):
        self.commit_toggle()
        self.type_char(text)
        self.committed_text += text
        self.update_display_bar()
        self.update_prediction_strip("")

    def on_clear_display_clicked(self, btn):
        self.committed_text = ""
        self.preedit_text = ""
        self.hover_tentative_char = ""
        self.update_display_bar()
        self.update_prediction_strip("")

    def update_display_bar(self):
        """表示スペースの描画更新 (確定テキスト＋下線付き仮入力テキスト)"""
        comm = GLib.markup_escape_text(self.committed_text[-25:] if len(self.committed_text) > 25 else self.committed_text)
        pre = GLib.markup_escape_text(self.preedit_text or self.hover_tentative_char)

        if not comm and not pre:
            self.display_label.set_markup("<span color='#5f6368'>文字またはコマンドを入力...</span>")
        else:
            markup = f"<span color='#ffffff' weight='bold'>{comm}</span>"
            if pre:
                markup += f"<span color='#8ab4f8' underline='single' weight='bold'> {pre}</span>"
            self.display_label.set_markup(markup)

    def update_prediction_strip(self, prefix: str):
        """コード／Linuxコマンド予測候補バーの更新"""
        for child in self.pred_box.get_children():
            self.pred_box.remove(child)

        candidates = self.predictor.predict(prefix, max_results=8)
        for label, insert_text, back_steps in candidates:
            btn = Gtk.Button(label=label)
            btn.get_style_context().add_class("pred-btn")
            btn.connect("clicked", self.on_prediction_clicked, insert_text, back_steps)
            self.pred_box.pack_start(btn, False, False, 1)

        self.pred_box.show_all()

    def on_prediction_clicked(self, btn, insert_text: str, back_steps: int):
        """予測候補をタップしてエディタへスマート挿入"""
        # 直前にホバー予備文字があれば取り消す
        if self.hover_tentative_char:
            XDO.key("BackSpace")
            self.hover_tentative_char = ""

        self.commit_toggle()
        XDO.type(insert_text)

        # カッコ等の自動復帰
        if back_steps > 0:
            for _ in range(back_steps):
                XDO.key("Left")

        self.committed_text += insert_text.strip()
        self.preedit_text = ""
        self.update_display_bar()
        self.update_prediction_strip("")

    def on_edge_press(self, widget, event):
        alloc = widget.get_allocation()
        w, h = alloc.width, alloc.height
        x, y = event.x, event.y
        margin = EDGE_MOVE_MARGIN
        is_on_edge = (x < margin or x > w - margin or y < margin or y > h - margin)
        if event.button == 1:
            # 外周 12px マージン内での押下のみ移動ドラッグを開始 (キー領域等の内部誤爆を完全防止)
            if is_on_edge:
                self.begin_move_drag(event.button, int(event.x_root), int(event.y_root), event.time)
                return True
        return False

    def on_edge_scroll(self, widget, event):
        has_delta, dx, dy = event.get_scroll_deltas()
        if not has_delta:
            direction = event.direction
            dx, dy = 0.0, 0.0
            if direction == Gdk.ScrollDirection.UP:
                dy = -1.0
            elif direction == Gdk.ScrollDirection.DOWN:
                dy = 1.0
            elif direction == Gdk.ScrollDirection.LEFT:
                dx = -1.0
            elif direction == Gdk.ScrollDirection.RIGHT:
                dx = 1.0

        cur_x, cur_y = self.get_position()
        move_speed = 22.0
        new_x = int(cur_x + dx * move_speed)
        new_y = int(cur_y + dy * move_speed)
        self.move(new_x, new_y)
        return True

    def on_configure(self, widget, event):
        if self._pos_save_id is not None:
            GLib.source_remove(self._pos_save_id)
        self._pos_save_id = GLib.timeout_add(400, self._save_pos)
        return False

    def _save_pos(self):
        self._pos_save_id = None
        x, y = self.get_position()
        self.saved_pos = (x, y)
        self.save_layout(self.current_layout_name)
        return False

    def position_at_bottom_right(self):
        try:
            display = Gdk.Display.get_default()
            if display:
                monitor = display.get_primary_monitor() or (display.get_monitor(0) if display.get_n_monitors() > 0 else None)
                if monitor:
                    geom = monitor.get_geometry()
                    self.move(max(10, geom.x + geom.width - 380), max(10, geom.y + geom.height - 310))
                    return
        except Exception:
            pass
        self.move(100, 100)

    def load_saved_config(self):
        self.saved_pos = None
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.current_layout_name = data.get("layout", "Google")
                    self.input_mode = data.get("mode", "kana")
                    self.toggle_timeout_ms = int(data.get("toggle_timeout_ms", DEFAULT_TOGGLE_TIMEOUT_MS))
                    np_cfg = data.get("numpad_device", {})
                    self.numpad_dev_path = np_cfg.get("device_path")
                    self.numpad_exclusive = np_cfg.get("exclusive_grab", False)
                    if "window_x" in data and "window_y" in data:
                        self.saved_pos = (int(data["window_x"]), int(data["window_y"]))
                    return
        except Exception:
            pass
        self.current_layout_name = "Google"
        self.input_mode = "kana"
        self.toggle_timeout_ms = DEFAULT_TOGGLE_TIMEOUT_MS

    def save_layout(self, layout_name):
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            cfg = {
                "layout": layout_name,
                "mode": self.input_mode,
                "toggle_timeout_ms": self.toggle_timeout_ms
            }
            if self.saved_pos:
                cfg["window_x"], cfg["window_y"] = self.saved_pos
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[flktux] Error saving config: {e}", file=sys.stderr)

    def on_header_press(self, widget, event):
        if event.button == 1:
            self.begin_move_drag(event.button, int(event.x_root), int(event.y_root), event.time)
            return True
        return False

    def on_open_settings(self, widget):
        from .settings_gui import SettingsDialog
        win = SettingsDialog()
        win.show_all()

    def on_close_clicked(self, widget):
        self.destroy()
        Gtk.main_quit()

    def on_layout_combo_changed(self, combo):
        lid = combo.get_active_id()
        if lid and lid != self.current_layout_name:
            self.current_layout_name = lid
            self.save_layout(lid)
            self.rebuild_keys()

            if lid in ("10キー", "プッシュボタン"):
                self.numpad_listener.start()
            else:
                self.numpad_listener.stop()

    def on_tab_clicked(self, btn, layout_name):
        if self.current_layout_name != layout_name:
            self.current_layout_name = layout_name
            self.save_layout(layout_name)
            if hasattr(self, 'layout_combo'):
                self.layout_combo.set_active_id(layout_name)
            self.rebuild_keys()

            if layout_name in ("10キー", "プッシュボタン"):
                self.numpad_listener.start()
            else:
                self.numpad_listener.stop()

    def rebuild_keys(self):
        for child in self.grid.get_children():
            self.grid.remove(child)

        # Check for user custom keymap first
        custom_file = os.path.expanduser(f"~/.config/flktux/custom/{self.current_layout_name}.json")
        if os.path.isfile(custom_file):
            try:
                import json
                with open(custom_file, "r", encoding="utf-8") as f:
                    cdata = json.load(f)
                    self.current_matrix = cdata.get("modes", {}).get(self.input_mode, [])
            except Exception as e:
                print(f"Failed loading custom layout {self.current_layout_name}: {e}")
                self.current_matrix = get_layout("Google", self.input_mode)
        else:
            self.current_matrix = get_layout(self.current_layout_name, self.input_mode)

        for r, row in enumerate(self.current_matrix):
            for c, cell_info in enumerate(row):
                widget = self.create_cell_widget(cell_info)
                self.grid.attach(widget, c, r, 1, 1)

        # Adjust window size dynamically based on matrix rows and cols
        rows = len(self.current_matrix)
        cols = len(self.current_matrix[0]) if rows > 0 else 5
        target_w = max(240, cols * 70 + 15)
        target_h = max(270, rows * 64 + 35)
        self.set_size_request(target_w, target_h)
        self.resize(target_w, target_h)
        self.grid.show_all()

    def snap_pointer_to_cell_center(self, widget, event):
        """セルの中央座標を計算 (ポインタは一切強制移動せず、自由な移動を維持)"""
        try:
            alloc = widget.get_allocation()
            win = widget.get_window()
            if win:
                origin_x, origin_y = win.get_root_coords(alloc.x, alloc.y)
                center_x = origin_x + alloc.width // 2
                center_y = origin_y + alloc.height // 2
                return (center_x, center_y)
        except Exception:
            pass
        return (int(event.x_root), int(event.y_root))

    def on_cell_enter(self, widget, event, info):
        """キーにポインタが乗った時のホバー演出 (文字送信はクリック/リリース時のみ安全に実行)"""
        widget.get_style_context().add_class("key-hovered")
        self.hover_cell_widget = widget
        return False

    def on_cell_leave(self, widget, event, info):
        """キーから離脱した時の処理"""
        widget.get_style_context().remove_class("key-hovered")
        return False

    def create_cell_widget(self, info):
        box = Gtk.EventBox()
        box.set_visible_window(True)
        box.add_events(
            Gdk.EventMask.POINTER_MOTION_MASK
            | Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.ENTER_NOTIFY_MASK
            | Gdk.EventMask.LEAVE_NOTIFY_MASK
            | Gdk.EventMask.TOUCH_MASK
        )

        box.connect("enter-notify-event", self.on_cell_enter, info)
        box.connect("leave-notify-event", self.on_cell_leave, info)
        box.connect("button-press-event", self.on_cell_press, info)
        box.connect("motion-notify-event", self.on_cell_motion, info)
        box.connect("button-release-event", self.on_cell_release, info)
        box.connect("touch-event", self.on_cell_touch, info)

        lbl = Gtk.Label()
        lbl.set_use_markup(True)

        if info["type"] == "flick":
            box.get_style_context().add_class("key-cell")
            key_name = info["key"]
            flick_data = info.get("flick_data", KANA_FLICKS.get(key_name, {'center': key_name}))
            center_char = flick_data.get('center', key_name) if flick_data else key_name
            if info.get("num"):
                num = info["num"]
                lbl.set_markup(f"<span size='8500' color='#8ab4f8'>{num}</span> <span size='14000' weight='bold' color='#ffffff'>{center_char}</span>")
            else:
                lbl.set_markup(f"<span size='15000' weight='bold' color='#ffffff'>{center_char}</span>")
        else:
            style = info.get("style", "action-cell")
            box.get_style_context().add_class(style)
            label = info.get("label", "")
            action = info.get("action", "")

            # Highlight latched modifiers
            if action == "shift" and self.is_shift_latched:
                box.get_style_context().add_class("latched-cell")
            elif action == "ctrl" and self.is_ctrl_latched:
                box.get_style_context().add_class("latched-cell")

            color = "#202124" if ("enter" in style or (action == "shift" and self.is_shift_latched) or (action == "ctrl" and self.is_ctrl_latched)) else "#e8eaed"
            font_size = "11000" if len(label) > 2 else "13000"
            lbl.set_markup(f"<span size='{font_size}' weight='bold' color='{color}'>{label}</span>")

        box.add(lbl)
        return box

    def _calc_guide_center(self, widget):
        alloc = widget.get_allocation()
        coords = widget.translate_coordinates(self.flick_guide, alloc.width // 2, alloc.height // 2)
        if coords is not None:
            return coords[0], coords[1]
        coords = widget.translate_coordinates(self.overlay, alloc.width // 2, alloc.height // 2)
        if coords is not None:
            return coords[0], coords[1]
        return alloc.x + alloc.width // 2, alloc.y + alloc.height // 2

    def on_cell_touch(self, widget, event, info):
        touch_type = event.touch.type
        event_time = getattr(event, 'time', 0)
        if touch_type == Gdk.EventType.TOUCH_BEGIN:
            class FakePressEvent:
                button = 1
                x_root = event.touch.x_root
                y_root = event.touch.y_root
                time = event_time
            self.on_cell_press(widget, FakePressEvent(), info)
            return True
        elif touch_type == Gdk.EventType.TOUCH_UPDATE:
            class FakeMotionEvent:
                x_root = event.touch.x_root
                y_root = event.touch.y_root
                time = event_time
            self.on_cell_motion(widget, FakeMotionEvent(), info)
            return True
        elif touch_type in (Gdk.EventType.TOUCH_END, Gdk.EventType.TOUCH_CANCEL):
            class FakeReleaseEvent:
                button = 1
                time = event_time
            self.on_cell_release(widget, FakeReleaseEvent(), info)
            return True
        return False

    def on_cell_press(self, widget, event, info):
        if event.button not in (1, 3):
            return True

        self._cancel_hover_timer()
        center_coords = self.snap_pointer_to_cell_center(widget, event)
        self.drag_start = center_coords
        self.active_cell = info
        self.press_button = event.button
        self.current_dir = 'center'
        widget.get_style_context().add_class("key-pressed")

        if info["type"] == "flick":
            key_name = info["key"]
            flick_data = info.get("flick_data", KANA_FLICKS.get(key_name, {'center': key_name}))
            cx, cy = self._calc_guide_center(widget)
            self.flick_guide.show_guide(cx, cy, flick_data, 'center')

        return True

    def on_cell_motion(self, widget, event, info):
        if not self.drag_start or not self.active_cell:
            return True

        dx = event.x_root - self.drag_start[0]
        dy = event.y_root - self.drag_start[1]
        dist = math.hypot(dx, dy)

        threshold = 18  # 18px detent threshold
        if dist > threshold:
            angle = math.degrees(math.atan2(dy, dx))
            if -45 <= angle <= 45:
                direction = 'right'
            elif 45 < angle <= 135:
                direction = 'down'
            elif -135 <= angle < -45:
                direction = 'up'
            else:
                direction = 'left'
        else:
            direction = 'center'

        if direction != self.current_dir:
            self.current_dir = direction
            if info["type"] == "flick":
                key_name = info["key"]
                flick_data = info.get("flick_data", KANA_FLICKS.get(key_name, {'center': key_name}))
                cx, cy = self._calc_guide_center(widget)
                self.flick_guide.show_guide(cx, cy, flick_data, direction)

                target_char = flick_data.get(direction, '') if flick_data else key_name
                if target_char:
                    self.preedit_text = target_char
                    self.update_display_bar()
                    self.update_prediction_strip(target_char)

        return True

    def on_cell_release(self, widget, event, info):
        widget.get_style_context().remove_class("key-pressed")
        self.flick_guide.hide_guide()

        if not self.drag_start:
            return True

        button = self.press_button
        flick_dir = self.current_dir

        if info["type"] == "flick":
            key_name = info["key"]
            flick_data = info.get("flick_data", KANA_FLICKS.get(key_name, {'center': key_name}))

            if button != 1:
                self.commit_toggle()
            else:
                if flick_dir != 'center':
                    self.commit_toggle()
                    char = flick_data.get(flick_dir, '') if flick_data else ''
                    if char:
                        self.type_char(char)
                        self.committed_text += char
                        self.preedit_text = ""
                        self.hover_tentative_char = ""
                        self.last_char = char
                        self.update_display_bar()
                        self.update_prediction_strip(char)
                else:
                    self.handle_flick_tap(key_name, flick_data)
        else:
            self.handle_action(info.get("action"))

        self.drag_start = None
        self.active_cell = None
        self.current_dir = 'center'
        return True

    def on_numpad_event(self, r: int, c: int):
        if r < len(self.current_matrix) and c < len(self.current_matrix[r]):
            cell_info = self.current_matrix[r][c]
            if cell_info["type"] == "flick":
                key_name = cell_info["key"]
                flick_data = cell_info.get("flick_data", KANA_FLICKS.get(key_name, {'center': key_name}))
                self.handle_flick_tap(key_name, flick_data)
            else:
                self.handle_action(cell_info.get("action"))

    def _cancel_toggle_timer(self):
        if getattr(self, 'toggle_timer_id', None) is not None:
            try:
                GLib.source_remove(self.toggle_timer_id)
            except Exception:
                pass
            self.toggle_timer_id = None

    def _start_toggle_timer(self):
        self._cancel_toggle_timer()
        self.toggle_timer_id = GLib.timeout_add(self.toggle_timeout_ms, self._on_toggle_timeout)

    def _on_toggle_timeout(self):
        self.commit_toggle()
        return False

    def commit_toggle(self):
        self._cancel_toggle_timer()
        if self.preedit_text:
            self.committed_text += self.preedit_text
            self.preedit_text = ""
            self.hover_tentative_char = ""
            self.update_display_bar()
        self.toggle_key = None
        self.toggle_index = 0

    def replace_last_char(self, char):
        self.last_char = char
        XDO.replace(char)

    def handle_flick_tap(self, key_name, flick_data):
        cycle = TOGGLE_CYCLES.get(key_name)
        if cycle:
            if self.toggle_key == key_name and getattr(self, 'toggle_timer_id', None) is not None:
                self._cancel_toggle_timer()
                self.toggle_index = (self.toggle_index + 1) % len(cycle)
                char = cycle[self.toggle_index]
                self.replace_last_char(char)
                self.preedit_text = char
                self.hover_tentative_char = char
                self.update_display_bar()
                self.update_prediction_strip(char)
                self._start_toggle_timer()
                return
            else:
                self.commit_toggle()
                self.toggle_key = key_name
                self.toggle_index = 0
                char = cycle[0]
                self.type_char(char)
                self.preedit_text = char
                self.hover_tentative_char = char
                self.update_display_bar()
                self.update_prediction_strip(char)
                self._start_toggle_timer()
                return

        self.commit_toggle()
        char = flick_data.get('center', key_name) if flick_data else key_name
        self.type_char(char)
        self.committed_text += char
        self.preedit_text = ""
        self.hover_tentative_char = ""
        self.update_display_bar()
        self.update_prediction_strip(char)

    def handle_action(self, action):
        self.commit_toggle()
        if action == "backspace":
            self.last_char = ""
            XDO.key("BackSpace")
            if self.preedit_text or self.hover_tentative_char:
                self.preedit_text = ""
                self.hover_tentative_char = ""
            elif self.committed_text:
                self.committed_text = self.committed_text[:-1]
            self.update_display_bar()
            self.update_prediction_strip("")
        elif action == "undo":
            XDO.key("ctrl+z")
        elif action == "redo":
            XDO.key("ctrl+y")
        elif action == "slash":
            self.type_char("/")
        elif action == "asterisk":
            self.type_char("*")
        elif action == "minus":
            self.type_char("-")
        elif action == "plus":
            self.type_char("+")
        elif action == "double_zero":
            self.type_char("00")
        elif action == "next":
            self.commit_toggle()
            XDO.key("Right")
        elif action == "space":
            self.commit_toggle()
            self.last_char = " "
            XDO.key("space")
            self.committed_text += " "
            self.update_display_bar()
        elif action == "convert":
            self.commit_toggle()
            self.last_char = ""
            XDO.key("space")
        elif action == "enter":
            self.commit_toggle()
            self.last_char = ""
            XDO.key("Return")
            self.committed_text = ""
            self.preedit_text = ""
            self.hover_tentative_char = ""
            self.update_display_bar()
            self.update_prediction_strip("")
        elif action == "left":
            prefix = "Shift+" if self.is_shift_latched else ""
            XDO.key(f"{prefix}Left")
        elif action == "right":
            prefix = "Shift+" if self.is_shift_latched else ""
            XDO.key(f"{prefix}Right")
        elif action == "up":
            prefix = "Shift+" if self.is_shift_latched else ""
            XDO.key(f"{prefix}Up")
        elif action == "down":
            prefix = "Shift+" if self.is_shift_latched else ""
            XDO.key(f"{prefix}Down")
        elif action == "tab":
            if self.is_shift_latched:
                XDO.key("ISO_Left_Tab")
                self.is_shift_latched = False
                self.rebuild_keys()
            else:
                XDO.key("Tab")
        elif action == "shift_tab":
            XDO.key("ISO_Left_Tab")
        elif action == "shift":
            self.is_shift_latched = not self.is_shift_latched
            self.rebuild_keys()
        elif action == "ctrl":
            self.is_ctrl_latched = not self.is_ctrl_latched
            self.rebuild_keys()
        elif action == "home":
            XDO.key("Home")
        elif action == "end":
            XDO.key("End")
        elif action == "page_up":
            XDO.key("Prior")
        elif action == "page_down":
            XDO.key("Next")
        elif action == "esc":
            XDO.key("Escape")
        elif action == "delete":
            XDO.key("Delete")
        elif action == "dakuten":
            self.apply_dakuten()
        elif action == "mode":
            # Cycle modes: kana -> katakana -> alpha -> number -> nav -> kana
            modes = ["kana", "katakana", "alpha", "number", "nav"]
            curr_idx = modes.index(self.input_mode) if self.input_mode in modes else 0
            self.input_mode = modes[(curr_idx + 1) % len(modes)]
            self.save_layout(self.current_layout_name)
            self.rebuild_keys()
        elif action == "number":
            self.input_mode = "number" if self.input_mode != "number" else "kana"
            self.save_layout(self.current_layout_name)
            self.rebuild_keys()
        elif action == "alpha":
            self.input_mode = "alpha"
            self.save_layout(self.current_layout_name)
            self.rebuild_keys()
        elif action == "kana":
            self.input_mode = "kana"
            self.save_layout(self.current_layout_name)
            self.rebuild_keys()
        elif action == "symbol":
            self.input_mode = "alpha" if self.input_mode != "alpha" else "kana"
            self.save_layout(self.current_layout_name)
            self.rebuild_keys()

    def type_char(self, char):
        self.last_char = char
        XDO.type(char)

    def apply_dakuten(self):
        if not self.last_char:
            return
        toggled = DAKUTEN_MAP.get(self.last_char)
        if toggled:
            self.commit_toggle()
            self.replace_last_char(toggled)


def main():
    win = FlickTuxWindow()
    win.show_all()
    Gtk.main()


if __name__ == '__main__':
    main()
