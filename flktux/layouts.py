#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
flktux.layouts: Japanese flick keyboards and 10-key layout definitions
"""

# Common Kana Flick Definitions
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

# 1. Google (Gboard) Layout: 5 columns x 4 rows
LAYOUT_GOOGLE = [
    [{"type": "action", "label": "あA1", "action": "mode", "style": "action-cell"},
     {"type": "flick", "key": "あ"},
     {"type": "flick", "key": "か"},
     {"type": "flick", "key": "さ"},
     {"type": "action", "label": "⌫", "action": "backspace", "style": "action-cell"}],
    [{"type": "action", "label": "◀", "action": "left", "style": "action-cell"},
     {"type": "flick", "key": "た"},
     {"type": "flick", "key": "な"},
     {"type": "flick", "key": "は"},
     {"type": "action", "label": "▶", "action": "right", "style": "action-cell"}],
    [{"type": "action", "label": "記号", "action": "symbol", "style": "action-cell"},
     {"type": "flick", "key": "ま"},
     {"type": "flick", "key": "や", "flick_data": YA_ANDROID},
     {"type": "flick", "key": "ら"},
     {"type": "action", "label": "空白", "action": "space", "style": "action-cell"}],
    [{"type": "action", "label": "変換", "action": "convert", "style": "action-cell"},
     {"type": "action", "label": "゛゜小", "action": "dakuten", "style": "action-cell"},
     {"type": "flick", "key": "わ"},
     {"type": "flick", "key": "、。"},
     {"type": "action", "label": "確定", "action": "enter", "style": "enter-cell"}],
]

# 2. Samsung (Galaxy) Layout: 5 columns x 4 rows
LAYOUT_GALAXY = [
    [{"type": "action", "label": "あ/A", "action": "mode", "style": "action-cell"},
     {"type": "flick", "key": "あ"},
     {"type": "flick", "key": "か"},
     {"type": "flick", "key": "さ"},
     {"type": "action", "label": "⌫", "action": "backspace", "style": "action-cell"}],
    [{"type": "action", "label": "数字", "action": "number", "style": "action-cell"},
     {"type": "flick", "key": "た"},
     {"type": "flick", "key": "な"},
     {"type": "flick", "key": "は"},
     {"type": "action", "label": "◀", "action": "left", "style": "action-cell"}],
    [{"type": "action", "label": "記号", "action": "symbol", "style": "action-cell"},
     {"type": "flick", "key": "ま"},
     {"type": "flick", "key": "や", "flick_data": YA_ANDROID},
     {"type": "flick", "key": "ら"},
     {"type": "action", "label": "▶", "action": "right", "style": "action-cell"}],
    [{"type": "action", "label": "空白", "action": "space", "style": "action-cell"},
     {"type": "action", "label": "゛゜小", "action": "dakuten", "style": "action-cell"},
     {"type": "flick", "key": "わ"},
     {"type": "flick", "key": "、。"},
     {"type": "action", "label": "確定", "action": "enter", "style": "enter-cell"}],
]

# 3. Apple (iPhone iOS) Layout: 5 columns x 4 rows
LAYOUT_IPHONE = [
    [{"type": "action", "label": "🌐/英", "action": "mode", "style": "action-cell"},
     {"type": "flick", "key": "あ"},
     {"type": "flick", "key": "か"},
     {"type": "flick", "key": "さ"},
     {"type": "action", "label": "⌫", "action": "backspace", "style": "action-cell"}],
    [{"type": "action", "label": "1 2 3", "action": "number", "style": "action-cell"},
     {"type": "flick", "key": "た"},
     {"type": "flick", "key": "な"},
     {"type": "flick", "key": "は"},
     {"type": "action", "label": "空白", "action": "space", "style": "action-cell"}],
    [{"type": "action", "label": "◀", "action": "left", "style": "action-cell"},
     {"type": "flick", "key": "ま"},
     {"type": "flick", "key": "や", "flick_data": YA_IPHONE},
     {"type": "flick", "key": "ら"},
     {"type": "action", "label": "▶", "action": "right", "style": "action-cell"}],
    [{"type": "action", "label": "記号", "action": "symbol", "style": "action-cell"},
     {"type": "action", "label": "゛゜小", "action": "dakuten", "style": "action-cell"},
     {"type": "flick", "key": "わ"},
     {"type": "flick", "key": "、。"},
     {"type": "action", "label": "確定", "action": "enter", "style": "enter-cell"}],
]

# 4. Feature Phone (ガラケー / ケータイ打ち) Layout: 5 columns x 4 rows
LAYOUT_GALAKEI = [
    [{"type": "action", "label": "クリア", "action": "backspace", "style": "action-cell"},
     {"type": "flick", "key": "あ", "num": "1"},
     {"type": "flick", "key": "か", "num": "2"},
     {"type": "flick", "key": "さ", "num": "3"},
     {"type": "action", "label": "確定", "action": "enter", "style": "enter-cell"}],
    [{"type": "action", "label": "◀", "action": "left", "style": "action-cell"},
     {"type": "flick", "key": "た", "num": "4"},
     {"type": "flick", "key": "な", "num": "5"},
     {"type": "flick", "key": "は", "num": "6"},
     {"type": "action", "label": "▶", "action": "right", "style": "action-cell"}],
    [{"type": "action", "label": "記号", "action": "symbol", "style": "action-cell"},
     {"type": "flick", "key": "ま", "num": "7"},
     {"type": "flick", "key": "や", "num": "8", "flick_data": YA_ANDROID},
     {"type": "flick", "key": "ら", "num": "9"},
     {"type": "action", "label": "空白", "action": "space", "style": "action-cell"}],
    [{"type": "action", "label": "変換", "action": "convert", "style": "action-cell"},
     {"type": "action", "label": "゛゜小", "action": "dakuten", "num": "*", "style": "action-cell"},
     {"type": "flick", "key": "わ", "num": "0"},
     {"type": "flick", "key": "、。", "num": "#"},
     {"type": "action", "label": "次へ", "action": "next", "style": "action-cell"}],
]

# 5. 10-Key Numpad Layout: 5 rows x 4 columns
# ユーザー指定: 7:あ, 8:か, 9:さ / 4:た, 5:な, 6:は / 1:ま, 2:や, 3:ら / 0:わ
LAYOUT_TENKEY = [
    [{"type": "action", "label": "記号", "num": "/", "action": "symbol", "style": "action-cell"},
     {"type": "action", "label": "◀", "num": "←", "action": "left", "style": "action-cell"},
     {"type": "action", "label": "▶", "num": "→", "action": "right", "style": "action-cell"},
     {"type": "action", "label": "⌫", "num": "BS", "action": "backspace", "style": "action-cell"}],
    [{"type": "flick", "key": "あ", "num": "7"},
     {"type": "flick", "key": "か", "num": "8"},
     {"type": "flick", "key": "さ", "num": "9"},
     {"type": "action", "label": "空白", "num": "-", "action": "space", "style": "action-cell"}],
    [{"type": "flick", "key": "た", "num": "4"},
     {"type": "flick", "key": "な", "num": "5"},
     {"type": "flick", "key": "は", "num": "6"},
     {"type": "action", "label": "変換", "num": "変", "action": "convert", "style": "action-cell"}],
    [{"type": "flick", "key": "ま", "num": "1"},
     {"type": "flick", "key": "や", "num": "2", "flick_data": YA_ANDROID},
     {"type": "flick", "key": "ら", "num": "3"},
     {"type": "action", "label": "次へ", "num": "+", "action": "next", "style": "action-cell"}],
    [{"type": "flick", "key": "わ", "num": "0"},
     {"type": "flick", "key": "、。", "num": "."},
     {"type": "action", "label": "゛゜小", "num": "*", "action": "dakuten", "style": "action-cell"},
     {"type": "action", "label": "確定", "num": "Ent", "action": "enter", "style": "enter-cell"}],
]

LAYOUTS = {
    "Google": LAYOUT_GOOGLE,
    "Galaxy": LAYOUT_GALAXY,
    "iPhone": LAYOUT_IPHONE,
    "ガラケー": LAYOUT_GALAKEI,
    "10キー": LAYOUT_TENKEY,
}

# Toggle cycles for keypad typing (あ->い->う->え->お)
TOGGLE_CYCLES = {
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
}

# Dakuten / Handakuten / Small letter toggle cycles
DAKUTEN_MAP = {
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
}
