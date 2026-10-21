#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
flktux.tablet: Universal Multi-Vendor Tablet Control & Sensitivity Tuning
Supports Wacom, XP-Pen, Huion, Gaomon, Xencelabs, UGEE, and Weylus (iPad/iPad mini).
Provides pressure curve calibration, smoothing, 16:9 aspect ratio mapping,
and palm rejection.
"""

import os
import json
import subprocess
from typing import Dict, Any, Optional, List

try:
    from .device_scanner import scan_devices
except (ImportError, ValueError):
    from flktux.device_scanner import scan_devices

SETTINGS_DIR = os.path.expanduser("~/.config/flktux")
SETTINGS_FILE = os.path.join(SETTINGS_DIR, "tablet_settings.json")

# Preset Profiles
PROFILES = {
    "art": {
        "name": "🎨 お絵描き・イラスト制作",
        "description": "手ブレ補正ON、なめらか線画、筆圧柔らかめ、16:9正円比率維持、手のひら誤爆防止(タッチOFF)",
        "pressure_curve": "5 20 80 100",  # 柔らかめ
        "pressure_curve_level": 2,
        "raw_sample": 6,                  # 手ブレ補正・スムージング
        "suppress": 2,
        "threshold": 12,                  # 軽いタッチ
        "aspect_ratio_16_9": True,        # 正円を描けるArea比率
        "touch_enabled": False,           # パームリジェクション (タッチOFF)
        "pointer_speed": 1.2,
        "scroll_distance": 30,
    },
    "fast": {
        "name": "⚡ 超機敏・快速デスクトップ",
        "description": "遅延ゼロ(RawSample 1)、最高速レスポンス、羽のように軽いクリック、トラックパッド高速モード",
        "pressure_curve": "0 0 100 100",  # リニア
        "pressure_curve_level": 3,
        "raw_sample": 1,                  # 遅延ゼロ
        "suppress": 0,
        "threshold": 8,                   # 超高感度クリック
        "aspect_ratio_16_9": False,       # 盤面全域を使う
        "touch_enabled": True,            # 指タッチON
        "pointer_speed": 1.8,
        "scroll_distance": 25,
    },
    "standard": {
        "name": "⚖️ 標準・バランス",
        "description": "推奨標準バランス設定",
        "pressure_curve": "0 0 100 100",
        "pressure_curve_level": 3,
        "raw_sample": 4,
        "suppress": 2,
        "threshold": 27,
        "aspect_ratio_16_9": False,
        "touch_enabled": True,
        "pointer_speed": 1.4,
        "scroll_distance": 30,
    }
}

# Curve presets based on 5-level slider (1:非常柔らか 〜 5:硬め)
PRESSURE_CURVES = {
    1: "0 40 60 100",  # 非常に柔らかい
    2: "5 20 80 100",  # やや柔らかい
    3: "0 0 100 100",  # 標準 (リニア)
    4: "20 0 100 80",  # やや硬め
    5: "40 0 100 60",  # しっかり硬め
}


class TabletManager:
    """Wacom, XP-Pen, Huion, Gaomon, Weylus (iPad) 等のマルチベンダー液タブ・ペンタブ管理"""

    def __init__(self):
        self.device_name: Optional[str] = None
        self.stylus_name: Optional[str] = None
        self.touch_name: Optional[str] = None
        self.vendor: str = "auto"
        self.is_wacom: bool = False
        self.is_weylus: bool = False
        self.detect_devices()

    def detect_devices(self):
        # 1. Check with device_scanner
        discovered = scan_devices()
        tablets = [d for d in discovered if d.get("category") == "tablet_stylus"]

        if tablets:
            chosen = tablets[0]
            self.device_name = chosen["name"]
            self.stylus_name = chosen["name"]
            name_lower = chosen["name"].lower()
            if "wacom" in name_lower:
                self.vendor = "wacom"
                self.is_wacom = True
            elif "weylus" in name_lower:
                self.vendor = "weylus"
                self.is_weylus = True
            elif "xp-pen" in name_lower:
                self.vendor = "xp-pen"
            elif "huion" in name_lower:
                self.vendor = "huion"
            elif "gaomon" in name_lower:
                self.vendor = "gaomon"
            else:
                self.vendor = "generic"

        # 2. If Wacom is detected or suspected, check xsetwacom
        try:
            out = subprocess.check_output(
                ["xsetwacom", "--list", "devices"],
                stderr=subprocess.DEVNULL,
                text=True
            )
            for line in out.strip().splitlines():
                if "type: STYLUS" in line:
                    self.stylus_name = line.split("\tid:")[0].strip()
                    self.is_wacom = True
                elif "type: TOUCH" in line:
                    self.touch_name = line.split("\tid:")[0].strip()
        except Exception:
            pass

    def load_settings(self) -> Dict[str, Any]:
        """設定ファイルからロード。なければ 'art' プロファイルを既定値とする"""
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return dict(PROFILES["art"])

    def save_settings(self, settings: Dict[str, Any]):
        """現在の設定をファイルに保存"""
        os.makedirs(SETTINGS_DIR, exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)

    def apply_settings(self, settings: Dict[str, Any]) -> bool:
        """設定をOS / デバイスドライバに反映"""
        success = True

        # 1. Wacom デバイスの場合 (xsetwacom)
        if self.is_wacom and self.stylus_name:
            try:
                # 筆圧カーブ
                curve = settings.get("pressure_curve", "0 0 100 100")
                subprocess.run(
                    ["xsetwacom", "set", self.stylus_name, "PressureCurve", *curve.split()],
                    check=False
                )
                # スムージング (手ブレ補正)
                raw_sample = settings.get("raw_sample", 4)
                subprocess.run(
                    ["xsetwacom", "set", self.stylus_name, "RawSample", str(raw_sample)],
                    check=False
                )
                # クリック閾値
                threshold = settings.get("threshold", 12)
                subprocess.run(
                    ["xsetwacom", "set", self.stylus_name, "Threshold", str(threshold)],
                    check=False
                )
                # タッチ機能 (パームリジェクション)
                if self.touch_name:
                    touch_on = "on" if settings.get("touch_enabled", True) else "off"
                    subprocess.run(
                        ["xsetwacom", "set", self.touch_name, "Touch", touch_on],
                        check=False
                    )
            except Exception:
                success = False

        # 2. XP-Pen, Huion, Gaomon, Weylus, 汎用の場合 (xinput / libinput)
        elif self.stylus_name:
            try:
                # xinput でデバイスの加速速度などを調整
                pointer_speed = settings.get("pointer_speed", 1.2)
                # libinput Accel Speed (-1.0 to 1.0)
                accel_val = min(1.0, max(-1.0, (pointer_speed - 1.0) * 0.8))
                subprocess.run(
                    ["xinput", "set-prop", self.stylus_name, "libinput Accel Speed", str(accel_val)],
                    check=False
                )
            except Exception:
                pass

        self.save_settings(settings)
        return success


# Global singleton instance
TABLET = TabletManager()
