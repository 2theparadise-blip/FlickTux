#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
flktux.engine.flick_detector: 4-way flick direction and 18px deadzone detector
Pure calculation domain, independent of GTK3 UI.
"""

import math
from typing import Optional, Tuple


class FlickDetector:
    """
    接触開始点からの変位 $(dx, dy)$ と移動距離を算出し、
    18pxデッドゾーン判定および上下左右4方向フリック判定を行う。
    """

    # 仕様 3.1 & 7.3: 初期点復帰デッドゾーン (18px不感帯判定)
    DEADZONE_RADIUS = 18.0

    def __init__(self, deadzone: float = DEADZONE_RADIUS):
        self.deadzone = deadzone
        self.start_x: float = 0.0
        self.start_y: float = 0.0
        self.is_active: bool = False
        self.current_dir: str = "center"

    def start(self, x: float, y: float):
        """フリック操作の開始点（キー中心またはタップ開始座標）を記録"""
        self.start_x = float(x)
        self.start_y = float(y)
        self.is_active = True
        self.current_dir = "center"

    def update(self, current_x: float, current_y: float) -> str:
        """
        現在のポインタ座標から方向を計算して返す。
        戻り値: 'center', 'left', 'up', 'right', 'down'
        """
        if not self.is_active:
            return "center"

        dx = float(current_x) - self.start_x
        dy = float(current_y) - self.start_y
        distance = math.hypot(dx, dy)

        # 18px以内の変位はすべて center (タップ・初期点復帰デッドゾーン)
        if distance <= self.deadzone:
            self.current_dir = "center"
            return "center"

        # 角度計算 (-180度 〜 +180度, 0度は真右(X軸正方向))
        # Y軸は下方向が正となる画面GUI座標系
        angle = math.degrees(math.atan2(dy, dx))

        # 4方向判定 (+/- 45度の対角線で4分割)
        if -45.0 <= angle < 45.0:
            d = "right"
        elif 45.0 <= angle < 135.0:
            d = "down"
        elif -135.0 <= angle < -45.0:
            d = "up"
        else:
            d = "left"

        self.current_dir = d
        return d

    def reset(self):
        """フリック操作を終了し、状態をリセット"""
        self.is_active = False
        self.current_dir = "center"
        self.start_x = 0.0
        self.start_y = 0.0
