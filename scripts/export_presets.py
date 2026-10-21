#!/usr/bin/env python3
"""Export the Python layouts (flktux/layouts.py) to JSON for the Rust port.

Usage: python3 scripts/export_presets.py
Writes configs/keymaps/presets/*.json and configs/keymaps/common.json.
"""
import importlib.util
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("layouts", os.path.join(ROOT, "flktux", "layouts.py"))
layouts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(layouts)

PRESETS = [
    ("google", "Google", "Google"),
    ("galaxy", "Galaxy", "Galaxy"),
    ("iphone", "iPhone", "iPhone"),
    ("garakei", "ガラケー", "ガラケー"),
    ("tenkey", "10キー", "10キー"),
]
MODES = ["kana", "katakana", "alpha", "number", "nav"]

out_dir = os.path.join(ROOT, "configs", "keymaps", "presets")
os.makedirs(out_dir, exist_ok=True)

for pid, name, py_name in PRESETS:
    modes = {m: layouts.get_layout(py_name, m) for m in MODES}
    rows = len(modes["kana"])
    cols = len(modes["kana"][0])
    for m, grid in modes.items():
        assert len(grid) == rows and all(len(r) == cols for r in grid), (pid, m)
    with open(os.path.join(out_dir, f"{pid}.json"), "w", encoding="utf-8") as f:
        json.dump({"id": pid, "name": name, "rows": rows, "cols": cols, "modes": modes},
                  f, ensure_ascii=False, indent=1)

# Fix a typo in the Python table: 'ほ' appeared twice, so ぼ->ぽ was lost.
dak = dict(layouts.DAKUTEN_MAP)
dak.update({"ほ": "ぼ", "ぼ": "ぽ", "ぽ": "ほ"})

with open(os.path.join(ROOT, "configs", "keymaps", "common.json"), "w", encoding="utf-8") as f:
    json.dump({"toggle_cycles": layouts.TOGGLE_CYCLES, "dakuten_map": dak},
              f, ensure_ascii=False, indent=1)
print("exported:", [p[0] for p in PRESETS])
