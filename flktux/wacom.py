#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
flktux.wacom: Wacom tablet control, sensitivity tuning, and profiles
Supports Bamboo CTH-470 and all xsetwacom compatible graphic tablets.
"""

import os
import json
import subprocess
from typing import Dict, Any, Optional

SETTINGS_DIR = os.path.expanduser("~/.config/flktux")
SETTINGS_FILE = os.path.join(SETTINGS_DIR, "wacom_settings.json")

# Preset Profiles
PROFILES = {
    "art": {
        "name": "🎨 お絵描き・イラスト制作",
        "description": "手ブレ補正ON、なめらか線画、筆圧柔らかめ、16:9正円比率維持、手のひら誤爆防止(タッチOFF)",
        "pressure_curve": "5 20 80 100",  # 柔らかめ (軽い力で強弱が出る)
        "pressure_curve_level": 2,
        "raw_sample": 6,                  # 手ブレ補正・スムージング
        "suppress": 2,
        "threshold": 12,                  # 軽いタッチ
        "aspect_ratio_16_9": True,        # 正円を描けるArea比率 (0 0 14720 8280)
        "touch_enabled": False,           # パームリジェクション (タッチOFF)
        "pointer_speed": 1.2,
        "scroll_distance": 30,
    },
    "fast": {
        "name": "⚡ 超機敏・快速デスクトップ",
        "description": "遅延ゼロ(RawSample 1)、最高速レスポンス、羽のように軽いクリック、トラックパッド高速モード",
        "pressure_curve": "0 0 100 100",  # リニア
        "pressure_curve_level": 3,
        "raw_sample": 1,                  # 遅延ゼロ (ペン先に完全追従)
        "suppress": 0,                    # 微細な動きも即座に検知
        "threshold": 8,                   # 超高感度クリック
        "aspect_ratio_16_9": False,       # 盤面全域を使う
        "touch_enabled": True,            # 指タッチON
        "pointer_speed": 1.8,             # 高速トラックパッド
        "scroll_distance": 25,
    },
    "standard": {
        "name": "⚖️ 標準・バランス",
        "description": "Wacom公式推奨の標準バランス設定",
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


class WacomManager:
    """Wacom デバイスの検出と設定適用・永続化を管理"""

    def __init__(self):
        self.stylus_name: Optional[str] = None
        self.touch_name: Optional[str] = None
        self.pad_name: Optional[str] = None
        self.eraser_name: Optional[str] = None
        self.detect_devices()

    def detect_devices(self):
        try:
            out = subprocess.check_output(
                ["xsetwacom", "--list", "devices"],
                stderr=subprocess.DEVNULL,
                text=True
            )
            for line in out.strip().splitlines():
                if "type: STYLUS" in line:
                    self.stylus_name = line.split("\tid:")[0].strip()
                elif "type: TOUCH" in line:
                    self.touch_name = line.split("\tid:")[0].strip()
                elif "type: PAD" in line:
                    self.pad_name = line.split("\tid:")[0].strip()
                elif "type: ERASER" in line:
                    self.eraser_name = line.split("\tid:")[0].strip()
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

    def save_settings(self, cfg: Dict[str, Any]):
        os.makedirs(SETTINGS_DIR, exist_ok=True)
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[flktux.wacom] Failed to save settings: {e}")

    def apply_settings(self, cfg: Dict[str, Any]):
        """設定を live に適用 (xsetwacom / xinput)"""
        self.detect_devices()

        # 1. スタイラスペン設定
        if self.stylus_name:
            curve = cfg.get("pressure_curve", "0 0 100 100")
            raw = str(cfg.get("raw_sample", 4))
            sup = str(cfg.get("suppress", 2))
            thresh = str(cfg.get("threshold", 20))

            subprocess.run(["xsetwacom", "set", self.stylus_name, "PressureCurve", curve], check=False)
            subprocess.run(["xsetwacom", "set", self.stylus_name, "RawSample", raw], check=False)
            subprocess.run(["xsetwacom", "set", self.stylus_name, "Suppress", sup], check=False)
            subprocess.run(["xsetwacom", "set", self.stylus_name, "Threshold", thresh], check=False)

            if cfg.get("aspect_ratio_16_9", False):
                # Bamboo 14720 x 9200 (16:10) を 16:9 (14720 x 8280) に合わせ正円を描けるようにする
                subprocess.run(["xsetwacom", "set", self.stylus_name, "Area", "0", "0", "14720", "8280"], check=False)
            else:
                subprocess.run(["xsetwacom", "set", self.stylus_name, "ResetArea"], check=False)

        # 2. 消しゴム設定 (スタイラスと連動)
        if self.eraser_name:
            curve = cfg.get("pressure_curve", "0 0 100 100")
            raw = str(cfg.get("raw_sample", 4))
            sup = str(cfg.get("suppress", 2))
            thresh = str(cfg.get("threshold", 20))
            subprocess.run(["xsetwacom", "set", self.eraser_name, "PressureCurve", curve], check=False)
            subprocess.run(["xsetwacom", "set", self.eraser_name, "RawSample", raw], check=False)
            subprocess.run(["xsetwacom", "set", self.eraser_name, "Suppress", sup], check=False)
            subprocess.run(["xsetwacom", "set", self.eraser_name, "Threshold", thresh], check=False)
            if cfg.get("aspect_ratio_16_9", False):
                subprocess.run(["xsetwacom", "set", self.eraser_name, "Area", "0", "0", "14720", "8280"], check=False)
            else:
                subprocess.run(["xsetwacom", "set", self.eraser_name, "ResetArea"], check=False)

        # 3. 指タッチ設定
        if self.touch_name:
            touch_on = "on" if cfg.get("touch_enabled", True) else "off"
            scroll_dist = str(cfg.get("scroll_distance", 30))
            subprocess.run(["xsetwacom", "set", self.touch_name, "Touch", touch_on], check=False)
            subprocess.run(["xsetwacom", "set", self.touch_name, "ScrollDistance", scroll_dist], check=False)

            # トラックパッド速度
            speed = float(cfg.get("pointer_speed", 1.4))
            s_str = f"{speed:.2f}"
            matrix = [s_str, "0", "0", "0", s_str, "0", "0", "0", "1"]
            subprocess.run(
                ["xinput", "set-prop", self.touch_name, "Coordinate Transformation Matrix"] + matrix,
                check=False
            )


# Global singleton instance
WACOM = WacomManager()
