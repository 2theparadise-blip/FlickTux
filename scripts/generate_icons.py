#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/generate_icons.py: Generates all standard Linux icon resolutions
(hicolor 16x16 to 512x512, plus pixmaps) for both:
- flicktux (small, high-clarity icon)
- flicktux_l (large original illustration)
"""

import os
import sys
from PIL import Image, ImageDraw

def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assets_dir = os.path.join(root, "assets")

    src_large = os.path.join(assets_dir, "flicktux_l.png")
    if not os.path.exists(src_large):
        src_large = os.path.join(assets_dir, "icon.png")

    src_small = os.path.join(assets_dir, "flicktux.png")
    if not os.path.exists(src_small):
        src_small = os.path.join(assets_dir, "flicktux_s.png")

    im_l = Image.open(src_large).convert("RGBA")
    im_s = Image.open(src_small).convert("RGBA")

    sizes = [16, 22, 24, 32, 48, 64, 96, 128, 256, 512]

    for sz in sizes:
        dir_path = os.path.join(assets_dir, f"icons/hicolor/{sz}x{sz}/apps")
        os.makedirs(dir_path, exist_ok=True)

        res_s = im_s.resize((sz, sz), Image.Resampling.LANCZOS)
        res_s.save(os.path.join(dir_path, "flicktux.png"), "PNG")

        res_l = im_l.resize((sz, sz), Image.Resampling.LANCZOS)
        res_l.save(os.path.join(dir_path, "flicktux_l.png"), "PNG")

    pixmaps_dir = os.path.join(assets_dir, "pixmaps")
    os.makedirs(pixmaps_dir, exist_ok=True)
    im_s.resize((256, 256), Image.Resampling.LANCZOS).save(os.path.join(pixmaps_dir, "flicktux.png"), "PNG")
    im_l.resize((256, 256), Image.Resampling.LANCZOS).save(os.path.join(pixmaps_dir, "flicktux_l.png"), "PNG")

    print("[scripts/generate_icons.py] Successfully generated all standard icon sizes.")

if __name__ == "__main__":
    main()
