#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
flktux.settings_gui: Wacom tablet sensitivity & Flick settings center
Includes live drawing test canvas with pressure sensitivity feedback!
"""

import os
import cairo
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk

from .wacom import WACOM, PROFILES, PRESSURE_CURVES


class PressureTestCanvas(Gtk.DrawingArea):
    """ペンの筆圧(0〜100%)に応じて線の太さが変化するリアルタイム試し書き広場"""

    def __init__(self):
        super().__init__()
        self.set_size_request(-1, 140)
        self.strokes = []  # List of lines: [[(x, y, pressure), ...], ...]
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
                pressure = max(0.1, min(1.0, p_val))
            self.current_stroke = [(event.x, event.y, pressure)]
            self.queue_draw()
        return True

    def on_motion(self, widget, event):
        if self.current_stroke:
            pressure = 0.5
            has_p, p_val = event.get_axis(Gdk.AxisUse.PRESSURE)
            if has_p:
                pressure = max(0.1, min(1.0, p_val))
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
        # Background
        cr.set_source_rgb(0.13, 0.14, 0.16)
        cr.paint()

        # Canvas Border
        cr.set_source_rgb(0.25, 0.26, 0.28)
        cr.set_line_width(1.5)
        cr.rectangle(1, 1, widget.get_allocated_width() - 2, widget.get_allocated_height() - 2)
        cr.stroke()

        # Helper text if canvas is empty
        if not self.strokes and not self.current_stroke:
            cr.set_source_rgb(0.45, 0.48, 0.52)
            cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
            cr.set_font_size(12)
            cr.move_to(20, 75)
            cr.show_text("🖊️ ここにペンで自由に描いて、筆圧と線のなめらかさを試せます")

        # Draw strokes with variable thickness based on pressure
        all_strokes = list(self.strokes)
        if self.current_stroke:
            all_strokes.append(self.current_stroke)

        cr.set_source_rgb(0.54, 0.71, 0.97) # Light blue (#8ab4f8)
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
                line_w = max(1.5, avg_p * 14.0)

                cr.set_line_width(line_w)
                cr.move_to(x1, y1)
                cr.line_to(x2, y2)
                cr.stroke()

        return False


class SettingsDialog(Gtk.Window):
    """FlickTux & Wacom Tablet Settings Center"""

    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_title("FlickTux - ペンタブ感度・お絵描き調整設定")
        self.set_default_size(520, 620)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_border_width(12)

        # Set window icon
        for icon_path in [
            "/opt/flicktux/assets/icon.png",
            "/usr/share/pixmaps/flicktux.png",
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "icon.png"),
        ]:
            if os.path.exists(icon_path):
                try:
                    self.set_icon_from_file(icon_path)
                    break
                except Exception:
                    pass

        self.cfg = WACOM.load_settings()

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(main_box)

        # 1. Title & Profile Quick Switch
        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        title_lbl = Gtk.Label()
        title_lbl.set_markup("<span size='14000' weight='bold' color='#8ab4f8'>🎨 ペンタブ感度 ＆ プロファイル設定</span>")
        title_box.pack_start(title_lbl, False, False, 0)
        main_box.pack_start(title_box, False, False, 0)

        prof_frame = Gtk.Frame(label="ワンクリック・プリセット")
        prof_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        prof_box.set_border_width(8)

        btn_art = Gtk.Button(label="🎨 イラスト・お絵描き")
        btn_art.connect("clicked", lambda w: self.apply_preset("art"))
        prof_box.pack_start(btn_art, True, True, 0)

        btn_fast = Gtk.Button(label="⚡ 超機敏・快速")
        btn_fast.connect("clicked", lambda w: self.apply_preset("fast"))
        prof_box.pack_start(btn_fast, True, True, 0)

        btn_std = Gtk.Button(label="⚖️ 標準")
        btn_std.connect("clicked", lambda w: self.apply_preset("standard"))
        prof_box.pack_start(btn_std, True, True, 0)

        prof_frame.add(prof_box)
        main_box.pack_start(prof_frame, False, False, 0)

        # 2. Detailed Sliders Frame
        sliders_frame = Gtk.Frame(label="詳細パラメーター微調整")
        sliders_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        sliders_box.set_border_width(8)

        # Pressure Curve (1: Soft -> 5: Hard)
        p_val = self.cfg.get("pressure_curve_level", 3)
        self.p_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 5, 1)
        self.p_scale.set_value(p_val)
        self.p_scale.set_digits(0)
        self.p_scale.add_mark(1, Gtk.PositionType.BOTTOM, "超柔")
        self.p_scale.add_mark(3, Gtk.PositionType.BOTTOM, "標準")
        self.p_scale.add_mark(5, Gtk.PositionType.BOTTOM, "硬め")
        self.p_scale.connect("value-changed", self.on_change)
        sliders_box.pack_start(self._make_row("筆圧の硬さ (軽い力で強弱 ←→ 力強く描く):", self.p_scale), False, False, 0)

        # Smoothing / RawSample (1: Instant -> 10: Smooth)
        raw_val = self.cfg.get("raw_sample", 4)
        self.raw_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 10, 1)
        self.raw_scale.set_value(raw_val)
        self.raw_scale.set_digits(0)
        self.raw_scale.add_mark(1, Gtk.PositionType.BOTTOM, "遅延ゼロ")
        self.raw_scale.add_mark(6, Gtk.PositionType.BOTTOM, "なめらか")
        self.raw_scale.add_mark(10, Gtk.PositionType.BOTTOM, "強補正")
        self.raw_scale.connect("value-changed", self.on_change)
        sliders_box.pack_start(self._make_row("ペンの追従性・手ブレ補正 (最速 ←→ 線画安定):", self.raw_scale), False, False, 0)

        # Click Threshold (8 to 50)
        th_val = self.cfg.get("threshold", 20)
        self.th_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 8, 50, 1)
        self.th_scale.set_value(th_val)
        self.th_scale.set_digits(0)
        self.th_scale.connect("value-changed", self.on_change)
        sliders_box.pack_start(self._make_row("クリック感度 (羽タッチ ←→ 押し込み):", self.th_scale), False, False, 0)

        # 16:9 Aspect Ratio Preservation Toggle
        asp_val = self.cfg.get("aspect_ratio_16_9", False)
        self.asp_switch = Gtk.Switch()
        self.asp_switch.set_active(asp_val)
        self.asp_switch.connect("notify::active", self.on_change)
        sliders_box.pack_start(self._make_row("16:9 画面比率維持 (正円を描いたときに歪まない):", self.asp_switch), False, False, 0)

        # Touchpad Pointer Speed (1.0 to 2.5)
        spd_val = self.cfg.get("pointer_speed", 1.4)
        self.spd_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1.0, 2.5, 0.1)
        self.spd_scale.set_value(spd_val)
        self.spd_scale.set_digits(1)
        self.spd_scale.connect("value-changed", self.on_change)
        sliders_box.pack_start(self._make_row("指トラックパッド移動速度:", self.spd_scale), False, False, 0)

        # Touchpad Enable Switch
        touch_val = self.cfg.get("touch_enabled", True)
        self.touch_switch = Gtk.Switch()
        self.touch_switch.set_active(touch_val)
        self.touch_switch.connect("notify::active", self.on_change)
        sliders_box.pack_start(self._make_row("指タッチ機能 (イラスト中OFFで手のひら誤爆防止):", self.touch_switch), False, False, 0)

        sliders_frame.add(sliders_box)
        main_box.pack_start(sliders_frame, False, False, 0)

        # 3. Live Pressure Test Canvas
        test_frame = Gtk.Frame(label="🖊️ リアルタイム筆圧・試し書きテスト広場")
        test_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        test_box.set_border_width(6)

        self.canvas = PressureTestCanvas()
        test_box.pack_start(self.canvas, True, True, 0)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        clear_btn = Gtk.Button(label="キャンバスをクリア")
        clear_btn.connect("clicked", lambda w: self.canvas.clear())
        btn_box.pack_end(clear_btn, False, False, 0)
        test_box.pack_start(btn_box, False, False, 0)

        test_frame.add(test_box)
        main_box.pack_start(test_frame, True, True, 0)

        self.show_all()

    def _make_row(self, title: str, widget: Gtk.Widget) -> Gtk.Box:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        lbl = Gtk.Label(label=title)
        lbl.set_xalign(0.0)
        row.pack_start(lbl, True, True, 0)
        row.pack_end(widget, False, False, 0)
        return row

    def apply_preset(self, preset_key: str):
        if preset_key in PROFILES:
            p = PROFILES[preset_key]
            self.p_scale.set_value(p["pressure_curve_level"])
            self.raw_scale.set_value(p["raw_sample"])
            self.th_scale.set_value(p["threshold"])
            self.asp_switch.set_active(p["aspect_ratio_16_9"])
            self.spd_scale.set_value(p["pointer_speed"])
            self.touch_switch.set_active(p["touch_enabled"])
            self.on_change(None)

    def on_change(self, widget, *args):
        p_lvl = int(self.p_scale.get_value())
        curve = PRESSURE_CURVES.get(p_lvl, "0 0 100 100")
        raw = int(self.raw_scale.get_value())
        th = int(self.th_scale.get_value())
        asp = self.asp_switch.get_active()
        spd = float(self.spd_scale.get_value())
        touch = self.touch_switch.get_active()

        self.cfg["pressure_curve_level"] = p_lvl
        self.cfg["pressure_curve"] = curve
        self.cfg["raw_sample"] = raw
        self.cfg["threshold"] = th
        self.cfg["aspect_ratio_16_9"] = asp
        self.cfg["pointer_speed"] = spd
        self.cfg["touch_enabled"] = touch

        # Live apply & persist
        WACOM.apply_settings(self.cfg)
        WACOM.save_settings(self.cfg)


def main():
    win = SettingsDialog()
    win.connect("destroy", Gtk.main_quit)
    Gtk.main()


if __name__ == '__main__':
    main()
