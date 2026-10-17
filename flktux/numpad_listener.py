#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
flktux.numpad_listener: Physical 10-key (NumPad) hardware integration
Listens for PC numpad / external Bluetooth/USB numpad keys and maps to
FlickTux 10-key toggle input (7:あ, 8:か, 9:さ, 4:た, 5:な, 6:は, 1:ま, 2:や, 3:ら, 0:わ).
"""

import sys
import threading
from typing import Callable, Optional
from gi.repository import GLib

# Physical KeyPad symbol names to FlickTux actions / keys
NUMPAD_KEY_MAP = {
    "KP_7": ("flick", "あ"),
    "KP_8": ("flick", "か"),
    "KP_9": ("flick", "さ"),
    "KP_4": ("flick", "た"),
    "KP_5": ("flick", "な"),
    "KP_6": ("flick", "は"),
    "KP_1": ("flick", "ま"),
    "KP_2": ("flick", "や"),
    "KP_3": ("flick", "ら"),
    "KP_0": ("flick", "わ"),
    "KP_Decimal": ("flick", "、。"),
    "KP_Multiply": ("action", "dakuten"),   # * -> ゛゜小
    "KP_Divide": ("action", "symbol"),      # / -> 記号
    "KP_Subtract": ("action", "space"),     # - -> 空白
    "KP_Add": ("action", "next"),           # + -> 次へ (トグル確定)
    "KP_Enter": ("action", "enter"),        # Enter -> 確定
    "KP_Delete": ("action", "backspace"),   # Delete -> ⌫
    "BackSpace": ("action", "backspace"),
}


class NumpadListener:
    """X11 バックグラウンドリスナー: 物理テンキーの入力を検知し、
    フォーカスに関わらず FlickTux のガラケー打ちトグルを実行"""

    def __init__(self, callback: Callable[[str, str], None]):
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
            for key_name in NUMPAD_KEY_MAP.keys():
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
                            kind, target = NUMPAD_KEY_MAP[name]
                            GLib.idle_add(self.callback, kind, target)
                            break
        except Exception as e:
            if self.running:
                print(f"[flktux.numpad] Listener stopped: {e}", file=sys.stderr)
