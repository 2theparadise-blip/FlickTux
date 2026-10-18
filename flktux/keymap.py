#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
flktux.keymap: Keymap and button assignment management for Wacom & FlickTux
Allows dynamic user customization of Stylus buttons, ExpressKeys, and Gestures.
"""

import os
import json
import subprocess
from typing import Dict, Any, List, Optional

KEYMAP_DIR = os.path.expanduser("~/.config/flktux")
KEYMAP_FILE = os.path.join(KEYMAP_DIR, "keymap.json")

# Available action choices for buttons
BUTTON_ACTIONS = {
    "flick_toggle": {
        "label": "📱 FlickTux 開閉 (F12)",
        "wacom_val": "key F12",
        "desc": "キーボードの表示/非表示を瞬時にトグル"
    },
    "undo": {
        "label": "↩️ 元に戻す (Ctrl+Z)",
        "wacom_val": "key +ctrl z -ctrl",
        "desc": "直前の描画・操作を取り消し"
    },
    "redo": {
        "label": "↪️ やり直し (Ctrl+Y)",
        "wacom_val": "key +ctrl y -ctrl",
        "desc": "取り消した操作を再実行"
    },
    "save": {
        "label": "💾 上書き保存 (Ctrl+S)",
        "wacom_val": "key +ctrl s -ctrl",
        "desc": "ファイルを即座に保存"
    },
    "eyedropper": {
        "label": "💉 スポイト (Alt)",
        "wacom_val": "key alt",
        "desc": "キャンバスの色を吸い取る"
    },
    "hand": {
        "label": "✋ 手のひら移動 (Space)",
        "wacom_val": "key space",
        "desc": "画面のスクロール・パン移動"
    },
    "right_click": {
        "label": "🖱️ 右クリック",
        "wacom_val": "button +3",
        "desc": "右クリックメニューを表示"
    },
    "middle_click": {
        "label": "🖱️ 中クリック (ホイール)",
        "wacom_val": "button +2",
        "desc": "中クリック・自動スクロール"
    },
    "eraser_toggle": {
        "label": "🧹 消しゴム切替 (E)",
        "wacom_val": "key e",
        "desc": "ブラシと消しゴムを切り替え"
    },
    "disabled": {
        "label": "⛔ 無効 (何もしない)",
        "wacom_val": "0",
        "desc": "誤爆防止のためボタンを無効化"
    }
}

DEFAULT_KEYMAP = {
    "stylus": {
        "button2": "right_click",    # 下ボタン: 右クリック
        "button3": "flick_toggle",   # 上ボタン: FlickTux ワンタッチ召喚 (おすすめ!)
    },
    "pad": {
        "key1": "undo",             # 上ボタン①: 取り消し
        "key2": "redo",             # 2段目②: やり直し
        "key3": "flick_toggle",     # 3段目③: FlickTux 起動
        "key4": "hand",             # 下ボタン④: 手のひら
    },
    "gestures": {
        "Z": "key +ctrl z -ctrl",   # 盤面に「Z」を描く ➔ Undo
        "S": "key +ctrl s -ctrl",   # 盤面に「S」を描く ➔ Save
        "C": "flick_toggle",        # 盤面に「C」を描く ➔ FlickTux
    }
}


class KeymapManager:
    """ユーザーキーマップの保存・読込・Wacomへの動的バインドを統括"""

    def __init__(self):
        self.stylus_name: Optional[str] = None
        self.pad_name: Optional[str] = None
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
                elif "type: PAD" in line:
                    self.pad_name = line.split("\tid:")[0].strip()
        except Exception:
            pass

    def load_keymap(self) -> Dict[str, Any]:
        if os.path.exists(KEYMAP_FILE):
            try:
                with open(KEYMAP_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Merge with default to ensure all keys exist
                    merged = dict(DEFAULT_KEYMAP)
                    for sec in ("stylus", "pad", "gestures"):
                        if sec in data:
                            merged[sec] = dict(DEFAULT_KEYMAP.get(sec, {}))
                            merged[sec].update(data[sec])
                    return merged
            except Exception as e:
                print(f"[flktux.keymap] Load error: {e}")
        return dict(DEFAULT_KEYMAP)

    def save_keymap(self, data: Dict[str, Any]):
        os.makedirs(KEYMAP_DIR, exist_ok=True)
        try:
            with open(KEYMAP_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.apply_keymap(data)
        except Exception as e:
            print(f"[flktux.keymap] Save error: {e}")

    def apply_keymap(self, cfg: Optional[Dict[str, Any]] = None):
        if cfg is None:
            cfg = self.load_keymap()
        self.detect_devices()

        # 1. Stylus Buttons (Button 2: 下, Button 3: 上)
        if self.stylus_name:
            stylus_cfg = cfg.get("stylus", {})
            b2_act = stylus_cfg.get("button2", "right_click")
            b3_act = stylus_cfg.get("button3", "flick_toggle")

            b2_val = BUTTON_ACTIONS.get(b2_act, {}).get("wacom_val", "button +3")
            b3_val = BUTTON_ACTIONS.get(b3_act, {}).get("wacom_val", "key F12")

            subprocess.run(["xsetwacom", "set", self.stylus_name, "Button", "2", b2_val], check=False)
            subprocess.run(["xsetwacom", "set", self.stylus_name, "Button", "3", b3_val], check=False)

        # 2. ExpressKeys Pad Buttons (Bamboo CTH-470 は Button 1, 2, 3, 8)
        if self.pad_name:
            pad_cfg = cfg.get("pad", {})
            mapping = [
                ("1", pad_cfg.get("key1", "undo")),
                ("2", pad_cfg.get("key2", "redo")),
                ("3", pad_cfg.get("key3", "flick_toggle")),
                ("8", pad_cfg.get("key4", "hand")),
            ]
            for btn_num, act_key in mapping:
                val = BUTTON_ACTIONS.get(act_key, {}).get("wacom_val", "0")
                subprocess.run(["xsetwacom", "set", self.pad_name, "Button", btn_num, val], check=False)


KEYMAP = KeymapManager()

if __name__ == '__main__':
    km = KEYMAP.load_keymap()
    KEYMAP.apply_keymap(km)
    print("Keymap applied successfully!")
