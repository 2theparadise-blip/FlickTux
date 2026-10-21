#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
flktux.settings_gui: Multi-Device Settings Center
Supports:
1. 🖊️ 液タブ・ペンタブ (Wacom, XP-Pen, Huion, Gaomon, Xencelabs, UGEE)
   - Multi-vendor device selector, pressure curve slider, 16:9 aspect ratio, live drawing test canvas
2. 🔌 外部10キー・自作機 (Arduino, Raspberry Pi Pico, Teensy, QMK, USB numpads)
   - Device search engine, exclusive grab (EVIOCGRAB), live key-light-up test monitor
3. 📱 iPad / iPad mini (Weylus)
   - Weylus status, IP & URL connection info, 4:3 aspect ratio correction, Apple Pencil palm rejection
4. 🎮 ペン・本体ボタン割当 (ExpressKeys & Stylus buttons)
"""

import os
import sys
PKG_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PKG_ROOT not in sys.path:
    sys.path.insert(0, PKG_ROOT)

import json
import socket
import subprocess
import cairo
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib

try:
    from .tablet import TABLET, PROFILES, PRESSURE_CURVES
    from .wacom import WACOM
    from .keymap import KEYMAP, BUTTON_ACTIONS
    from .device_scanner import scan_devices, KeypadSniffer
except (ImportError, ValueError):
    from flktux.tablet import TABLET, PROFILES, PRESSURE_CURVES
    from flktux.wacom import WACOM
    from flktux.keymap import KEYMAP, BUTTON_ACTIONS
    from flktux.device_scanner import scan_devices, KeypadSniffer

CONFIG_DIR = os.path.expanduser("~/.config/flktux")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")


def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class PressureTestCanvas(Gtk.DrawingArea):
    """ペンの筆圧(0〜100%)に応じて線の太さが変化するリアルタイム試し書き広場"""

    def __init__(self):
        super().__init__()
        self.set_size_request(-1, 130)
        self.strokes = []
        self.current_stroke = []

        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK
        )

        self.connect("draw", self.on_draw)
        self.connect("button-press-event", self.on_press)
        self.connect("button-release-event", self.on_release)
        self.connect("motion-notify-event", self.on_motion)

    def clear(self):
        self.strokes = []
        self.current_stroke = []
        self.queue_draw()

    def on_press(self, widget, event):
        if event.button == 1:
            pressure = 0.5
            has_p, p_val = event.get_axis(Gdk.AxisUse.PRESSURE)
            if has_p:
                pressure = max(0.05, min(1.0, p_val))
            self.current_stroke = [(event.x, event.y, pressure)]
            self.queue_draw()
        return True

    def on_motion(self, widget, event):
        if self.current_stroke:
            pressure = 0.5
            has_p, p_val = event.get_axis(Gdk.AxisUse.PRESSURE)
            if has_p:
                pressure = max(0.05, min(1.0, p_val))
            self.current_stroke.append((event.x, event.y, pressure))
            self.queue_draw()
        return True

    def on_release(self, widget, event):
        if event.button == 1 and self.current_stroke:
            self.strokes.append(self.current_stroke)
            self.current_stroke = []
            self.queue_draw()
        return True

    def on_draw(self, widget, cr):
        cr.set_source_rgb(0.12, 0.13, 0.15)
        cr.paint()

        cr.set_source_rgb(0.25, 0.28, 0.32)
        cr.set_line_width(1.5)
        cr.rectangle(1, 1, widget.get_allocated_width() - 2, widget.get_allocated_height() - 2)
        cr.stroke()

        if not self.strokes and not self.current_stroke:
            cr.set_source_rgb(0.48, 0.52, 0.58)
            cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
            cr.set_font_size(12)
            cr.move_to(20, 70)
            cr.show_text("🖊️ ペンで自由に線を描いて、筆圧となめらかさを試せます (Wacom / XP-Pen / Huion / iPad)")

        all_strokes = list(self.strokes)
        if self.current_stroke:
            all_strokes.append(self.current_stroke)

        cr.set_source_rgb(0.54, 0.71, 0.97)  # #8ab4f8
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)

        for stroke in all_strokes:
            if len(stroke) < 2:
                if len(stroke) == 1:
                    x, y, p = stroke[0]
                    r = max(2.0, p * 8.0)
                    cr.arc(x, y, r, 0, 6.28)
                    cr.fill()
                continue

            for i in range(len(stroke) - 1):
                x1, y1, p1 = stroke[i]
                x2, y2, p2 = stroke[i + 1]
                avg_p = (p1 + p2) / 2.0
                line_w = max(1.2, avg_p * 15.0)

                cr.set_line_width(line_w)
                cr.move_to(x1, y1)
                cr.line_to(x2, y2)
                cr.stroke()

        return False


class SettingsDialog(Gtk.Window):
    """FlickTux Multi-Device Settings Center"""

    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_title("FlickTux - マルチデバイス＆ハードウェア設定センター")
        self.set_default_size(620, 680)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_border_width(10)
        try:
            self.set_icon_name("flicktux")
        except Exception:
            pass

        # Load configurations
        self.cfg = TABLET.load_settings()
        self.keymap_cfg = KEYMAP.load_keymap()
        self.app_cfg = self._load_app_config()

        self.sniffer = None
        self.test_buttons = {}

        self.notebook = Gtk.Notebook()
        self.add(self.notebook)
        notebook = self.notebook

        # Tab 1: Tablet / Pen Display (Wacom, XP-Pen, Huion, etc.)
        notebook.append_page(self._create_tablet_tab(), Gtk.Label(label="🖊️ 液タブ・ペンタブ"))

        # Tab 2: DIY 10-Key / Arduino Keypad
        notebook.append_page(self._create_numpad_tab(), Gtk.Label(label="🔌 外部10キー・自作機"))

        # Tab 3: iPad / iPad mini (Weylus)
        notebook.append_page(self._create_weylus_tab(), Gtk.Label(label="📱 iPad (Weylus)"))

        # Tab 4: ExpressKeys & Stylus buttons
        notebook.append_page(self._create_keymap_tab(), Gtk.Label(label="🎮 ペン・ボタン割当"))

        self.connect("destroy", self._on_destroy)

    def _load_app_config(self) -> dict:
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_app_config(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.app_cfg, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ==================== Tab 1: 液タブ・ペンタブ ====================
    def _create_tablet_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(8)

        # Detected Tablet Selector
        dev_frame = Gtk.Frame(label="接続デバイス認識")
        dev_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        dev_box.set_border_width(8)

        self.tablet_combo = Gtk.ComboBoxText()
        self._populate_tablet_combo()
        dev_box.pack_start(self.tablet_combo, True, True, 0)

        btn_rescan_tab = Gtk.Button(label="🔄 再検出")
        btn_rescan_tab.connect("clicked", lambda w: self._populate_tablet_combo())
        dev_box.pack_start(btn_rescan_tab, False, False, 0)

        dev_frame.add(dev_box)
        box.pack_start(dev_frame, False, False, 0)

        # Quick Presets
        preset_frame = Gtk.Frame(label="プロファイル・プリセット")
        preset_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        preset_box.set_border_width(6)

        btn_art = Gtk.Button(label="🎨 イラスト制作")
        btn_art.connect("clicked", lambda w: self._apply_preset("art"))
        btn_fast = Gtk.Button(label="⚡ 快速デスクトップ")
        btn_fast.connect("clicked", lambda w: self._apply_preset("fast"))
        btn_std = Gtk.Button(label="⚖️ 標準バランス")
        btn_std.connect("clicked", lambda w: self._apply_preset("standard"))

        preset_box.pack_start(btn_art, True, True, 0)
        preset_box.pack_start(btn_fast, True, True, 0)
        preset_box.pack_start(btn_std, True, True, 0)
        preset_frame.add(preset_box)
        box.pack_start(preset_frame, False, False, 0)

        # Sliders
        sliders_frame = Gtk.Frame(label="筆圧・感度詳細調整")
        s_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        s_box.set_border_width(8)

        row1, self.curve_scale = self._create_slider(
            "筆圧の硬さ (1:超軟 〜 5:硬)", 1, 5, 1,
            self.cfg.get("pressure_curve_level", 3),
            self.on_param_changed
        )
        row2, self.thresh_scale = self._create_slider(
            "クリック感度 (小さいほど軽いタッチで反応)", 1, 50, 1,
            self.cfg.get("threshold", 12),
            self.on_param_changed
        )
        row3, self.raw_scale = self._create_slider(
            "手ブレ補正・スムージング (1:遅延ゼロ 〜 10:なめらか)", 1, 10, 1,
            self.cfg.get("raw_sample", 6),
            self.on_param_changed
        )
        row4, self.speed_scale = self._create_slider(
            "ポインタ移動速度倍率 (トラックパッド/マウス)", 0.5, 3.0, 0.1,
            self.cfg.get("pointer_speed", 1.2),
            self.on_param_changed
        )

        s_box.pack_start(row1, False, False, 0)
        s_box.pack_start(row2, False, False, 0)
        s_box.pack_start(row3, False, False, 0)
        s_box.pack_start(row4, False, False, 0)

        self.aspect_chk = Gtk.CheckButton(label="📐 16:9 正円アスペクト比を維持 (真円が楕円に歪まない)")
        self.aspect_chk.set_active(self.cfg.get("aspect_ratio_16_9", True))
        self.aspect_chk.connect("toggled", self.on_param_changed)
        s_box.pack_start(self.aspect_chk, False, False, 2)

        sliders_frame.add(s_box)
        box.pack_start(sliders_frame, False, False, 0)

        # Live Canvas
        canvas_frame = Gtk.Frame(label="🖊️ リアルタイム筆圧・試し書きテスト広場")
        canvas_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        canvas_box.set_border_width(6)

        self.canvas = PressureTestCanvas()
        canvas_box.pack_start(self.canvas, True, True, 0)

        btn_clear = Gtk.Button(label="🗑️ キャンバスをクリア")
        btn_clear.connect("clicked", lambda w: self.canvas.clear())
        canvas_box.pack_start(btn_clear, False, False, 0)

        canvas_frame.add(canvas_box)
        box.pack_start(canvas_frame, True, True, 0)

        return box

    def _populate_tablet_combo(self):
        self.tablet_combo.remove_all()
        devs = scan_devices()
        tablets = [d for d in devs if d.get("category") in ("tablet_stylus", "tablet_touch")]

        if not tablets:
            self.tablet_combo.append("none", "⚠️ スタイラス/液タブが検出されませんでした (自動検出中)")
            self.tablet_combo.set_active(0)
            return

        for idx, t in enumerate(tablets):
            label = f"{t['name']} ({t.get('description', '')})"
            self.tablet_combo.append(t["path"], label)
        self.tablet_combo.set_active(0)

    # ==================== Tab 2: 外部10キー・自作機 ====================
    def _create_numpad_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(10)

        desc = Gtk.Label(
            label="Arduino (Pro Micro), Raspberry Pi Pico (RP2040), Teensy, QMKキーパッドなどの\n"
                  "自作10キーデバイスやプッシュフォン型キーボードをFlickTuxに紐付けます。"
        )
        desc.set_line_wrap(True)
        box.pack_start(desc, False, False, 0)

        # Device Scanner Frame
        dev_frame = Gtk.Frame(label="自作10キー / テンキー デバイス選択")
        d_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        d_box.set_border_width(8)

        row_sel = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.numpad_combo = Gtk.ComboBoxText()
        self._populate_numpad_combo()
        row_sel.pack_start(self.numpad_combo, True, True, 0)

        btn_rescan = Gtk.Button(label="🔍 デバイス再検索")
        btn_rescan.connect("clicked", lambda w: self._populate_numpad_combo())
        row_sel.pack_start(btn_rescan, False, False, 0)
        d_box.pack_start(row_sel, False, False, 0)

        self.exclusive_chk = Gtk.CheckButton(label="🔒 排他キャプチャ (EVIOCGRAB): 他アプリへのキー漏れを防止しFlickTux専用にする")
        self.exclusive_chk.set_active(self.app_cfg.get("numpad_device", {}).get("exclusive_grab", False))
        self.exclusive_chk.connect("toggled", self._on_numpad_setting_changed)
        d_box.pack_start(self.exclusive_chk, False, False, 0)

        btn_bind = Gtk.Button(label="💾 このデバイスを FlickTux にバインドして保存")
        btn_bind.connect("clicked", self._on_bind_numpad_clicked)
        d_box.pack_start(btn_bind, False, False, 4)

        dev_frame.add(d_box)
        box.pack_start(dev_frame, False, False, 0)

        # Live Sniffer Monitor
        test_frame = Gtk.Frame(label="🔴 リアルタイム入力テストモニター (自作キーを押すと緑に点灯)")
        t_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        t_box.set_border_width(8)

        grid = Gtk.Grid()
        grid.set_row_spacing(6)
        grid.set_column_spacing(6)
        grid.set_row_homogeneous(True)
        grid.set_column_homogeneous(True)

        keys_matrix = [
            ["1", "2", "3"],
            ["4", "5", "6"],
            ["7", "8", "9"],
            ["*", "0", "#"]
        ]

        self.test_buttons = {}
        for r, row in enumerate(keys_matrix):
            for c, k in enumerate(row):
                btn = Gtk.Button(label=k)
                btn.set_sensitive(False)
                grid.attach(btn, c, r, 1, 1)
                self.test_buttons[k] = btn

        t_box.pack_start(grid, True, True, 4)

        self.sniffer_status_lbl = Gtk.Label(label="📡 選択されたデバイスからの入力を待機中...")
        t_box.pack_start(self.sniffer_status_lbl, False, False, 2)

        test_frame.add(t_box)
        box.pack_start(test_frame, True, True, 0)

        # Start sniffer on active selection
        self.numpad_combo.connect("changed", self._on_numpad_combo_changed)
        self._start_sniffer_for_current()

        return box

    def _populate_numpad_combo(self):
        self.numpad_combo.remove_all()
        devs = scan_devices()
        keypads = [d for d in devs if d.get("category") in ("diy_keypad", "standard_keyboard")]

        if not keypads:
            self.numpad_combo.append("none", "⚠️ 10キー / 自作キーパッド未接続 (PC全体で監視)")
            self.numpad_combo.set_active(0)
            return

        cur_saved = self.app_cfg.get("numpad_device", {}).get("device_path", "")
        active_idx = 0
        for idx, k in enumerate(keypads):
            label = f"{k['name']} - {k.get('description', '')}"
            self.numpad_combo.append(k["path"], label)
            if cur_saved and (k["path"] == cur_saved or k.get("real_path") == cur_saved):
                active_idx = idx

        self.numpad_combo.set_active(active_idx)

    def _on_numpad_combo_changed(self, combo):
        self._start_sniffer_for_current()

    def _start_sniffer_for_current(self):
        if self.sniffer:
            self.sniffer.stop()
            self.sniffer = None

        dev_path = self.numpad_combo.get_active_id()
        if dev_path and dev_path != "none" and os.path.exists(dev_path):
            self.sniffer_status_lbl.set_text(f"📡 監視中: {os.path.basename(dev_path)} (ボタンを押すと点灯)")
            self.sniffer = KeypadSniffer(dev_path, self._on_key_sniffed)
            self.sniffer.start()
        else:
            self.sniffer_status_lbl.set_text("⚪ デバイス未選択または監視不可")

    def _on_key_sniffed(self, key_label: str):
        GLib.idle_add(self._highlight_key_button, key_label)

    def _highlight_key_button(self, key_label: str):
        if key_label in self.test_buttons:
            btn = self.test_buttons[key_label]
            ctx = btn.get_style_context()
            btn.set_label(f"★ {key_label}")
            GLib.timeout_add(300, lambda: btn.set_label(key_label))
        return False

    def _on_numpad_setting_changed(self, chk):
        if "numpad_device" not in self.app_cfg:
            self.app_cfg["numpad_device"] = {}
        self.app_cfg["numpad_device"]["exclusive_grab"] = self.exclusive_chk.get_active()
        self._save_app_config()

    def _on_bind_numpad_clicked(self, widget):
        dev_path = self.numpad_combo.get_active_id()
        if "numpad_device" not in self.app_cfg:
            self.app_cfg["numpad_device"] = {}
        self.app_cfg["numpad_device"]["enabled"] = True
        self.app_cfg["numpad_device"]["device_path"] = dev_path
        self.app_cfg["numpad_device"]["exclusive_grab"] = self.exclusive_chk.get_active()
        self._save_app_config()

        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=f"✅ 10キーデバイスを正常にバインドしました！\nパス: {dev_path}"
        )
        dialog.run()
        dialog.destroy()

    # ==================== Tab 3: iPad / iPad mini (Weylus) ====================
    def _create_weylus_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_border_width(12)

        ip = get_local_ip()
        weylus_url = f"http://{ip}:1701"

        # Connection Card
        status_frame = Gtk.Frame(label="📱 iPad / iPad mini 液タブ化 (Weylus 連携)")
        s_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        s_box.set_border_width(10)

        # Check if Weylus virtual device or process is running
        devs = scan_devices()
        has_weylus = any("weylus" in d.get("name", "").lower() for d in devs)

        status_lbl = Gtk.Label(
            label="🟢 【接続検知】Weylus 仮想液タブ (Apple Pencil) がアクティブです！" if has_weylus else
                  "⚪ 【待機中】iPad からブラウザで下記のURLを開いてください。"
        )
        status_lbl.set_line_wrap(True)
        s_box.pack_start(status_lbl, False, False, 2)

        url_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        url_lbl = Gtk.Label(label=f"iPad 接続用 URL: <b>{weylus_url}</b>")
        url_lbl.set_use_markup(True)
        url_box.pack_start(url_lbl, True, True, 0)

        btn_copy = Gtk.Button(label="📋 URLコピー")
        btn_copy.connect("clicked", lambda w: Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).set_text(weylus_url, -1))
        url_box.pack_start(btn_copy, False, False, 0)
        s_box.pack_start(url_box, False, False, 4)

        status_frame.add(s_box)
        box.pack_start(status_frame, False, False, 0)

        # iPad Optimizations Frame
        opt_frame = Gtk.Frame(label="iPad 特有の最適化設定")
        o_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        o_box.set_border_width(10)

        self.weylus_aspect_chk = Gtk.CheckButton(label="📐 4:3 アスペクト比補正 (iPad の画面比率に合わせて正円を維持)")
        self.weylus_aspect_chk.set_active(self.app_cfg.get("weylus", {}).get("aspect_ratio_4_3", True))
        self.weylus_aspect_chk.connect("toggled", self._on_weylus_setting_changed)
        o_box.pack_start(self.weylus_aspect_chk, False, False, 0)

        self.palm_chk = Gtk.CheckButton(label="🖐️ Apple Pencil パームリジェクション (ペン接触中に手のひらタッチを完全無効化)")
        self.palm_chk.set_active(self.app_cfg.get("weylus", {}).get("palm_rejection", True))
        self.palm_chk.connect("toggled", self._on_weylus_setting_changed)
        o_box.pack_start(self.palm_chk, False, False, 0)

        row_scale = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row_scale.pack_start(Gtk.Label(label="UI 表示倍率 (iPad mini 等の小型画面用):"), False, False, 0)

        self.scale_combo = Gtk.ComboBoxText()
        scales = [("1.0", "1.0x (標準)"), ("1.25", "1.25x (iPad mini 推奨)"), ("1.5", "1.5x (拡大)"), ("1.8", "1.8x (特大)")]
        cur_scale = str(self.app_cfg.get("weylus", {}).get("ui_scale", "1.0"))
        active_s_idx = 0
        for i, (val, text) in enumerate(scales):
            self.scale_combo.append(val, text)
            if val == cur_scale:
                active_s_idx = i
        self.scale_combo.set_active(active_s_idx)
        self.scale_combo.connect("changed", self._on_weylus_setting_changed)
        row_scale.pack_start(self.scale_combo, False, False, 0)
        o_box.pack_start(row_scale, False, False, 4)

        opt_frame.add(o_box)
        box.pack_start(opt_frame, False, False, 0)

        return box

    def _on_weylus_setting_changed(self, *args):
        if "weylus" not in self.app_cfg:
            self.app_cfg["weylus"] = {}
        self.app_cfg["weylus"]["enabled"] = True
        self.app_cfg["weylus"]["aspect_ratio_4_3"] = self.weylus_aspect_chk.get_active()
        self.app_cfg["weylus"]["palm_rejection"] = self.palm_chk.get_active()
        try:
            self.app_cfg["weylus"]["ui_scale"] = float(self.scale_combo.get_active_id() or "1.0")
        except Exception:
            pass
        self._save_app_config()

    # ==================== Tab 4: キーマップ・ボタン設定 ====================
    def _create_keymap_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_border_width(10)

        stylus_frame = Gtk.Frame(label="スタイラスペン・サイドボタン")
        s_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        s_box.set_border_width(8)

        st_cfg = self.keymap_cfg.get("stylus", {})
        self.combo_b3 = self._create_action_combo("ボタン3 (上ボタン):", st_cfg.get("button3", "flick_toggle"), s_box)
        self.combo_b2 = self._create_action_combo("ボタン2 (下ボタン):", st_cfg.get("button2", "right_click"), s_box)
        stylus_frame.add(s_box)
        box.pack_start(stylus_frame, False, False, 0)

        pad_frame = Gtk.Frame(label="ペンタブ本体エクスプレスキー")
        p_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        p_box.set_border_width(8)

        p_cfg = self.keymap_cfg.get("pad", {})
        self.combo_k1 = self._create_action_combo("キー 1:", p_cfg.get("key1", "undo"), p_box)
        self.combo_k2 = self._create_action_combo("キー 2:", p_cfg.get("key2", "redo"), p_box)
        self.combo_k3 = self._create_action_combo("キー 3:", p_cfg.get("key3", "flick_toggle"), p_box)
        self.combo_k4 = self._create_action_combo("キー 4:", p_cfg.get("key4", "hand"), p_box)
        pad_frame.add(p_box)
        box.pack_start(pad_frame, False, False, 0)

        btn_save = Gtk.Button(label="💾 キーマップを保存してペンタブに適用")
        btn_save.connect("clicked", self.on_save_keymap)
        box.pack_start(btn_save, False, False, 4)

        return box

    def _create_slider(self, label_text, min_val, max_val, step, cur_val, cb):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl = Gtk.Label(label=label_text)
        lbl.set_xalign(0.0)
        adj = Gtk.Adjustment(value=cur_val, lower=min_val, upper=max_val, step_increment=step)
        scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adj)
        scale.set_digits(1 if step < 1.0 else 0)
        scale.set_value_pos(Gtk.PositionType.RIGHT)
        scale.connect("value-changed", cb)
        row.pack_start(lbl, True, True, 0)
        row.pack_start(scale, True, True, 0)
        return row, scale

    def _create_action_combo(self, label_text, cur_action, parent_box):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl = Gtk.Label(label=label_text)
        lbl.set_xalign(0.0)
        combo = Gtk.ComboBoxText()
        idx_to_select = 0
        current_idx = 0
        for act_id, act_info in BUTTON_ACTIONS.items():
            combo.append(act_id, act_info["label"])
            if act_id == cur_action:
                idx_to_select = current_idx
            current_idx += 1
        combo.set_active(idx_to_select)
        row.pack_start(lbl, False, False, 0)
        row.pack_start(combo, True, True, 0)
        parent_box.pack_start(row, False, False, 0)
        return combo

    def _apply_preset(self, preset_key):
        if preset_key in PROFILES:
            p = PROFILES[preset_key]
            self.curve_scale.set_value(p.get("pressure_curve_level", 3))
            self.thresh_scale.set_value(p.get("threshold", 12))
            self.raw_scale.set_value(p.get("raw_sample", 6))
            self.aspect_chk.set_active(p.get("aspect_ratio_16_9", True))
            self.speed_scale.set_value(p.get("pointer_speed", 1.2))

    def on_param_changed(self, widget):
        curve_lvl = int(self.curve_scale.get_value())
        self.cfg["pressure_curve_level"] = curve_lvl
        self.cfg["pressure_curve"] = PRESSURE_CURVES.get(curve_lvl, "0 0 100 100")
        self.cfg["threshold"] = int(self.thresh_scale.get_value())
        self.cfg["raw_sample"] = int(self.raw_scale.get_value())
        self.cfg["aspect_ratio_16_9"] = self.aspect_chk.get_active()
        self.cfg["pointer_speed"] = round(self.speed_scale.get_value(), 2)

        TABLET.apply_settings(self.cfg)
        TABLET.save_settings(self.cfg)

    def on_save_keymap(self, widget):
        self.keymap_cfg["stylus"] = {
            "button3": self.combo_b3.get_active_id() or "flick_toggle",
            "button2": self.combo_b2.get_active_id() or "right_click",
        }
        self.keymap_cfg["pad"] = {
            "key1": self.combo_k1.get_active_id() or "undo",
            "key2": self.combo_k2.get_active_id() or "redo",
            "key3": self.combo_k3.get_active_id() or "flick_toggle",
            "key4": self.combo_k4.get_active_id() or "hand",
        }
        KEYMAP.save_keymap(self.keymap_cfg)
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="✅ キーマップ設定を保存し、ペンタブへ即座に適用しました！"
        )
        dialog.run()
        dialog.destroy()

    def _on_destroy(self, widget):
        if self.sniffer:
            self.sniffer.stop()
            self.sniffer = None


def main():
    win = SettingsDialog()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()


if __name__ == '__main__':
    main()
