#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
flktux.settings_gui: Complete Wacom sensitivity, custom profiles, and keymap center
Features:
- Live drawing test canvas with pressure sensitivity feedback
- Granular sliders: Pressure curve, Threshold, RawSample, Suppress, AspectRatio, Speed
- Custom user profile creation and saving (named profiles)
- Keymap assignment tab for Stylus buttons and ExpressKeys
"""

import os
import json
import cairo
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk

from .wacom import WACOM, PROFILES, PRESSURE_CURVES
from .keymap import KEYMAP, BUTTON_ACTIONS


class PressureTestCanvas(Gtk.DrawingArea):
    """ペンの筆圧(0〜100%)に応じて線の太さが変化するリアルタイム試し書き広場"""

    def __init__(self):
        super().__init__()
        self.set_size_request(-1, 140)
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
            cr.move_to(20, 75)
            cr.show_text("🖊️ ペンで自由に線を描いて、筆圧となめらかさを試せます")

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
    """FlickTux & Wacom Tablet Detailed Settings Center"""

    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_title("FlickTux - ペンタブ感度・プロファイル ＆ キーマップ設定")
        self.set_default_size(580, 680)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_border_width(12)

        # Load configurations
        self.cfg = WACOM.load_settings()
        self.keymap_cfg = KEYMAP.load_keymap()

        notebook = Gtk.Notebook()
        self.add(notebook)

        # Tab 1: Sensitivity & Profiles
        tab1_box = self._create_sensitivity_tab()
        notebook.append_page(tab1_box, Gtk.Label(label="🎨 筆圧・感度プロファイル"))

        # Tab 2: Keymap Customization
        tab2_box = self._create_keymap_tab()
        notebook.append_page(tab2_box, Gtk.Label(label="🎮 キーマップ・ボタン設定"))

    def _create_sensitivity_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(8)

        # Quick Presets Bar
        preset_frame = Gtk.Frame(label="プリセット切替")
        preset_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        preset_box.set_border_width(6)

        btn_art = Gtk.Button(label="🎨 イラスト")
        btn_art.connect("clicked", lambda w: self._apply_preset("art"))
        btn_fast = Gtk.Button(label="⚡ 快速")
        btn_fast.connect("clicked", lambda w: self._apply_preset("fast"))
        btn_std = Gtk.Button(label="⚖️ 標準")
        btn_std.connect("clicked", lambda w: self._apply_preset("standard"))

        preset_box.pack_start(btn_art, True, True, 0)
        preset_box.pack_start(btn_fast, True, True, 0)
        preset_box.pack_start(btn_std, True, True, 0)
        preset_frame.add(preset_box)
        box.pack_start(preset_frame, False, False, 0)

        # Detailed Sliders Frame
        sliders_frame = Gtk.Frame(label="筆圧・感度詳細調整")
        s_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        s_box.set_border_width(8)

        # 1. Pressure Curve
        row1, self.curve_scale = self._create_slider(
            "筆圧の硬さ (1:超軟 〜 5:硬)", 1, 5, 1,
            self.cfg.get("pressure_curve_level", 3),
            self.on_param_changed
        )
        s_box.pack_start(row1, False, False, 0)

        # 2. Threshold
        row2, self.thresh_scale = self._create_slider(
            "最小反応しきい値 (0:羽毛タッチ 〜 100:強め)", 0, 100, 2,
            self.cfg.get("threshold", 12),
            self.on_param_changed
        )
        s_box.pack_start(row2, False, False, 0)

        # 3. RawSample
        row3, self.raw_scale = self._create_slider(
            "手ブレ補正 (1:遅延ゼロ 〜 20:なめらか)", 1, 20, 1,
            self.cfg.get("raw_sample", 6),
            self.on_param_changed
        )
        s_box.pack_start(row3, False, False, 0)

        # 4. Suppress
        row4, self.sup_scale = self._create_slider(
            "微小ブレ抑制 (0:検知即座 〜 10:安定)", 0, 10, 1,
            self.cfg.get("suppress", 2),
            self.on_param_changed
        )
        s_box.pack_start(row4, False, False, 0)

        # 5. Aspect Ratio & Speed
        row5 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.aspect_chk = Gtk.CheckButton(label="16:9 正円比率補正 (真円が楕円に歪まない)")
        self.aspect_chk.set_active(self.cfg.get("aspect_ratio_16_9", True))
        self.aspect_chk.connect("toggled", self.on_param_changed)
        row5.pack_start(self.aspect_chk, False, False, 0)
        s_box.pack_start(row5, False, False, 0)

        row6, self.speed_scale = self._create_slider(
            "トラックパッド移動速度", 0.5, 3.0, 0.1,
            self.cfg.get("pointer_speed", 1.4),
            self.on_param_changed
        )
        s_box.pack_start(row6, False, False, 0)

        sliders_frame.add(s_box)
        box.pack_start(sliders_frame, False, False, 0)

        # Live Canvas
        canvas_frame = Gtk.Frame(label="🖊️ 試し書きテスト広場")
        c_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        c_box.set_border_width(4)
        self.canvas = PressureTestCanvas()
        c_box.pack_start(self.canvas, True, True, 0)

        btn_clear = Gtk.Button(label="キャンバスを消去")
        btn_clear.connect("clicked", lambda w: self.canvas.clear())
        c_box.pack_start(btn_clear, False, False, 0)

        canvas_frame.add(c_box)
        box.pack_start(canvas_frame, True, True, 0)

        return box

    def _create_keymap_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(8)

        # Stylus buttons
        stylus_frame = Gtk.Frame(label="🖊️ ペン（スタイラス）ボタン設定")
        stylus_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        stylus_box.set_border_width(8)

        self.combo_b3 = self._create_combo_row(stylus_box, "ペン上ボタン (Button 3):",
                                               self.keymap_cfg.get("stylus", {}).get("button3", "flick_toggle"))
        self.combo_b2 = self._create_combo_row(stylus_box, "ペン下ボタン (Button 2):",
                                               self.keymap_cfg.get("stylus", {}).get("button2", "right_click"))

        stylus_frame.add(stylus_box)
        box.pack_start(stylus_frame, False, False, 0)

        # ExpressKeys
        pad_frame = Gtk.Frame(label="🖐️ タブレット本体ボタン（エクスプレスキー）")
        pad_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        pad_box.set_border_width(8)

        pad_cfg = self.keymap_cfg.get("pad", {})
        self.combo_k1 = self._create_combo_row(pad_box, "上ボタン①:", pad_cfg.get("key1", "undo"))
        self.combo_k2 = self._create_combo_row(pad_box, "2段目ボタン②:", pad_cfg.get("key2", "redo"))
        self.combo_k3 = self._create_combo_row(pad_box, "3段目ボタン③:", pad_cfg.get("key3", "flick_toggle"))
        self.combo_k4 = self._create_combo_row(pad_box, "下ボタン④:", pad_cfg.get("key4", "hand"))

        pad_frame.add(pad_box)
        box.pack_start(pad_frame, False, False, 0)

        # Save Button
        btn_save = Gtk.Button(label="💾 キーマップ設定を保存して今すぐ適用")
        btn_save.connect("clicked", self.on_save_keymap)
        box.pack_end(btn_save, False, False, 4)

        return box

    def _create_slider(self, label_text, min_val, max_val, step, cur_val, cb):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl = Gtk.Label(label=label_text)
        lbl.set_size_request(240, -1)
        lbl.set_xalign(0.0)
        scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, min_val, max_val, step)
        scale.set_value(cur_val)
        scale.set_hexpand(True)
        scale.connect("value-changed", cb)
        row.pack_start(lbl, False, False, 0)
        row.pack_start(scale, True, True, 0)
        return row, scale

    def _create_combo_row(self, parent_box, label_text, cur_action):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl = Gtk.Label(label=label_text)
        lbl.set_size_request(180, -1)
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
            self.sup_scale.set_value(p.get("suppress", 2))
            self.aspect_chk.set_active(p.get("aspect_ratio_16_9", True))
            self.speed_scale.set_value(p.get("pointer_speed", 1.4))

    def on_param_changed(self, widget):
        curve_lvl = int(self.curve_scale.get_value())
        self.cfg["pressure_curve_level"] = curve_lvl
        self.cfg["pressure_curve"] = PRESSURE_CURVES.get(curve_lvl, "0 0 100 100")
        self.cfg["threshold"] = int(self.thresh_scale.get_value())
        self.cfg["raw_sample"] = int(self.raw_scale.get_value())
        self.cfg["suppress"] = int(self.sup_scale.get_value())
        self.cfg["aspect_ratio_16_9"] = self.aspect_chk.get_active()
        self.cfg["pointer_speed"] = round(self.speed_scale.get_value(), 2)

        WACOM.apply_settings(self.cfg)
        WACOM.save_settings(self.cfg)

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


def main():
    win = SettingsDialog()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()


if __name__ == '__main__':
    main()
