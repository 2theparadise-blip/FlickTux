#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
flktux.device_scanner: Discovers pen tablets (Wacom, XP-Pen, Huion, Gaomon, Weylus)
and DIY / Arduino 10-key devices (RP2040, Teensy, QMK, Arduino Pro Micro).
Provides live event sniffer for testing keypad presses.
"""

import os
import re
import glob
import threading
from typing import List, Dict, Any, Optional, Callable

DIY_VENDORS = {
    0x2341: "Arduino SA",
    0x1b4f: "SparkFun",
    0x239a: "Adafruit",
    0x2e8a: "Raspberry Pi (Pico/RP2040)",
    0x16c0: "PJRC (Teensy)",
    0x303a: "Espressif (ESP32)",
    0xfeed: "QMK Firmware",
    0x4653: "QMK / VIA Keypad",
}

TABLET_VENDORS = {
    0x056a: "Wacom",
    0x28bd: "XP-Pen",
    0x256c: "Huion",
    0x5543: "UC-Logic / Gaomon",
    0x0b57: "Hanvon",
    0x2e2c: "Xencelabs",
}


def scan_devices() -> List[Dict[str, Any]]:
    """システムに接続されている液タブ・ペンタブ、自作10キー、テンキーデバイスを網羅走査"""
    devices = []
    visited_events = set()

    # 1. /dev/input/by-id から優先的にスキャン (永続的シンボリックリンク)
    by_id_pattern = "/dev/input/by-id/*"
    for link_path in sorted(glob.glob(by_id_pattern)):
        try:
            real_path = os.path.realpath(link_path)
            visited_events.add(real_path)
            info = _inspect_device_path(link_path, real_path)
            if info:
                devices.append(info)
        except Exception:
            pass

    # 2. 残りの /dev/input/event* をスキャン
    for event_path in sorted(glob.glob("/dev/input/event*")):
        if event_path not in visited_events:
            try:
                info = _inspect_device_path(event_path, event_path)
                if info:
                    devices.append(info)
            except Exception:
                pass

    # 推奨度と名前でソート
    devices.sort(key=lambda d: (not d.get("is_recommended", False), d.get("category", ""), d.get("name", "")))
    return devices


def _inspect_device_path(display_path: str, real_path: str) -> Optional[Dict[str, Any]]:
    event_name = os.path.basename(real_path)
    sys_device_dir = f"/sys/class/input/{event_name}/device"

    if not os.path.exists(sys_device_dir):
        return None

    name = "Unknown Device"
    name_file = os.path.join(sys_device_dir, "name")
    if os.path.exists(name_file):
        try:
            with open(name_file, "r", encoding="utf-8", errors="ignore") as f:
                name = f.read().strip()
        except Exception:
            pass

    vid, pid = 0, 0
    id_file = os.path.join(sys_device_dir, "id/vendor")
    if os.path.exists(id_file):
        try:
            with open(id_file, "r") as f:
                vid = int(f.read().strip(), 16)
        except Exception:
            pass

    pid_file = os.path.join(sys_device_dir, "id/product")
    if os.path.exists(pid_file):
        try:
            with open(pid_file, "r") as f:
                pid = int(f.read().strip(), 16)
        except Exception:
            pass

    name_lower = name.lower()

    # Weylus Detection
    if "weylus stylus" in name_lower:
        return {
            "path": display_path,
            "real_path": real_path,
            "name": name,
            "vendor_id": vid,
            "product_id": pid,
            "category": "tablet_stylus",
            "is_recommended": True,
            "description": "📱 Weylus iPad / iPad mini 仮想スタイラス (Apple Pencil)",
        }
    if "weylus touch" in name_lower:
        return {
            "path": display_path,
            "real_path": real_path,
            "name": name,
            "vendor_id": vid,
            "product_id": pid,
            "category": "tablet_touch",
            "is_recommended": True,
            "description": "📱 Weylus iPad / iPad mini 仮想マルチタッチ",
        }

    # Tablet detection
    is_tablet_vendor = vid in TABLET_VENDORS or any(t in name_lower for t in [
        "wacom", "xp-pen", "huion", "gaomon", "xencelabs", "ugee", "ug-tablet", "veikk", "parblo", "hanvon", "artisul"
    ])

    if is_tablet_vendor or "stylus" in name_lower or "pen" in name_lower:
        vendor_label = TABLET_VENDORS.get(vid, "液タブ / 板タブ")
        return {
            "path": display_path,
            "real_path": real_path,
            "name": name,
            "vendor_id": vid,
            "product_id": pid,
            "category": "tablet_stylus",
            "is_recommended": True,
            "description": f"🖊️ {vendor_label}: ペン入力 (筆圧検知対応)",
        }

    # DIY Keypad / Arduino / RP2040 / Push-phone
    is_diy = vid in DIY_VENDORS or any(k in name_lower for k in [
        "arduino", "pico", "teensy", "sparkfun", "adafruit", "keypad", "numpad", "macropad", "qmk", "dialpad"
    ])

    if is_diy:
        vendor_label = DIY_VENDORS.get(vid, "自作キーパッド")
        return {
            "path": display_path,
            "real_path": real_path,
            "name": name,
            "vendor_id": vid,
            "product_id": pid,
            "category": "diy_keypad",
            "is_recommended": True,
            "description": f"🔌 {vendor_label} (自作10キー / プッシュフォン推奨)",
        }

    # Standard Keyboard or keypad
    if "keyboard" in name_lower or "-kbd" in display_path:
        return {
            "path": display_path,
            "real_path": real_path,
            "name": name,
            "vendor_id": vid,
            "product_id": pid,
            "category": "standard_keyboard",
            "is_recommended": False,
            "description": "⌨ 標準キーボード / テンキー部",
        }

    return None


class KeypadSniffer:
    """デバイスからのリアルタイムキー入力をバックグラウンドで監視し、
    押されたキー（1〜9, 0, *, # 等）をGUIテスト用に通知するスニッファー"""

    def __init__(self, device_path: str, callback: Callable[[str], None]):
        self.device_path = device_path
        self.callback = callback
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.fd: Optional[int] = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.fd is not None:
            try:
                os.close(self.fd)
            except Exception:
                pass
            self.fd = None

    def _run(self):
        try:
            # Open evdev node in read-only mode
            real_path = os.path.realpath(self.device_path)
            self.fd = os.open(real_path, os.O_RDONLY | os.O_NONBLOCK)
            import select
            import struct

            # struct input_event { struct timeval time; __u16 type; __u16 code; __s32 value; };
            # 64-bit Linux: 16 (timeval) + 2 (type) + 2 (code) + 4 (value) = 24 bytes
            EVENT_FORMAT = "llHHI"
            EVENT_SIZE = struct.calcsize(EVENT_FORMAT)

            while self.running and self.fd is not None:
                r, _, _ = select.select([self.fd], [], [], 0.2)
                if self.fd in r:
                    data = os.read(self.fd, EVENT_SIZE * 16)
                    for i in range(0, len(data), EVENT_SIZE):
                        chunk = data[i:i + EVENT_SIZE]
                        if len(chunk) == EVENT_SIZE:
                            _, _, ev_type, ev_code, ev_val = struct.unpack(EVENT_FORMAT, chunk)
                            if ev_type == 1 and ev_val == 1:  # EV_KEY KeyPress
                                key_label = self._keycode_to_label(ev_code)
                                if key_label:
                                    self.callback(key_label)
        except Exception:
            pass

    @staticmethod
    def _keycode_to_label(code: int) -> Optional[str]:
        # Standard Linux Keycodes
        CODE_MAP = {
            79: "1", 80: "2", 81: "3",  # KP_1, KP_2, KP_3
            75: "4", 76: "5", 77: "6",  # KP_4, KP_5, KP_6
            71: "7", 72: "8", 73: "9",  # KP_7, KP_8, KP_9
            82: "0",                     # KP_0
            55: "*",                     # KP_MULTIPLY
            98: "/",                     # KP_DIVIDE
            74: "-",                     # KP_SUBTRACT
            78: "+",                     # KP_ADD
            83: ".",                     # KP_DOT / KP_DELETE
            96: "#",                     # KP_ENTER (treated as # / Enter)
            28: "Enter",                 # KEY_ENTER
            2: "1", 3: "2", 4: "3", 5: "4", 6: "5", 7: "6", 8: "7", 9: "8", 10: "9", 11: "0",
        }
        return CODE_MAP.get(code)
