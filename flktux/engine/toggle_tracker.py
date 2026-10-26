#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
flktux.engine.toggle_tracker: Multi-tap toggle cycling & commit timer management
Tracks sequential key presses (ガラケー連打) and auto-commit timeouts.
"""

from typing import Callable, Dict, List, Optional, Tuple


class ToggleTracker:
    """
    同一キー連打（ガラケー打ち）による文字サイクル進行、
    オートコミットタイマー、および濁点・半濁点・小文字変換を管理する。
    """

    def __init__(
        self,
        toggle_cycles: Optional[Dict[str, List[str]]] = None,
        dakuten_map: Optional[Dict[str, str]] = None,
        timeout_ms: int = 500,
        on_commit: Optional[Callable[[str], None]] = None,
        timer_starter: Optional[Callable[[int, Callable[[], None]], any]] = None,
        timer_canceler: Optional[Callable[[any], None]] = None,
    ):
        self.toggle_cycles = toggle_cycles or {}
        self.dakuten_map = dakuten_map or {}
        self.timeout_ms = timeout_ms

        self.current_key: Optional[str] = None
        self.current_index: int = 0
        self.last_char: str = ""
        self.is_cycling: bool = False

        self.timer_id = None
        self.on_commit = on_commit
        self.timer_starter = timer_starter
        self.timer_canceler = timer_canceler

    def set_timeout(self, ms: int):
        self.timeout_ms = max(100, int(ms))

    def _cancel_timer(self):
        if self.timer_id is not None:
            if self.timer_canceler:
                try:
                    self.timer_canceler(self.timer_id)
                except Exception:
                    pass
            self.timer_id = None

    def _start_timer(self):
        self._cancel_timer()
        if self.timer_starter:
            self.timer_id = self.timer_starter(self.timeout_ms, self._on_timeout)

    def _on_timeout(self):
        self.timer_id = None
        self.commit()
        return False

    def tap(self, key_name: str) -> Tuple[str, bool]:
        """
        キーがタップされた時の処理。
        戻り値: (char: str, is_cycle_advance: bool)
          - is_cycle_advance == True の場合: 直前の文字を置換（replace）
          - is_cycle_advance == False の場合: 新規文字として送信（type）
        """
        cycle = self.toggle_cycles.get(key_name)
        if not cycle:
            # トグルサイクル対象外の単一キー
            self.commit()
            self.last_char = key_name
            return key_name, False

        if self.is_cycling and self.current_key == key_name:
            # 同一キーの連打（サイクル進行）
            self._cancel_timer()
            self.current_index = (self.current_index + 1) % len(cycle)
            char = cycle[self.current_index]
            self.last_char = char
            self._start_timer()
            return char, True
        else:
            # 新しいキーの打鍵開始
            self.commit()
            self.current_key = key_name
            self.current_index = 0
            self.is_cycling = True
            char = cycle[0]
            self.last_char = char
            self._start_timer()
            return char, False

    def commit(self) -> Optional[str]:
        """現在トグル中の文字を確定し、サイクルを終了する"""
        self._cancel_timer()
        committed = None
        if self.is_cycling and self.current_key:
            cycle = self.toggle_cycles.get(self.current_key, [])
            if cycle and 0 <= self.current_index < len(cycle):
                committed = cycle[self.current_index]
        self.is_cycling = False
        self.current_key = None
        self.current_index = 0
        if committed and self.on_commit:
            self.on_commit(committed)
        return committed

    def toggle_dakuten(self) -> Optional[str]:
        """
        直前に入力された文字に対して、濁点・半濁点・小文字変換を適用する。
        変換後の文字を返す（変換不可なら None）。
        """
        if not self.last_char:
            return None
        toggled = self.dakuten_map.get(self.last_char)
        if toggled:
            self.commit()
            self.last_char = toggled
            return toggled
        return None

    def record_flick(self, char: str):
        """フリック確定文字の登録（トグルサイクルは確定終了）"""
        self.commit()
        self.last_char = char


Tuple_Char_Action = tuple[str, bool]
