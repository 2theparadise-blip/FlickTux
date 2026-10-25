#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
flktux.handwriting: Linuxツール再利用型 手書き入力 ＆ 手書き文字配置パッド
Features:
1. 筆圧対応 cairo 描画キャンバス (Wacom / XP-Pen / Huion / iPad / トラックパッド対応)
2. Linux標準 zinnia-recognize 連携による手書き文字認識 (漢字・かな・英数)
3. 自動クロップ透過PNG生成 ＆ Linux標準 xclip + Ctrl+V による手書き文字スタンプ配置
"""

import os
import sys
import math
import shutil
import subprocess
from typing import List, Tuple, Optional, Callable

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GLib
import cairo

from flktux.xdo import XDO


# =============================================================================
# 1. Linux zinnia-recognize / Fallback Handwriting Recognizer
# =============================================================================

class ZinniaRecognizer:
    """Linux 標準の zinnia-recognize / tegaki-zinnia-japanese と連携する認識エンジン"""

    MODEL_PATHS = [
        "/usr/share/tegaki/models/zinnia/handwriting-ja.model",
        "/usr/share/tegaki/models/zinnia/japanese-handwriting.model",
        "/usr/share/zinnia/model/tomoe/handwriting-ja.model",
        "/usr/local/share/tegaki/models/zinnia/japanese-handwriting.model",
    ]

    def __init__(self):
        self.zinnia_bin = shutil.which("zinnia") or shutil.which("zinnia-recognize")
        self.model_path = None
        for p in self.MODEL_PATHS:
            if os.path.exists(p):
                self.model_path = p
                break

    def is_available(self) -> bool:
        return self.zinnia_bin is not None and self.model_path is not None

    def recognize(self, strokes: List[List[Tuple[float, float, float]]], max_results: int = 6) -> List[str]:
        """ストローク列 (x, y, pressure) を zinnia 形式に変換して認識"""
        if not strokes:
            return []

        if not self.is_available():
            return self._fallback_recognize(strokes, max_results)

        # zinnia-recognize Sフォーマット:
        # (width, height)
        # S (x y)*
        # S (x y)*
        lines = []
        for stroke in strokes:
            pts = " ".join(f"{int(x)} {int(y)}" for x, y, _ in stroke)
            lines.append(f"S {pts}")
        input_data = "\n".join(lines) + "\n\n"

        try:
            cmd = [self.zinnia_bin, "-m", self.model_path, "-n", str(max_results)]
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, _ = proc.communicate(input=input_data, timeout=1.0)
            candidates = []
            for line in stdout.strip().splitlines():
                parts = line.split("\t")
                if parts and parts[0]:
                    candidates.append(parts[0])
            return candidates[:max_results]
        except Exception as e:
            print(f"[flktux.handwriting] Zinnia recognition error: {e}", file=sys.stderr)
            return self._fallback_recognize(strokes, max_results)

    def _fallback_recognize(self, strokes: List[List[Tuple[float, float, float]]], max_results: int = 6) -> List[str]:
        """zinnia 未導入環境向けの軽量幾何ストローク認識 (数字・記号・基本字形)"""
        if not strokes:
            return []

        stroke_count = len(strokes)
        total_len = 0.0
        for s in strokes:
            for i in range(len(s) - 1):
                dx = s[i + 1][0] - s[i][0]
                dy = s[i + 1][1] - s[i][1]
                total_len += math.hypot(dx, dy)

        # 1画の場合の幾何判定
        if stroke_count == 1:
            s = strokes[0]
            start_x, start_y = s[0][0], s[0][1]
            end_x, end_y = s[-1][0], s[-1][1]
            dx = end_x - start_x
            dy = end_y - start_y
            dist = math.hypot(dx, dy)

            # 円弧 (始点と終点が近い) ➔ 0, o, O
            if dist < 30 and total_len > 80:
                return ["0", "o", "O", "〇", "○"][:max_results]
            # 縦線 ➔ 1, |, l, I
            elif abs(dy) > abs(dx) * 2 and dy > 20:
                return ["1", "|", "l", "I", "一"][:max_results]
            # 横線 ➔ 一, -, ~
            elif abs(dx) > abs(dy) * 2 and dx > 20:
                return ["一", "-", "ー", "〜"][:max_results]
            # 点/チョン ➔ 、
            elif total_len < 30:
                return ["、", "。", ".", "・"][:max_results]

        # 2画の場合 ➔ 十, 二, 八, 人, etc.
        elif stroke_count == 2:
            return ["十", "二", "八", "人", "入", "ト"][:max_results]

        # 3画以上 ➔ 三, 川, 山, etc.
        elif stroke_count == 3:
            return ["三", "川", "山", "大", "小", "土"][:max_results]

        return ["※ zinnia-utils 推奨"]


# =============================================================================
# 2. Pressure-Sensitive Cairo Handwriting Canvas
# =============================================================================

class HandwritingCanvas(Gtk.DrawingArea):
    """筆圧・ストローク対応の Cairo 描画キャンバス"""

    def __init__(self, on_stroke_change: Optional[Callable[[], None]] = None):
        super().__init__()
        self.on_stroke_change = on_stroke_change

        self.strokes: List[List[Tuple[float, float, float]]] = []
        self.current_stroke: List[Tuple[float, float, float]] = []

        self.pen_color = (0.54, 0.71, 0.97)  # #8ab4f8
        self.bg_color = (0.12, 0.13, 0.15)   # #202124

        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK
        )

        self.connect("button-press-event", self._on_press)
        self.connect("motion-notify-event", self._on_motion)
        self.connect("button-release-event", self._on_release)
        self.connect("draw", self._on_draw)

    def _get_pressure(self, event) -> float:
        success, pressure = event.get_axis(Gdk.AxisUse.PRESSURE)
        if success and pressure is not None:
            return max(0.1, min(1.0, float(pressure)))
        return 0.5  # マウス等のフォールバック

    def _on_press(self, widget, event):
        if event.button == 1:
            p = self._get_pressure(event)
            self.current_stroke = [(event.x, event.y, p)]
            self.queue_draw()
        return True

    def _on_motion(self, widget, event):
        if event.state & Gdk.ModifierType.BUTTON1_MASK:
            p = self._get_pressure(event)
            self.current_stroke.append((event.x, event.y, p))
            self.queue_draw()
        return True

    def _on_release(self, widget, event):
        if event.button == 1 and self.current_stroke:
            self.strokes.append(self.current_stroke)
            self.current_stroke = []
            self.queue_draw()
            if self.on_stroke_change:
                self.on_stroke_change()
        return True

    def undo(self):
        if self.strokes:
            self.strokes.pop()
            self.queue_draw()
            if self.on_stroke_change:
                self.on_stroke_change()

    def clear(self):
        self.strokes = []
        self.current_stroke = []
        self.queue_draw()
        if self.on_stroke_change:
            self.on_stroke_change()

    def _on_draw(self, widget, cr: cairo.Context):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()

        # 背景塗りつぶし
        cr.set_source_rgb(*self.bg_color)
        cr.paint()

        # 枠線
        cr.set_source_rgb(0.24, 0.26, 0.28)
        cr.set_line_width(1.0)
        cr.rectangle(1, 1, w - 2, h - 2)
        cr.stroke()

        # 空白時のガイドメッセージ
        if not self.strokes and not self.current_stroke:
            cr.set_source_rgb(0.48, 0.52, 0.58)
            cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
            cr.set_font_size(13)
            cr.move_to(w // 2 - 120, h // 2)
            cr.show_text("✍ ペンまたはマウスで手書き入力")

        # ストローク描画
        all_strokes = list(self.strokes)
        if self.current_stroke:
            all_strokes.append(self.current_stroke)

        cr.set_source_rgb(*self.pen_color)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)

        for stroke in all_strokes:
            if len(stroke) < 2:
                if len(stroke) == 1:
                    x, y, p = stroke[0]
                    r = max(2.0, p * 7.0)
                    cr.arc(x, y, r, 0, 6.28)
                    cr.fill()
                continue

            for i in range(len(stroke) - 1):
                x1, y1, p1 = stroke[i]
                x2, y2, p2 = stroke[i + 1]
                avg_p = (p1 + p2) / 2.0
                line_w = max(1.5, avg_p * 12.0)

                cr.set_line_width(line_w)
                cr.move_to(x1, y1)
                cr.line_to(x2, y2)
                cr.stroke()

        return False

    def export_cropped_transparent_png(self, filepath: str = "/tmp/flktux_handwriting.png") -> Optional[str]:
        """描かれたストロークの最小外接矩形を計算し、余白を自動クロップした透過PNGを生成"""
        if not self.strokes:
            return None

        # 1. バウンディングボックスの計算
        min_x = float('inf')
        min_y = float('inf')
        max_x = float('-inf')
        max_y = float('-inf')

        for stroke in self.strokes:
            for x, y, _ in stroke:
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)

        padding = 12
        crop_x = max(0, min_x - padding)
        crop_y = max(0, min_y - padding)
        crop_w = int((max_x - min_x) + padding * 2)
        crop_h = int((max_y - min_y) + padding * 2)

        if crop_w <= 0 or crop_h <= 0:
            return None

        # 2. 透過 Cairo ImageSurface へのレンダリング
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, crop_w, crop_h)
        cr = cairo.Context(surface)

        # 透過背景 (クリア)
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)

        # 高品位白色ペン描画 (配置しやすい白文字)
        cr.set_source_rgba(1.0, 1.0, 1.0, 1.0)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)

        for stroke in self.strokes:
            if len(stroke) < 2:
                if len(stroke) == 1:
                    x, y, p = stroke[0]
                    r = max(2.5, p * 8.0)
                    cr.arc(x - crop_x, y - crop_y, r, 0, 6.28)
                    cr.fill()
                continue

            for i in range(len(stroke) - 1):
                x1, y1, p1 = stroke[i]
                x2, y2, p2 = stroke[i + 1]
                avg_p = (p1 + p2) / 2.0
                line_w = max(2.0, avg_p * 14.0)

                cr.set_line_width(line_w)
                cr.move_to(x1 - crop_x, y1 - crop_y)
                cr.line_to(x2 - crop_x, y2 - crop_y)
                cr.stroke()

        surface.write_to_png(filepath)
        return filepath


# =============================================================================
# 3. Handwriting Pad Composite Widget
# =============================================================================

class HandwritingPadWidget(Gtk.Box):
    """手書き認識候補バー ＋ 描画キャンバス ＋ 配置ボタンの複合ウィジェット"""

    def __init__(self, on_text_input: Callable[[str], None]):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        self.on_text_input = on_text_input
        self.recognizer = ZinniaRecognizer()

        # 1. 候補文字バー (Candidate Strip)
        self.cand_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.cand_box.get_style_context().add_class("handwriting-cand-bar")
        self.cand_scroll = Gtk.ScrolledWindow()
        self.cand_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        self.cand_scroll.set_min_content_height(34)
        self.cand_scroll.add(self.cand_box)
        self.pack_start(self.cand_scroll, False, False, 1)

        # 2. 描画キャンバス
        self.canvas = HandwritingCanvas(on_stroke_change=self._on_strokes_updated)
        self.canvas.set_size_request(320, 160)
        self.pack_start(self.canvas, True, True, 2)

        # 3. コントロールボタンバー
        btn_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)

        self.btn_paste_stamp = Gtk.Button(label="📌 手書き配置 (Ctrl+V)")
        self.btn_paste_stamp.get_style_context().add_class("stamp-btn")
        self.btn_paste_stamp.set_tooltip_text("描いた文字・サインを透過画像としてエディタやお絵描きアプリに貼り付け")
        self.btn_paste_stamp.connect("clicked", self._on_paste_stamp_clicked)
        btn_bar.pack_start(self.btn_paste_stamp, True, True, 1)

        btn_copy = Gtk.Button(label="📋")
        btn_copy.get_style_context().add_class("tool-btn")
        btn_copy.set_tooltip_text("手書き画像をクリップボードにコピー")
        btn_copy.connect("clicked", self._on_copy_clicked)
        btn_bar.pack_start(btn_copy, False, False, 1)

        btn_undo = Gtk.Button(label="↩ 1画戻す")
        btn_undo.get_style_context().add_class("tool-btn")
        btn_undo.connect("clicked", lambda w: self.canvas.undo())
        btn_bar.pack_start(btn_undo, False, False, 1)

        btn_clear = Gtk.Button(label="🧹 クリア")
        btn_clear.get_style_context().add_class("tool-btn")
        btn_clear.connect("clicked", lambda w: self.canvas.clear())
        btn_bar.pack_start(btn_clear, False, False, 1)

        self.pack_start(btn_bar, False, False, 2)

        self._update_candidate_buttons([])

    def _on_strokes_updated(self):
        """ストロークが更新されたら手書き文字認識を実行して候補を更新"""
        if not self.canvas.strokes:
            self._update_candidate_buttons([])
            return

        candidates = self.recognizer.recognize(self.canvas.strokes, max_results=7)
        self._update_candidate_buttons(candidates)

    def _update_candidate_buttons(self, candidates: List[str]):
        """候補バーのボタンを更新"""
        for child in self.cand_box.get_children():
            self.cand_box.remove(child)

        if not candidates:
            lbl = Gtk.Label(label="候補: (文字を書くとここに認識結果が表示されます)")
            lbl.get_style_context().add_class("cand-hint-label")
            self.cand_box.pack_start(lbl, False, False, 6)
        else:
            for cand in candidates:
                btn = Gtk.Button(label=cand)
                btn.get_style_context().add_class("cand-btn")
                btn.connect("clicked", self._on_candidate_clicked, cand)
                self.cand_box.pack_start(btn, False, False, 2)

        self.cand_box.show_all()

    def _on_candidate_clicked(self, btn, text: str):
        """候補文字をタップしてエディタに文字コードとして入力"""
        if self.on_text_input:
            self.on_text_input(text)
        self.canvas.clear()

    def _copy_stamp_to_clipboard(self) -> bool:
        """手書き画像を生成して xclip でクリップボードに格納"""
        png_path = self.canvas.export_cropped_transparent_png()
        if not png_path or not os.path.exists(png_path):
            return False

        if shutil.which("xclip"):
            try:
                subprocess.run(
                    ["xclip", "-selection", "clipboard", "-t", "image/png", "-i", png_path],
                    check=True,
                    timeout=1.0
                )
                return True
            except Exception as e:
                print(f"[flktux.handwriting] xclip error: {e}", file=sys.stderr)
        return False

    def _on_copy_clicked(self, btn):
        self._copy_stamp_to_clipboard()

    def _on_paste_stamp_clicked(self, btn):
        """手書き画像をクリップボードにコピーし、アクティブウィンドウへ Ctrl+V を送信"""
        if self._copy_stamp_to_clipboard():
            # 少し待ってから Ctrl+V を送信 (不可分)
            GLib.timeout_add(80, lambda: (XDO.key("ctrl+v"), False)[1])
