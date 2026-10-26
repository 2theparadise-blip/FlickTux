#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
flktux.numpad_listener: Physical 10-key (NumPad) & DIY / Arduino device integration.
Supports:
1. Specific device binding (e.g. /dev/input/by-id/usb-Arduino...) with EVIOCGRAB
   so DIY keypads / push-phones do not leak keystrokes into other desktop applications.
2. Global X11 grab fallback for standard PC/Bluetooth numpads.
"""

import os
import sys
import threading
import select
import struct
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

# Linux evdev keycode mapping to grid position (row, col)
EVDEV_CODE_MAP = {
    98: (0, 0),   # KEY_KPSLASH (/)
    71: (1, 0),   # KEY_KP7 (7)
    72: (1, 1),   # KEY_KP8 (8)
    73: (1, 2),   # KEY_KP9 (9)
    74: (1, 3),   # KEY_KPMINUS (-)

    75: (2, 0),   # KEY_KP4 (4)
    76: (2, 1),   # KEY_KP5 (5)
    77: (2, 2),   # KEY_KP6 (6)

    79: (3, 0),   # KEY_KP1 (1)
    80: (3, 1),   # KEY_KP2 (2)
    81: (3, 2),   # KEY_KP3 (3)
    78: (3, 3),   # KEY_KPPLUS (+)

    82: (4, 0),   # KEY_KP0 (0)
    83: (4, 1),   # KEY_KPDOT (.)
    55: (4, 2),   # KEY_KPASTERISK (*)
    96: (4, 3),   # KEY_KPENTER (Enter)
    28: (4, 3),   # KEY_ENTER

    14: (0, 3),   # KEY_BACKSPACE
    111: (0, 3),  # KEY_DELETE
}


class NumpadListener:
    """物理テンキー / 自作 Arduino テンキーの入力を検知し、
    フォーカスに関わらず FlickTux のガラケー打ちトグルを実行"""

    def __init__(self, callback: Callable[[int, int], None], device_path: Optional[str] = None, exclusive_grab: bool = False):
        self.callback = callback
        self.device_path = device_path
        self.exclusive_grab = exclusive_grab
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.d = None
        self.root = None
        self.grabbed_keycodes = {}
        self.evdev_fd: Optional[int] = None

    def start(self):
        if self.running:
            return
        self.running = True

        # Check if direct device path is specified and accessible
        if self.device_path and os.path.exists(self.device_path):
            self.thread = threading.Thread(target=self._run_evdev, daemon=True)
            self.thread.start()
            return

        # Fallback to X11 grab
        try:
            from Xlib import X, display, XK
            self.X = X
            self.display = display
            self.XK = XK
            self.thread = threading.Thread(target=self._run_x11, daemon=True)
            self.thread.start()
        except ImportError:
            print("[flktux.numpad] python3-xlib not installed; physical numpad listener disabled.", file=sys.stderr)

    def stop(self):
        self.running = False
        if self.evdev_fd is not None:
            try:
                if self.exclusive_grab:
                    import fcntl
                    # EVIOCGRAB = 0x40044590 (release grab: arg 0)
                    fcntl.ioctl(self.evdev_fd, 0x40044590, 0)
                os.close(self.evdev_fd)
            except Exception:
                pass
            self.evdev_fd = None

        if self.d and self.root:
            try:
                for kc in self.grabbed_keycodes.values():
                    self.root.ungrab_key(kc, self.X.AnyModifier)
                self.d.sync()
            except Exception:
                pass

    def _run_evdev(self):
        """Direct evdev reader for specific DIY device (with optional EVIOCGRAB)"""
        try:
            real_path = os.path.realpath(self.device_path)
            self.evdev_fd = os.open(real_path, os.O_RDONLY | os.O_NONBLOCK)

            if self.exclusive_grab:
                try:
                    import fcntl
                    # EVIOCGRAB = 0x40044590 (exclusive grab: arg 1)
                    fcntl.ioctl(self.evdev_fd, 0x40044590, 1)
                    print(f"[flktux.numpad] Exclusive grab enabled on {real_path}")
                except Exception as e:
                    print(f"[flktux.numpad] Warning: Could not enable EVIOCGRAB: {e}", file=sys.stderr)

            # Linux input_event structure
            EVENT_FORMAT = "llHHI"
            EVENT_SIZE = struct.calcsize(EVENT_FORMAT)

            while self.running and self.evdev_fd is not None:
                r, _, _ = select.select([self.evdev_fd], [], [], 0.3)
                if self.evdev_fd in r:
                    data = os.read(self.evdev_fd, EVENT_SIZE * 16)
                    for i in range(0, len(data), EVENT_SIZE):
                        chunk = data[i:i + EVENT_SIZE]
                        if len(chunk) == EVENT_SIZE:
                            _, _, ev_type, ev_code, ev_val = struct.unpack(EVENT_FORMAT, chunk)
                            if ev_type == 1 and ev_val == 1:  # EV_KEY Press
                                if ev_code in EVDEV_CODE_MAP:
                                    r_pos, c_pos = EVDEV_CODE_MAP[ev_code]
                                    GLib.idle_add(self.callback, r_pos, c_pos)
        except Exception as e:
            if self.running:
                print(f"[flktux.numpad] Evdev listener error: {e}", file=sys.stderr)

    def _run_x11(self):
        """X11 Grab fallback for generic desktop keyboards"""
        try:
            self.d = self.display.Display()
            # Suppress noisy BadAccess X protocol errors
            self.d.set_error_handler(lambda err, req=None: None)
            self.root = self.d.screen().root

            for key_name in NUMPAD_GRID_MAP.keys():
                try:
                    ks = self.XK.string_to_keysym(key_name)
                    if ks:
                        kc = self.d.keysym_to_keycode(ks)
                        if kc:
                            self.root.grab_key(
                                kc,
                                self.X.AnyModifier,
                                True,
                                self.X.GrabModeAsync,
                                self.X.GrabModeAsync
                            )
                            self.grabbed_keycodes[key_name] = kc
                except Exception:
                    pass
            self.d.sync()

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
                print(f"[flktux.numpad] X11 listener stopped: {e}", file=sys.stderr)
