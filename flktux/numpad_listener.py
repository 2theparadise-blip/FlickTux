#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
flktux.numpad_listener: Physical 10-key (NumPad) hardware integration
Listens for PC numpad / external Bluetooth/USB numpad keys and maps to
FlickTux 10-key toggle input based on current mode (Kana, Katakana, Alpha, Numbers).
"""

import sys
import threading
from typing import Callable, Optional
from gi.repository import GLib

# Physical KeyPad symbol names to 10-key grid positions (row, col)
# Matches 7, 8, 9 / 4, 5, 6 / 1, 2, 3 / 0
NUMPAD_GRID_MAP = {
    "KP_Divide":   (0, 0),  # Row 0, Col 0: / (記号)
    "KP_7":        (1, 0),  # Row 1, Col 0: 7 (あ / ア / abc / 7)
    "KP_8":        (1, 1),  # Row 1, Col 1: 8 (か / カ / def / 8)
    "KP_9":        (1, 2),  # Row 1, Col 2: 9 (さ / サ / ghi / 9)
    "KP_Subtract": (1, 3),  # Row 1, Col 3: - (空白)

    "KP_4":        (2, 0),  # Row 2, Col 0: 4 (た / タ / jkl / 4)
    "KP_5":        (2, 1),  # Row 2, Col 1: 5 (な / ナ / mno / 5)
    "KP_6":        (2, 2),  # Row 2, Col 2: 6 (は / ハ / pqrs / 6)
    # Row 2, Col 3: 変換

    "KP_1":        (3, 0),  # Row 3, Col 0: 1 (ま / マ / tuv / 1)
    "KP_2":        (3, 1),  # Row 3, Col 1: 2 (や / ヤ / wxyz / 2)
    "KP_3":        (3, 2),  # Row 3, Col 2: 3 (ら / ラ / @._/ / 3)
    "KP_Add":      (3, 3),  # Row 3, Col 3: + (次へ)

    "KP_0":        (4, 0),  # Row 4, Col 0: 0 (わ / ワ / ␣ / 0)
    "KP_Decimal":  (4, 1),  # Row 4, Col 1: . (、。 / .,?! / .)
    "KP_Multiply": (4, 2),  # Row 4, Col 2: * (切替 / ゛゜小 / a/A)
    "KP_Enter":    (4, 3),  # Row 4, Col 3: Enter (確定)

    "KP_Delete":   (0, 3),  # Backspace (消去)
    "BackSpace":   (0, 3),
}


class NumpadListener:
    """X11 バックグラウンドリスナー: 物理テンキーの入力を検知し、
    フォーカスに関わらず FlickTux のガラケー打ちトグルを実行"""

    def __init__(self, callback: Callable[[int, int], None]):
        self.callback = callback
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.d = None
        self.root = None
        self.grabbed_keycodes = {}

    def start(self):
        try:
            from Xlib import X, display, XK
            self.X = X
            self.display = display
            self.XK = XK
        except ImportError:
            print("[flktux.numpad] python3-xlib not installed; physical numpad listener disabled.", file=sys.stderr)
            return

        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.d and self.root:
            try:
                for kc in self.grabbed_keycodes.values():
                    self.root.ungrab_key(kc, self.X.AnyModifier)
                self.d.sync()
            except Exception:
                pass

    def _run(self):
        try:
            self.d = self.display.Display()
            self.root = self.d.screen().root

            # Grab numpad keys
            for key_name in NUMPAD_GRID_MAP.keys():
                ks = self.XK.string_to_keysym(key_name)
                if ks:
                    kc = self.d.keysym_to_keycode(ks)
                    if kc:
                        self.grabbed_keycodes[key_name] = kc
                        self.root.grab_key(
                            kc,
                            self.X.AnyModifier,
                            True,
                            self.X.GrabModeAsync,
                            self.X.GrabModeAsync
                        )

            self.d.sync()

            # Event loop
            while self.running:
                event = self.d.next_event()
                if event.type == self.X.KeyPress:
                    for name, kc in self.grabbed_keycodes.items():
                        if event.detail == kc:
                            r, c = NUMPAD_GRID_MAP[name]
                            GLib.idle_add(self.callback, r, c)
                            break
        except Exception as e:
            if self.running:
                print(f"[flktux.numpad] Listener stopped: {e}", file=sys.stderr)
