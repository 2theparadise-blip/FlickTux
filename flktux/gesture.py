#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
flktux.gesture: Lightweight  Unistroke Recognizer for Wacom surface pen gestures
Detects gestures drawn on the tablet surface (Z: Undo, S: Save, C: FlickTux, etc.)
"""

import math
from typing import List, Tuple, Optional, Dict

Point = Tuple[float, float]
NUM_POINTS = 32
SQUARE_SIZE = 250.0

RAW_TEMPLATES = {
    "Z": [
        (0, 0), (50, 0), (100, 0), (150, 0), (200, 0),
        (150, 50), (100, 100), (50, 150), (0, 200),
        (50, 200), (100, 200), (150, 200), (200, 200)
    ],
    "S": [
        (200, 20), (150, 0), (50, 10), (10, 50), (40, 90), (120, 110),
        (180, 130), (190, 170), (150, 200), (50, 200), (0, 170)
    ],
    "C": [
        (180, 20), (100, 0), (30, 40), (0, 100), (30, 160), (100, 200), (180, 180)
    ],
    "O": [
        (100, 0), (30, 30), (0, 100), (30, 170), (100, 200),
        (170, 170), (200, 100), (170, 30), (100, 0)
    ],
    "LEFT": [
        (200, 100), (150, 100), (100, 100), (50, 100), (0, 100)
    ],
    "RIGHT": [
        (0, 100), (50, 100), (100, 100), (150, 100), (200, 100)
    ]
}


def _path_length(points: List[Point]) -> float:
    d = 0.0
    for i in range(1, len(points)):
        d += math.hypot(points[i][0] - points[i-1][0], points[i][1] - points[i-1][1])
    return d


def _resample(points: List[Point], n: int) -> List[Point]:
    total_len = _path_length(points)
    if total_len <= 0.0 or len(points) < 2:
        return [points[0]] * n

    interval = total_len / (n - 1)
    new_points = [points[0]]
    d = 0.0
    pts = list(points)
    i = 1
    while i < len(pts):
        step = math.hypot(pts[i][0] - pts[i-1][0], pts[i][1] - pts[i-1][1])
        if step == 0:
            i += 1
            continue
        if d + step >= interval:
            ratio = (interval - d) / step
            nx = pts[i-1][0] + ratio * (pts[i][0] - pts[i-1][0])
            ny = pts[i-1][1] + ratio * (pts[i][1] - pts[i-1][1])
            new_points.append((nx, ny))
            pts.insert(i, (nx, ny))
            d = 0.0
        else:
            d += step
        i += 1

    while len(new_points) < n:
        new_points.append(pts[-1])
    return new_points[:n]


def _scale_to_square(points: List[Point], size: float) -> List[Point]:
    min_x = min(p[0] for p in points)
    max_x = max(p[0] for p in points)
    min_y = min(p[1] for p in points)
    max_y = max(p[1] for p in points)
    w = max_x - min_x or 1.0
    h = max_y - min_y or 1.0
    return [((p[0] - min_x) * size / w, (p[1] - min_y) * size / h) for p in points]


def _translate_to_origin(points: List[Point]) -> List[Point]:
    cx = sum(p[0] for p in points) / len(points)
    cy = sum(p[1] for p in points) / len(points)
    return [(p[0] - cx, p[1] - cy) for p in points]


def _prepare(raw_points: List[Point]) -> List[Point]:
    res = _resample(raw_points, NUM_POINTS)
    scaled = _scale_to_square(res, SQUARE_SIZE)
    return _translate_to_origin(scaled)


PROCESSED_TEMPLATES: Dict[str, List[Point]] = {
    name: _prepare(raw) for name, raw in RAW_TEMPLATES.items()
}


def recognize_gesture(stroke: List[Point]) -> Tuple[Optional[str], float]:
    if len(stroke) < 4 or _path_length(stroke) < 20.0:
        return None, 0.0

    cand = _prepare(stroke)
    best_dist = float("inf")
    best_name = None

    half_diag = 0.5 * math.hypot(SQUARE_SIZE, SQUARE_SIZE)

    for name, templ in PROCESSED_TEMPLATES.items():
        total_dist = 0.0
        for i in range(NUM_POINTS):
            total_dist += math.hypot(cand[i][0] - templ[i][0], cand[i][1] - templ[i][1])
        avg_dist = total_dist / NUM_POINTS
        if avg_dist < best_dist:
            best_dist = avg_dist
            best_name = name

    score = max(0.0, 1.0 - (best_dist / half_diag))
    if score >= 0.70:
        return best_name, score
    return None, score
