#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
flktux.layouts: Multi-Mode Japanese (Hiragana / Katakana) & Alphabet & Number Layouts
Supports:
- Google (Gboard), Galaxy, iPhone, ガラケー, and 10キー (7:あ, 8:か, 9:さ...)
- 4 Modes for each layout:
    1. 'kana'     : ひらがな (あ, か, さ...)
    2. 'katakana' : カタカナ (ア, カ, サ...)
    3. 'alpha'    : 英語・アルファベット (abc, def, ghi... 大文字/小文字対応)
    4. 'number'   : 数字 (1, 2, 3...)
"""

# =============================================================================
# Flick Definitions
# =============================================================================

# 1. Hiragana (かな)
KANA_FLICKS = {
    'あ': {'center': 'あ', 'left': 'い', 'up': 'う', 'right': 'え', 'down': 'お'},
    'か': {'center': 'か', 'left': 'き', 'up': 'く', 'right': 'け', 'down': 'こ'},
    'さ': {'center': 'さ', 'left': 'し', 'up': 'す', 'right': 'せ', 'down': 'そ'},
    'た': {'center': 'た', 'left': 'ち', 'up': 'つ', 'right': 'て', 'down': 'と'},
    'な': {'center': 'な', 'left': 'に', 'up': 'ぬ', 'right': 'ね', 'down': 'の'},
    'は': {'center': 'は', 'left': 'ひ', 'up': 'ふ', 'right': 'へ', 'down': 'ほ'},
    'ま': {'center': 'ま', 'left': 'み', 'up': 'む', 'right': 'め', 'down': 'も'},
    'ら': {'center': 'ら', 'left': 'り', 'up': 'る', 'right': 'れ', 'down': 'ろ'},
    'わ': {'center': 'わ', 'left': 'を', 'up': 'ん', 'right': 'ー', 'down': '〜'},
    '、。': {'center': '、', 'left': '。', 'up': '？', 'right': '！', 'down': '…'},
}

YA_ANDROID = {'center': 'や', 'left': '（', 'up': 'ゆ', 'right': '）', 'down': 'よ'}
YA_IPHONE  = {'center': 'や', 'left': '「', 'up': 'ゆ', 'right': '」', 'down': 'よ'}

# 2. Katakana (カナ)
KATAKANA_FLICKS = {
    'ア': {'center': 'ア', 'left': 'イ', 'up': 'ウ', 'right': 'エ', 'down': 'オ'},
    'カ': {'center': 'カ', 'left': 'キ', 'up': 'ク', 'right': 'ケ', 'down': 'コ'},
    'サ': {'center': 'サ', 'left': 'シ', 'up': 'ス', 'right': 'セ', 'down': 'ソ'},
    'タ': {'center': 'タ', 'left': 'チ', 'up': 'ツ', 'right': 'テ', 'down': 'ト'},
    'ナ': {'center': 'ナ', 'left': 'ニ', 'up': 'ヌ', 'right': 'ネ', 'down': 'ノ'},
    'ハ': {'center': 'ハ', 'left': 'ヒ', 'up': 'フ', 'right': 'ヘ', 'down': 'ホ'},
    'マ': {'center': 'マ', 'left': 'ミ', 'up': 'ム', 'right': 'メ', 'down': 'モ'},
    'ヤ': {'center': 'ヤ', 'left': '（', 'up': 'ユ', 'right': '）', 'down': 'ヨ'},
    'ラ': {'center': 'ラ', 'left': 'リ', 'up': 'ル', 'right': 'レ', 'down': 'ロ'},
    'ワ': {'center': 'ワ', 'left': 'ヲ', 'up': 'ン', 'right': 'ー', 'down': '〜'},
    '、。': {'center': '、', 'left': '。', 'up': '？', 'right': '！', 'down': '…'},
}

# 3. Alphabet / English (英字フリック)
ALPHA_FLICKS = {
    '@':    {'center': '@', 'left': '#', 'up': '/', 'right': '&', 'down': '_'},
    'abc':  {'center': 'a', 'left': 'b', 'up': 'c', 'right': '2'},
    'def':  {'center': 'd', 'left': 'e', 'up': 'f', 'right': '3'},
    'ghi':  {'center': 'g', 'left': 'h', 'up': 'i', 'right': '4'},
    'jkl':  {'center': 'j', 'left': 'k', 'up': 'l', 'right': '5'},
    'mno':  {'center': 'm', 'left': 'n', 'up': 'o', 'right': '6'},
    'pqrs': {'center': 'p', 'left': 'q', 'up': 'r', 'right': 's', 'down': '7'},
    'tuv':  {'center': 't', 'left': 'u', 'up': 'v', 'right': '8'},
    'wxyz': {'center': 'w', 'left': 'x', 'up': 'y', 'right': 'z', 'down': '9'},
    '.,?!': {'center': '.', 'left': ',', 'up': '?', 'right': '!', 'down': '-'},
    '@._/': {'center': '@', 'left': '.', 'up': '_', 'right': '-', 'down': '/'},
    '␣':    {'center': ' ', 'left': '\t', 'up': '\n', 'right': ' ', 'down': ' '},
}

# 4. Numbers (数字)
NUMBER_FLICKS = {
    '1': {'center': '1', 'left': '(', 'up': ')', 'right': '$', 'down': '%'},
    '2': {'center': '2', 'left': 'A', 'up': 'B', 'right': 'C'},
    '3': {'center': '3', 'left': 'D', 'up': 'E', 'right': 'F'},
    '4': {'center': '4', 'left': 'G', 'up': 'H', 'right': 'I'},
    '5': {'center': '5', 'left': 'J', 'up': 'K', 'right': 'L'},
    '6': {'center': '6', 'left': 'M', 'up': 'N', 'right': 'O'},
    '7': {'center': '7', 'left': 'P', 'up': 'Q', 'right': 'R', 'down': 'S'},
    '8': {'center': '8', 'left': 'T', 'up': 'U', 'right': 'V'},
    '9': {'center': '9', 'left': 'W', 'up': 'X', 'right': 'Y', 'down': 'Z'},
    '0': {'center': '0', 'left': '+', 'up': '-', 'right': '*', 'down': '/'},
}


# =============================================================================
# Layout Generators
# =============================================================================

def get_layout(layout_name: str, mode: str = "kana"):
    """指定のレイアウト名と入力モード (kana / katakana / alpha / number) に応じた
    5x4 / 4x5 のマトリックスを生成して返す"""

    mode_label = {
        "kana": "あ",
        "katakana": "ア",
        "alpha": "A",
        "number": "1",
        "nav": "↑"
    }.get(mode, "あ")

    # -------------------------------------------------------------------------
    # 5. 10-Key Numpad Layout (5 rows x 4 columns)
    # 7, 8, 9 / 4, 5, 6 / 1, 2, 3 / 0
    # -------------------------------------------------------------------------
    if layout_name == "10キー":
        if mode == "nav":
            return [
                [{"type": "action", "label": "Esc", "num": "/", "action": "esc", "style": "action-cell"},
                 {"type": "action", "label": "Home", "num": "←", "action": "home", "style": "action-cell"},
                 {"type": "action", "label": "End", "num": "→", "action": "end", "style": "action-cell"},
                 {"type": "action", "label": "⌫", "num": "BS", "action": "backspace", "style": "action-cell"}],
                [{"type": "action", "label": "Tab", "num": "7", "action": "tab", "style": "action-cell"},
                 {"type": "action", "label": "▲ 上", "num": "8", "action": "up", "style": "action-cell"},
                 {"type": "action", "label": "S-Tab", "num": "9", "action": "shift_tab", "style": "action-cell"},
                 {"type": "action", "label": "PgUp", "num": "-", "action": "page_up", "style": "action-cell"}],
                [{"type": "action", "label": "◀ 左", "num": "4", "action": "left", "style": "action-cell"},
                 {"type": "action", "label": "決定", "num": "5", "action": "enter", "style": "action-cell"},
                 {"type": "action", "label": "▶ 右", "num": "6", "action": "right", "style": "action-cell"},
                 {"type": "action", "label": "PgDn", "num": "変", "action": "page_down", "style": "action-cell"}],
                [{"type": "action", "label": "Shift", "num": "1", "action": "shift", "style": "action-cell"},
                 {"type": "action", "label": "▼ 下", "num": "2", "action": "down", "style": "action-cell"},
                 {"type": "action", "label": "Ctrl", "num": "3", "action": "ctrl", "style": "action-cell"},
                 {"type": "action", "label": "次へ", "num": "+", "action": "next", "style": "action-cell"}],
                [{"type": "action", "label": "Space", "num": "0", "action": "space", "style": "action-cell"},
                 {"type": "action", "label": "Del", "num": ".", "action": "delete", "style": "action-cell"},
                 {"type": "action", "label": mode_label, "num": "切替", "action": "mode", "style": "action-cell"},
                 {"type": "action", "label": "確定", "num": "Ent", "action": "enter", "style": "enter-cell"}],
            ]

        if mode == "katakana":
            k7, k8, k9 = "ア", "カ", "サ"
            k4, k5, k6 = "タ", "ナ", "ハ"
            k1, k2, k3 = "マ", "ヤ", "ラ"
            k0, kdot, kdak = "ワ", "、。", "゛゜小"
            fd_map = KATAKANA_FLICKS
        elif mode == "alpha":
            k7, k8, k9 = "abc", "def", "ghi"
            k4, k5, k6 = "jkl", "mno", "pqrs"
            k1, k2, k3 = "tuv", "wxyz", "@._/"
            k0, kdot, kdak = "␣", ".,?!", "a/A"
            fd_map = ALPHA_FLICKS
        elif mode == "number":
            k7, k8, k9 = "7", "8", "9"
            k4, k5, k6 = "4", "5", "6"
            k1, k2, k3 = "1", "2", "3"
            k0, kdot, kdak = "0", ".", "+/-"
            fd_map = NUMBER_FLICKS
        else: # kana
            k7, k8, k9 = "あ", "か", "さ"
            k4, k5, k6 = "た", "な", "は"
            k1, k2, k3 = "ま", "や", "ら"
            k0, kdot, kdak = "わ", "、。", "゛゜小"
            fd_map = KANA_FLICKS

        return [
            [{"type": "action", "label": "記号", "num": "/", "action": "symbol", "style": "action-cell"},
             {"type": "action", "label": "◀", "num": "←", "action": "left", "style": "action-cell"},
             {"type": "action", "label": "▶", "num": "→", "action": "right", "style": "action-cell"},
             {"type": "action", "label": "⌫", "num": "BS", "action": "backspace", "style": "action-cell"}],
            [{"type": "flick", "key": k7, "num": "7", "flick_data": fd_map.get(k7)},
             {"type": "flick", "key": k8, "num": "8", "flick_data": fd_map.get(k8)},
             {"type": "flick", "key": k9, "num": "9", "flick_data": fd_map.get(k9)},
             {"type": "action", "label": "空白", "num": "-", "action": "space", "style": "action-cell"}],
            [{"type": "flick", "key": k4, "num": "4", "flick_data": fd_map.get(k4)},
             {"type": "flick", "key": k5, "num": "5", "flick_data": fd_map.get(k5)},
             {"type": "flick", "key": k6, "num": "6", "flick_data": fd_map.get(k6)},
             {"type": "action", "label": "変換", "num": "変", "action": "convert", "style": "action-cell"}],
            [{"type": "flick", "key": k1, "num": "1", "flick_data": fd_map.get(k1)},
             {"type": "flick", "key": k2, "num": "2", "flick_data": fd_map.get(k2)},
             {"type": "flick", "key": k3, "num": "3", "flick_data": fd_map.get(k3)},
             {"type": "action", "label": "次へ", "num": "+", "action": "next", "style": "action-cell"}],
            [{"type": "flick", "key": k0, "num": "0", "flick_data": fd_map.get(k0)},
             {"type": "action", "label": mode_label, "num": "切替", "action": "mode", "style": "action-cell"},
             {"type": "flick", "key": ".", "num": ".", "flick_data": fd_map.get(kdot)},
             {"type": "action", "label": "確定", "num": "Ent", "action": "enter", "style": "enter-cell"}],
        ]

    # -------------------------------------------------------------------------
    # 6. プッシュボタン (電話式 12キー / 4 rows x 3 columns)
    # 1, 2, 3 / 4, 5, 6 / 7, 8, 9 / *, 0, #
    # -------------------------------------------------------------------------
    if layout_name in ("プッシュボタン", "push_phone", "12キー"):
        if mode == "nav":
            return [
                [{"type": "action", "label": "Esc", "num": "1", "action": "esc", "style": "action-cell"},
                 {"type": "action", "label": "▲ 上", "num": "2", "action": "up", "style": "action-cell"},
                 {"type": "action", "label": "⌫", "num": "3", "action": "backspace", "style": "action-cell"}],
                [{"type": "action", "label": "◀ 左", "num": "4", "action": "left", "style": "action-cell"},
                 {"type": "action", "label": "決定", "num": "5", "action": "enter", "style": "action-cell"},
                 {"type": "action", "label": "▶ 右", "num": "6", "action": "right", "style": "action-cell"}],
                [{"type": "action", "label": "Tab", "num": "7", "action": "tab", "style": "action-cell"},
                 {"type": "action", "label": "▼ 下", "num": "8", "action": "down", "style": "action-cell"},
                 {"type": "action", "label": "Space", "num": "9", "action": "space", "style": "action-cell"}],
                [{"type": "action", "label": mode_label, "num": "*", "action": "mode", "style": "action-cell"},
                 {"type": "action", "label": "変換", "num": "0", "action": "convert", "style": "action-cell"},
                 {"type": "action", "label": "確定", "num": "#", "action": "enter", "style": "enter-cell"}],
            ]

        if mode == "katakana":
            p0, p1, p2 = "ア", "カ", "サ"
            p3, p4, p5 = "タ", "ナ", "ハ"
            p6, p7, p8 = "マ", "ヤ", "ラ"
            p9, pdot   = "ワ", "、。"
            pfd_map = KATAKANA_FLICKS
            pya_fd = KATAKANA_FLICKS['ヤ']
            pdak_label = "゛゜小"
        elif mode == "alpha":
            p0, p1, p2 = "@", "abc", "def"
            p3, p4, p5 = "ghi", "jkl", "mno"
            p6, p7, p8 = "pqrs", "tuv", "wxyz"
            p9, pdot   = "␣", ".,?!"
            pfd_map = ALPHA_FLICKS
            pya_fd = ALPHA_FLICKS['tuv']
            pdak_label = "a/A"
        elif mode == "number":
            p0, p1, p2 = "1", "2", "3"
            p3, p4, p5 = "4", "5", "6"
            p6, p7, p8 = "7", "8", "9"
            p9, pdot   = "0", "."
            pfd_map = NUMBER_FLICKS
            pya_fd = NUMBER_FLICKS['8']
            pdak_label = "+/-"
        else: # kana
            p0, p1, p2 = "あ", "か", "さ"
            p3, p4, p5 = "た", "な", "は"
            p6, p7, p8 = "ま", "や", "ら"
            p9, pdot   = "わ", "、。"
            pfd_map = KANA_FLICKS
            pya_fd = YA_ANDROID
            pdak_label = "゛゜小"

        return [
            [{"type": "flick", "key": p0, "num": "1", "flick_data": pfd_map.get(p0)},
             {"type": "flick", "key": p1, "num": "2", "flick_data": pfd_map.get(p1)},
             {"type": "flick", "key": p2, "num": "3", "flick_data": pfd_map.get(p2)}],
            [{"type": "flick", "key": p3, "num": "4", "flick_data": pfd_map.get(p3)},
             {"type": "flick", "key": p4, "num": "5", "flick_data": pfd_map.get(p4)},
             {"type": "flick", "key": p5, "num": "6", "flick_data": pfd_map.get(p5)}],
            [{"type": "flick", "key": p6, "num": "7", "flick_data": pfd_map.get(p6)},
             {"type": "flick", "key": p7, "num": "8", "flick_data": pya_fd},
             {"type": "flick", "key": p8, "num": "9", "flick_data": pfd_map.get(p8)}],
            [{"type": "action", "label": pdak_label, "num": "*", "action": "dakuten", "style": "action-cell"},
             {"type": "flick", "key": p9, "num": "0", "flick_data": pfd_map.get(p9)},
             {"type": "action", "label": "確定", "num": "#", "action": "enter", "style": "enter-cell"}],
        ]

    # -------------------------------------------------------------------------
    # 1. Google / 2. Galaxy / 3. iPhone / 4. ガラケー (4 rows x 5 columns)
    # -------------------------------------------------------------------------
    if mode == "nav":
        if layout_name == "iPhone":
            return [
                [{"type": "action", "label": "☆123", "action": "number", "style": "action-cell"},
                 {"type": "action", "label": "Home", "action": "home", "style": "action-cell"},
                 {"type": "action", "label": "▲ 上", "action": "up", "style": "action-cell"},
                 {"type": "action", "label": "End", "action": "end", "style": "action-cell"},
                 {"type": "action", "label": "⌫", "action": "backspace", "style": "action-cell"}],
                [{"type": "action", "label": "ABC", "action": "alpha", "style": "action-cell"},
                 {"type": "action", "label": "◀ 左", "action": "left", "style": "action-cell"},
                 {"type": "action", "label": "決定", "action": "enter", "style": "action-cell"},
                 {"type": "action", "label": "▶ 右", "action": "right", "style": "action-cell"},
                 {"type": "action", "label": "Space", "action": "space", "style": "action-cell"}],
                [{"type": "action", "label": "Shift", "action": "shift", "style": "action-cell"},
                 {"type": "action", "label": "Ctrl", "action": "ctrl", "style": "action-cell"},
                 {"type": "action", "label": "▼ 下", "action": "down", "style": "action-cell"},
                 {"type": "action", "label": "Tab", "action": "tab", "style": "action-cell"},
                 {"type": "action", "label": "確定", "action": "enter", "style": "enter-cell", "rowSpan": 2}],
                [{"type": "action", "label": "🌐", "action": "mode", "style": "action-cell"},
                 {"type": "action", "label": "Del", "action": "delete", "style": "action-cell"},
                 {"type": "action", "label": "S-Tab", "action": "shift_tab", "style": "action-cell"},
                 {"type": "action", "label": "Esc", "action": "esc", "style": "action-cell"},
                 {"type": "action", "label": "確定", "action": "enter", "style": "enter-cell"}],
            ]
        elif layout_name == "Galaxy":
            return [
                [{"type": "action", "label": mode_label, "action": "mode", "style": "action-cell"},
                 {"type": "action", "label": "Home", "action": "home", "style": "action-cell"},
                 {"type": "action", "label": "▲ 上", "action": "up", "style": "action-cell"},
                 {"type": "action", "label": "End", "action": "end", "style": "action-cell"},
                 {"type": "action", "label": "⌫", "action": "backspace", "style": "action-cell"}],
                [{"type": "action", "label": "数字", "action": "number", "style": "action-cell"},
                 {"type": "action", "label": "Tab", "action": "tab", "style": "action-cell"},
                 {"type": "action", "label": "決定", "action": "enter", "style": "action-cell"},
                 {"type": "action", "label": "S-Tab", "action": "shift_tab", "style": "action-cell"},
                 {"type": "action", "label": "◀ 左", "action": "left", "style": "action-cell"}],
                [{"type": "action", "label": "記号", "action": "symbol", "style": "action-cell"},
                 {"type": "action", "label": "Ctrl", "action": "ctrl", "style": "action-cell"},
                 {"type": "action", "label": "▼ 下", "action": "down", "style": "action-cell"},
                 {"type": "action", "label": "Shift", "action": "shift", "style": "action-cell"},
                 {"type": "action", "label": "▶ 右", "action": "right", "style": "action-cell"}],
                [{"type": "action", "label": "Space", "action": "space", "style": "action-cell"},
                 {"type": "action", "label": "Del", "action": "delete", "style": "action-cell"},
                 {"type": "action", "label": "Esc", "action": "esc", "style": "action-cell"},
                 {"type": "action", "label": "次へ", "action": "next", "style": "action-cell"},
                 {"type": "action", "label": "確定", "action": "enter", "style": "enter-cell"}],
            ]
        else: # Google / Garakei
            return [
                [{"type": "action", "label": mode_label, "action": "mode", "style": "action-cell"},
                 {"type": "action", "label": "Home", "action": "home", "style": "action-cell"},
                 {"type": "action", "label": "▲ 上", "action": "up", "style": "action-cell"},
                 {"type": "action", "label": "End", "action": "end", "style": "action-cell"},
                 {"type": "action", "label": "⌫", "action": "backspace", "style": "action-cell"}],
                [{"type": "action", "label": "◀ 左", "action": "left", "style": "action-cell"},
                 {"type": "action", "label": "Tab", "action": "tab", "style": "action-cell"},
                 {"type": "action", "label": "決定", "action": "enter", "style": "action-cell"},
                 {"type": "action", "label": "S-Tab", "action": "shift_tab", "style": "action-cell"},
                 {"type": "action", "label": "Space", "action": "space", "style": "action-cell"}],
                [{"type": "action", "label": "▶ 右", "action": "right", "style": "action-cell"},
                 {"type": "action", "label": "Ctrl", "action": "ctrl", "style": "action-cell"},
                 {"type": "action", "label": "▼ 下", "action": "down", "style": "action-cell"},
                 {"type": "action", "label": "Shift", "action": "shift", "style": "action-cell"},
                 {"type": "action", "label": "変換", "action": "convert", "style": "action-cell"}],
                [{"type": "action", "label": "記号", "action": "symbol", "style": "action-cell"},
                 {"type": "action", "label": "Del", "action": "delete", "style": "action-cell"},
                 {"type": "action", "label": "Esc", "action": "esc", "style": "action-cell"},
                 {"type": "action", "label": "次へ", "action": "next", "style": "action-cell"},
                 {"type": "action", "label": "確定", "action": "enter", "style": "enter-cell"}],
            ]

    if mode == "katakana":
        c0, c1, c2 = "ア", "カ", "サ"
        c3, c4, c5 = "タ", "ナ", "ハ"
        c6, c7, c8 = "マ", "ヤ", "ラ"
        c9, cdot   = "ワ", "、。"
        fd_map = KATAKANA_FLICKS
        ya_fd = KATAKANA_FLICKS['ヤ']
        dak_label = "゛゜小"
    elif mode == "alpha":
        c0, c1, c2 = "@", "abc", "def"
        c3, c4, c5 = "ghi", "jkl", "mno"
        c6, c7, c8 = "pqrs", "tuv", "wxyz"
        c9, cdot   = "␣", ".,?!"
        fd_map = ALPHA_FLICKS
        ya_fd = ALPHA_FLICKS['tuv']
        dak_label = "a/A"
    elif mode == "number":
        c0, c1, c2 = "1", "2", "3"
        c3, c4, c5 = "4", "5", "6"
        c6, c7, c8 = "7", "8", "9"
        c9, cdot   = "0", "."
        fd_map = NUMBER_FLICKS
        ya_fd = NUMBER_FLICKS['8']
        dak_label = "+/-"
    else: # kana
        c0, c1, c2 = "あ", "か", "さ"
        c3, c4, c5 = "た", "な", "は"
        c6, c7, c8 = "ま", "や", "ら"
        c9, cdot   = "わ", "、。"
        fd_map = KANA_FLICKS
        ya_fd = YA_IPHONE if layout_name == "iPhone" else YA_ANDROID
        dak_label = "゛゜小"

    if layout_name == "Galaxy":
        # Galaxy (Samsung 日本語テンキー):
        # 左列: mode_label, 数字, 記号, 空白
        # 右列: ⌫, ◀, ▶, 確定
        return [
            [{"type": "action", "label": mode_label, "action": "mode", "style": "action-cell"},
             {"type": "flick", "key": c0, "flick_data": fd_map.get(c0)},
             {"type": "flick", "key": c1, "flick_data": fd_map.get(c1)},
             {"type": "flick", "key": c2, "flick_data": fd_map.get(c2)},
             {"type": "action", "label": "⌫", "action": "backspace", "style": "action-cell"}],
            [{"type": "action", "label": "数字", "action": "number", "style": "action-cell"},
             {"type": "flick", "key": c3, "flick_data": fd_map.get(c3)},
             {"type": "flick", "key": c4, "flick_data": fd_map.get(c4)},
             {"type": "flick", "key": c5, "flick_data": fd_map.get(c5)},
             {"type": "action", "label": "◀", "action": "left", "style": "action-cell"}],
            [{"type": "action", "label": "記号", "action": "symbol", "style": "action-cell"},
             {"type": "flick", "key": c6, "flick_data": fd_map.get(c6)},
             {"type": "flick", "key": c7, "flick_data": ya_fd},
             {"type": "flick", "key": c8, "flick_data": fd_map.get(c8)},
             {"type": "action", "label": "▶", "action": "right", "style": "action-cell"}],
            [{"type": "action", "label": "空白", "action": "space", "style": "action-cell"},
             {"type": "action", "label": dak_label, "action": "dakuten", "style": "action-cell"},
             {"type": "flick", "key": c9, "flick_data": fd_map.get(c9)},
             {"type": "flick", "key": cdot, "flick_data": fd_map.get(cdot)},
             {"type": "action", "label": "確定", "action": "enter", "style": "enter-cell"}],
        ]
    elif layout_name == "iPhone":
        # iPhone (iOS 日本語かなフリック):
        # 左列: ☆123, ABC, 小 ゛゜, 🌐
        # 右列: ⌫, 空白, 改行 (rowSpan: 2)
        # 中央下段: 空き, わ, 、。？！
        return [
            [{"type": "action", "label": "☆123", "action": "number", "style": "action-cell"},
             {"type": "flick", "key": c0, "flick_data": fd_map.get(c0)},
             {"type": "flick", "key": c1, "flick_data": fd_map.get(c1)},
             {"type": "flick", "key": c2, "flick_data": fd_map.get(c2)},
             {"type": "action", "label": "⌫", "action": "backspace", "style": "action-cell"}],
            [{"type": "action", "label": "ABC", "action": "alpha", "style": "action-cell"},
             {"type": "flick", "key": c3, "flick_data": fd_map.get(c3)},
             {"type": "flick", "key": c4, "flick_data": fd_map.get(c4)},
             {"type": "flick", "key": c5, "flick_data": fd_map.get(c5)},
             {"type": "action", "label": "空白", "action": "space", "style": "action-cell"}],
            [{"type": "action", "label": "小 ゛゜" if mode == "kana" else dak_label, "action": "dakuten", "style": "action-cell"},
             {"type": "flick", "key": c6, "flick_data": fd_map.get(c6)},
             {"type": "flick", "key": c7, "flick_data": ya_fd},
             {"type": "flick", "key": c8, "flick_data": fd_map.get(c8)},
             {"type": "action", "label": "改行", "action": "enter", "style": "enter-cell", "rowSpan": 2}],
            [{"type": "action", "label": "🌐", "action": "mode", "style": "action-cell"},
             {"type": "action", "label": "マイク", "action": "space", "style": "action-cell"},
             {"type": "flick", "key": c9, "flick_data": fd_map.get(c9)},
             {"type": "flick", "key": cdot, "flick_data": fd_map.get(cdot)},
             {"type": "action", "label": "改行", "action": "enter", "style": "enter-cell"}],
        ]
    elif layout_name == "ガラケー":
        return [
            [{"type": "action", "label": "クリア", "action": "backspace", "style": "action-cell"},
             {"type": "flick", "key": c0, "num": "1", "flick_data": fd_map.get(c0)},
             {"type": "flick", "key": c1, "num": "2", "flick_data": fd_map.get(c1)},
             {"type": "flick", "key": c2, "num": "3", "flick_data": fd_map.get(c2)},
             {"type": "action", "label": "確定", "action": "enter", "style": "enter-cell"}],
            [{"type": "action", "label": "◀", "action": "left", "style": "action-cell"},
             {"type": "flick", "key": c3, "num": "4", "flick_data": fd_map.get(c3)},
             {"type": "flick", "key": c4, "num": "5", "flick_data": fd_map.get(c4)},
             {"type": "flick", "key": c5, "num": "6", "flick_data": fd_map.get(c5)},
             {"type": "action", "label": "▶", "action": "right", "style": "action-cell"}],
            [{"type": "action", "label": mode_label, "action": "mode", "style": "action-cell"},
             {"type": "flick", "key": c6, "num": "7", "flick_data": fd_map.get(c6)},
             {"type": "flick", "key": c7, "num": "8", "flick_data": ya_fd},
             {"type": "flick", "key": c8, "num": "9", "flick_data": fd_map.get(c8)},
             {"type": "action", "label": "空白", "action": "space", "style": "action-cell"}],
            [{"type": "action", "label": "変換", "action": "convert", "style": "action-cell"},
             {"type": "action", "label": dak_label, "action": "dakuten", "num": "*", "style": "action-cell"},
             {"type": "flick", "key": c9, "num": "0", "flick_data": fd_map.get(c9)},
             {"type": "flick", "key": cdot, "num": "#", "flick_data": fd_map.get(cdot)},
             {"type": "action", "label": "次へ", "action": "next", "style": "action-cell"}],
        ]
    else: # Google (Gboard 日本語 12キー)
        # 実機 Gboard 配置:
        # 左列: mode_label, ◀, ▶, 記号
        # 右列: ⌫, 空白, 変換, 確定
        # 中央下段: ゛゜小, わ, 、。
        return [
            [{"type": "action", "label": mode_label, "action": "mode", "style": "action-cell"},
             {"type": "flick", "key": c0, "flick_data": fd_map.get(c0)},
             {"type": "flick", "key": c1, "flick_data": fd_map.get(c1)},
             {"type": "flick", "key": c2, "flick_data": fd_map.get(c2)},
             {"type": "action", "label": "⌫", "action": "backspace", "style": "action-cell"}],
            [{"type": "action", "label": "◀", "action": "left", "style": "action-cell"},
             {"type": "flick", "key": c3, "flick_data": fd_map.get(c3)},
             {"type": "flick", "key": c4, "flick_data": fd_map.get(c4)},
             {"type": "flick", "key": c5, "flick_data": fd_map.get(c5)},
             {"type": "action", "label": "空白", "action": "space", "style": "action-cell"}],
            [{"type": "action", "label": "▶", "action": "right", "style": "action-cell"},
             {"type": "flick", "key": c6, "flick_data": fd_map.get(c6)},
             {"type": "flick", "key": c7, "flick_data": ya_fd},
             {"type": "flick", "key": c8, "flick_data": fd_map.get(c8)},
             {"type": "action", "label": "変換", "action": "convert", "style": "action-cell"}],
            [{"type": "action", "label": "記号", "action": "symbol", "style": "action-cell"},
             {"type": "action", "label": dak_label, "action": "dakuten", "style": "action-cell"},
             {"type": "flick", "key": c9, "flick_data": fd_map.get(c9)},
             {"type": "flick", "key": cdot, "flick_data": fd_map.get(cdot)},
             {"type": "action", "label": "確定", "action": "enter", "style": "enter-cell"}],
        ]


# Base dictionary for backward compatibility
LAYOUTS = {
    "Google": get_layout("Google", "kana"),
    "Galaxy": get_layout("Galaxy", "kana"),
    "iPhone": get_layout("iPhone", "kana"),
    "ガラケー": get_layout("ガラケー", "kana"),
    "10キー": get_layout("10キー", "kana"),
    "プッシュボタン": get_layout("プッシュボタン", "kana"),
}


# =============================================================================
# Toggle Cycles (Keypad Tap Typing)
# =============================================================================

TOGGLE_CYCLES = {
    # Hiragana
    'あ': ['あ', 'い', 'う', 'え', 'お'],
    'か': ['か', 'き', 'く', 'け', 'こ'],
    'さ': ['さ', 'し', 'す', 'せ', 'そ'],
    'た': ['た', 'ち', 'つ', 'て', 'と'],
    'な': ['な', 'に', 'ぬ', 'ね', 'の'],
    'は': ['は', 'ひ', 'ふ', 'へ', 'ほ'],
    'ま': ['ま', 'み', 'む', 'め', 'も'],
    'や': ['や', 'ゆ', 'よ', '（', '）'],
    'ら': ['ら', 'り', 'る', 'れ', 'ろ'],
    'わ': ['わ', 'を', 'ん', 'ー', '〜'],
    '、。': ['、', '。', '？', '！', '…'],

    # Katakana
    'ア': ['ア', 'イ', 'ウ', 'エ', 'オ'],
    'カ': ['カ', 'キ', 'ク', 'ケ', 'コ'],
    'サ': ['サ', 'シ', 'ス', 'セ', 'ソ'],
    'タ': ['タ', 'チ', 'ツ', 'テ', 'ト'],
    'ナ': ['ナ', 'ニ', 'ヌ', 'ネ', 'ノ'],
    'ハ': ['ハ', 'ヒ', 'フ', 'ヘ', 'ホ'],
    'マ': ['マ', 'ミ', 'ム', 'メ', 'モ'],
    'ヤ': ['ヤ', 'ユ', 'ヨ', '（', '）'],
    'ラ': ['ラ', 'リ', 'ル', 'レ', 'ロ'],
    'ワ': ['ワ', 'ヲ', 'ン', 'ー', '〜'],

    # English / Alphabet
    '@':    ['@', '#', '/', '&', '_'],
    'abc':  ['a', 'b', 'c'],
    'def':  ['d', 'e', 'f'],
    'ghi':  ['g', 'h', 'i'],
    'jkl':  ['j', 'k', 'l'],
    'mno':  ['m', 'n', 'o'],
    'pqrs': ['p', 'q', 'r', 's'],
    'tuv':  ['t', 'u', 'v'],
    'wxyz': ['w', 'x', 'y', 'z'],
    '.,?!': ['.', ',', '?', '!', '-'],
    '@._/': ['@', '.', '_', '-', '/'],
    '␣':    [' ', '\t'],

    # Numbers
    '1': ['1'], '2': ['2'], '3': ['3'],
    '4': ['4'], '5': ['5'], '6': ['6'],
    '7': ['7'], '8': ['8'], '9': ['9'],
    '0': ['0'], '.': ['.'],
}


# =============================================================================
# Dakuten / Handakuten / Small letter / Uppercase-Lowercase Cycles
# =============================================================================

DAKUTEN_MAP = {
    # Hiragana
    'あ': 'ぁ', 'ぁ': 'あ',
    'い': 'ぃ', 'ぃ': 'い',
    'う': 'ぅ', 'ぅ': 'ゔ', 'ゔ': 'う',
    'え': 'ぇ', 'ぇ': 'え',
    'お': 'ぉ', 'ぉ': 'お',
    'か': 'が', 'が': 'か',
    'き': 'ぎ', 'ぎ': 'き',
    'く': 'ぐ', 'ぐ': 'く',
    'け': 'げ', 'げ': 'け',
    'こ': 'ご', 'ご': 'こ',
    'さ': 'ざ', 'ざ': 'さ',
    'し': 'じ', 'じ': 'し',
    'す': 'ず', 'ず': 'す',
    'せ': 'ぜ', 'ぜ': 'せ',
    'そ': 'ぞ', 'ぞ': 'そ',
    'た': 'だ', 'だ': 'た',
    'ち': 'ぢ', 'ぢ': 'ち',
    'つ': 'っ', 'っ': 'づ', 'づ': 'つ',
    'て': 'で', 'で': 'て',
    'と': 'ど', 'ど': 'と',
    'は': 'ば', 'ば': 'ぱ', 'ぱ': 'は',
    'ひ': 'び', 'び': 'ぴ', 'ぴ': 'ひ',
    'ふ': 'ぶ', 'ぶ': 'ぷ', 'ぷ': 'ふ',
    'へ': 'べ', 'べ': 'ぺ', 'ぺ': 'へ',
    'ほ': 'ぼ', 'ほ': 'ぽ', 'ぽ': 'ほ',
    'や': 'ゃ', 'ゃ': 'や',
    'ゆ': 'ゅ', 'ゅ': 'ゆ',
    'よ': 'ょ', 'ょ': 'よ',
    'わ': 'ゎ', 'ゎ': 'わ',

    # Katakana
    'ア': 'ァ', 'ァ': 'ア',
    'イ': 'ィ', 'ィ': 'イ',
    'ウ': 'ゥ', 'ゥ': 'ヴ', 'ヴ': 'ウ',
    'エ': 'ェ', 'ェ': 'エ',
    'オ': 'ォ', 'ォ': 'オ',
    'カ': 'ガ', 'ガ': 'カ',
    'キ': 'ギ', 'ギ': 'キ',
    'ク': 'グ', 'グ': 'ク',
    'ケ': 'ゲ', 'ゲ': 'ケ',
    'コ': 'ゴ', 'ゴ': 'コ',
    'サ': 'ザ', 'ザ': 'サ',
    'シ': 'ジ', 'ジ': 'シ',
    'ス': 'ズ', 'ズ': 'ス',
    'セ': 'ゼ', 'ゼ': 'セ',
    'ソ': 'ゾ', 'ゾ': 'ソ',
    'タ': 'ダ', 'ダ': 'タ',
    'チ': 'ヂ', 'ヂ': 'チ',
    'ツ': 'ッ', 'ッ': 'ヅ', 'ヅ': 'ツ',
    'テ': 'デ', 'デ': 'テ',
    'ト': 'ド', 'ド': 'ト',
    'ハ': 'バ', 'バ': 'パ', 'パ': 'ハ',
    'ヒ': 'ビ', 'ビ': 'ピ', 'ピ': 'ヒ',
    'フ': 'ブ', 'ブ': 'プ', 'プ': 'フ',
    'ヘ': 'ベ', 'ベ': 'ペ', 'ペ': 'ヘ',
    'ホ': 'ボ', 'ボ': 'ポ', 'ポ': 'ホ',
    'ヤ': 'ャ', 'ャ': 'ヤ',
    'ユ': 'ュ', 'ュ': 'ユ',
    'ヨ': 'ョ', 'ョ': 'ヨ',
    'ワ': 'ヮ', 'ヮ': 'ワ',

    # Alphabet Lowercase <-> Uppercase toggle
    'a': 'A', 'A': 'a', 'b': 'B', 'B': 'b', 'c': 'C', 'C': 'c',
    'd': 'D', 'D': 'd', 'e': 'E', 'E': 'e', 'f': 'F', 'F': 'f',
    'g': 'G', 'G': 'g', 'h': 'H', 'H': 'h', 'i': 'I', 'I': 'i',
    'j': 'J', 'J': 'j', 'k': 'K', 'K': 'k', 'l': 'L', 'L': 'l',
    'm': 'M', 'M': 'm', 'n': 'N', 'N': 'n', 'o': 'O', 'O': 'o',
    'p': 'P', 'P': 'p', 'q': 'Q', 'Q': 'q', 'r': 'R', 'R': 'r',
    's': 'S', 'S': 's', 't': 'T', 'T': 't', 'u': 'U', 'U': 'u',
    'v': 'V', 'V': 'v', 'w': 'W', 'W': 'w', 'x': 'X', 'X': 'x',
    'y': 'Y', 'Y': 'y', 'z': 'Z', 'Z': 'z',
}
