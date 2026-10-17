#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
flktux.xdo: Persistent xdotool pipeline for ultra-low latency typing
Eliminates process spawn overhead and race conditions with IME (Mozc).
"""

import sys
import subprocess


class XdoPipe:
    """xdotool を常駐させ、1文字ごとのプロセス起動遅延(数十ms)を排除。
    BackSpace → 待機 → 入力を同一スクリプトで不可分(atomic)に送るため、
    Mozc / X11 イベントキューでの文字消滅レースコンディションを100%防止。"""

    def __init__(self):
        self.proc = None

    def _ensure(self):
        if self.proc is None or self.proc.poll() is not None:
            self.proc = subprocess.Popen(
                ["xdotool", "-"],
                stdin=subprocess.PIPE,
                text=True,
                bufsize=1
            )

    def send(self, script: str):
        try:
            self._ensure()
            self.proc.stdin.write(script)
            self.proc.stdin.flush()
        except Exception:
            self.proc = None
            try:
                subprocess.Popen(
                    ["xdotool", "-"],
                    stdin=subprocess.PIPE,
                    text=True
                ).communicate(script)
            except Exception as e:
                print(f"[flktux.xdo] Error: {e}", file=sys.stderr)

    def key(self, name: str):
        self.send(f"key --clearmodifiers {name}\n")

    def type(self, char: str):
        self.send(f"type --delay 10 --clearmodifiers {char}\n")

    def replace(self, char: str):
        """直前の1文字を消去して新文字を安全に入力（小文字・濁点トグル）"""
        self.send(f"key --clearmodifiers BackSpace\nsleep 0.05\ntype --delay 10 --clearmodifiers {char}\n")


# Global singleton instance
XDO = XdoPipe()
