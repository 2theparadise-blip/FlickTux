#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
flktux.engine.emitter: Low-latency keystroke and character emitter
Eliminates process spawn overhead and ensures display environment inheritance.
"""

import os
import sys
import subprocess
from typing import Optional


class XdoEmitter:
    """
    xdotool 常駐プロセスを通じた高速・不可分キー送出エミッタ。
    DISPLAY 環境変数を確実に継承し、OSキューでのレースコンディションを防止する。
    """

    def __init__(self, display: Optional[str] = None):
        self.display = display
        self.proc: Optional[subprocess.Popen] = None

    def _get_env(self) -> dict:
        env = dict(os.environ)
        if self.display:
            env["DISPLAY"] = self.display
        elif "DISPLAY" not in env or not env["DISPLAY"]:
            env["DISPLAY"] = ":0"
        return env

    def _ensure(self):
        if self.proc is None or self.proc.poll() is not None:
            self.proc = subprocess.Popen(
                ["xdotool", "-"],
                stdin=subprocess.PIPE,
                text=True,
                bufsize=1,
                env=self._get_env()
            )

    def send(self, script: str):
        """xdotool スクリプトを常駐パイプラインへ直接流し込む"""
        try:
            self._ensure()
            if self.proc and self.proc.stdin:
                self.proc.stdin.write(script)
                self.proc.stdin.flush()
        except Exception:
            self.proc = None
            try:
                subprocess.Popen(
                    ["xdotool", "-"],
                    stdin=subprocess.PIPE,
                    text=True,
                    env=self._get_env()
                ).communicate(script)
            except Exception as e:
                print(f"[flktux.engine.emitter] Error: {e}", file=sys.stderr)

    def key(self, key_name: str):
        """特殊キーやショートカットを送出 (例: 'Return', 'BackSpace', 'ctrl+z', 'Tab')"""
        self.send(f"key --clearmodifiers {key_name}\n")

    def type_char(self, char: str):
        """通常文字コードの送出"""
        # 特殊記号やクォートのエスケープ
        safe = char.replace("\\", "\\\\").replace("'", "\\'")
        self.send(f"type --delay 10 --clearmodifiers '{safe}'\n")

    def replace(self, char: str):
        """直前の1文字を BackSpace で消去し、新文字をアトミックに送信（濁点・小文字変換用）"""
        safe = char.replace("\\", "\\\\").replace("'", "\\'")
        self.send(f"key --clearmodifiers BackSpace\nsleep 0.05\ntype --delay 10 --clearmodifiers '{safe}'\n")

    def close(self):
        """プロセスの正常終了"""
        if self.proc:
            try:
                if self.proc.stdin:
                    self.proc.stdin.close()
                self.proc.terminate()
                self.proc.wait(timeout=0.5)
            except Exception:
                pass
            self.proc = None


# グローバルシングルトンインスタンス
EMITTER = XdoEmitter()
