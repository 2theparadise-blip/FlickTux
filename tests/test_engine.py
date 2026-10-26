#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_engine.py: Unit tests for flktux.engine domain
Tests XdoEmitter, FlickDetector, and ToggleTracker without GUI.
"""

import unittest
from flktux.engine.flick_detector import FlickDetector
from flktux.engine.toggle_tracker import ToggleTracker
from flktux.engine.emitter import XdoEmitter


class TestFlickDetector(unittest.TestCase):
    def setUp(self):
        self.detector = FlickDetector(deadzone=18.0)

    def test_deadzone(self):
        self.detector.start(100.0, 100.0)
        # Within 18px radius -> center
        self.assertEqual(self.detector.update(100.0, 100.0), "center")
        self.assertEqual(self.detector.update(110.0, 100.0), "center")  # dx=10
        self.assertEqual(self.detector.update(100.0, 115.0), "center")  # dy=15
        self.assertEqual(self.detector.update(112.0, 112.0), "center")  # hypot ~ 16.97

    def test_four_directions(self):
        self.detector.start(100.0, 100.0)
        # Right (dx = +30, dy = 0)
        self.assertEqual(self.detector.update(130.0, 100.0), "right")
        # Down (dx = 0, dy = +30)
        self.assertEqual(self.detector.update(100.0, 130.0), "down")
        # Left (dx = -30, dy = 0)
        self.assertEqual(self.detector.update(70.0, 100.0), "left")
        # Up (dx = 0, dy = -30)
        self.assertEqual(self.detector.update(100.0, 70.0), "up")

    def test_diagonal_boundaries(self):
        self.detector.start(100.0, 100.0)
        # 45 deg border (dx=+30, dy=+20 -> angle ~ 33.7 deg -> right)
        self.assertEqual(self.detector.update(130.0, 120.0), "right")
        # 60 deg (dx=+20, dy=+35 -> down)
        self.assertEqual(self.detector.update(120.0, 135.0), "down")

    def test_return_to_center_deadzone(self):
        self.detector.start(100.0, 100.0)
        # Flick out to right
        self.assertEqual(self.detector.update(150.0, 100.0), "right")
        # Return finger to start point within 18px -> center
        self.assertEqual(self.detector.update(105.0, 105.0), "center")


class TestToggleTracker(unittest.TestCase):
    def setUp(self):
        cycles = {
            "あ": ["あ", "い", "う", "え", "お"],
            "か": ["か", "き", "く", "け", "こ"],
        }
        dakuten = {
            "か": "が", "が": "か",
            "あ": "ぁ", "ぁ": "あ",
        }
        self.committed = []
        self.tracker = ToggleTracker(
            toggle_cycles=cycles,
            dakuten_map=dakuten,
            timeout_ms=500,
            on_commit=lambda c: self.committed.append(c)
        )

    def test_toggle_cycling(self):
        # 1st tap: あ (new character, is_cycle_advance=False)
        char, adv = self.tracker.tap("あ")
        self.assertEqual(char, "あ")
        self.assertFalse(adv)

        # 2nd tap: い (replace previous, is_cycle_advance=True)
        char, adv = self.tracker.tap("あ")
        self.assertEqual(char, "い")
        self.assertTrue(adv)

        # 3rd tap: う
        char, adv = self.tracker.tap("あ")
        self.assertEqual(char, "う")
        self.assertTrue(adv)

        # 4th tap: え
        char, adv = self.tracker.tap("あ")
        self.assertEqual(char, "え")

        # 5th tap: お
        char, adv = self.tracker.tap("あ")
        self.assertEqual(char, "お")

        # 6th tap: wraps around to あ
        char, adv = self.tracker.tap("あ")
        self.assertEqual(char, "あ")
        self.assertTrue(adv)

    def test_switch_key_commits_previous(self):
        self.tracker.tap("あ")
        # Switch to 'か' -> should commit 'あ'
        char, adv = self.tracker.tap("か")
        self.assertEqual(char, "か")
        self.assertFalse(adv)
        self.assertEqual(self.committed, ["あ"])

    def test_dakuten_conversion(self):
        self.tracker.tap("か")
        # Apply dakuten -> が
        converted = self.tracker.toggle_dakuten()
        self.assertEqual(converted, "が")
        self.assertEqual(self.tracker.last_char, "が")

        # Toggle back -> か
        converted = self.tracker.toggle_dakuten()
        self.assertEqual(converted, "か")
        self.assertEqual(self.tracker.last_char, "か")


class TestXdoEmitter(unittest.TestCase):
    def test_env_display_fallback(self):
        emitter = XdoEmitter(display=":99")
        env = emitter._get_env()
        self.assertEqual(env["DISPLAY"], ":99")


if __name__ == "__main__":
    unittest.main()
