//! Linux input keycodes (`linux/input-event-codes.h`) as plain `u16`,
//! so the core stays independent of the `evdev` crate.
//! Assumes a US-layout symbol mapping.

#![allow(dead_code)]

pub const KEY_ESC: u16 = 1;
pub const KEY_MINUS: u16 = 12;
pub const KEY_EQUAL: u16 = 13;
pub const KEY_BACKSPACE: u16 = 14;
pub const KEY_TAB: u16 = 15;
pub const KEY_LEFTCTRL: u16 = 29;
pub const KEY_LEFTBRACE: u16 = 26;
pub const KEY_RIGHTBRACE: u16 = 27;
pub const KEY_ENTER: u16 = 28;
pub const KEY_SEMICOLON: u16 = 39;
pub const KEY_APOSTROPHE: u16 = 40;
pub const KEY_GRAVE: u16 = 41;
pub const KEY_LEFTSHIFT: u16 = 42;
pub const KEY_BACKSLASH: u16 = 43;
pub const KEY_COMMA: u16 = 51;
pub const KEY_DOT: u16 = 52;
pub const KEY_SLASH: u16 = 53;
pub const KEY_SPACE: u16 = 57;
pub const KEY_HOME: u16 = 102;
pub const KEY_UP: u16 = 103;
pub const KEY_PAGEUP: u16 = 104;
pub const KEY_LEFT: u16 = 105;
pub const KEY_RIGHT: u16 = 106;
pub const KEY_END: u16 = 107;
pub const KEY_DOWN: u16 = 108;
pub const KEY_PAGEDOWN: u16 = 109;
pub const KEY_DELETE: u16 = 111;

/// A key press, optionally with Shift / Ctrl held.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Stroke {
    pub code: u16,
    pub shift: bool,
    pub ctrl: bool,
}

impl Stroke {
    pub const fn plain(code: u16) -> Self {
        Self { code, shift: false, ctrl: false }
    }
    pub const fn shifted(code: u16) -> Self {
        Self { code, shift: true, ctrl: false }
    }
}

const LETTERS: [u16; 26] = [
    30, 48, 46, 32, 18, 33, 34, 35, 23, 36, 37, 38, 50, // a-m
    49, 24, 25, 16, 19, 31, 20, 22, 47, 17, 45, 21, 44, // n-z
];
const DIGITS: [u16; 10] = [11, 2, 3, 4, 5, 6, 7, 8, 9, 10]; // 0-9

/// Map one ASCII char to a keystroke (US layout). `None` if unsupported.
pub fn stroke_for_char(c: char) -> Option<Stroke> {
    Some(match c {
        'a'..='z' => Stroke::plain(LETTERS[(c as u8 - b'a') as usize]),
        'A'..='Z' => Stroke::shifted(LETTERS[(c as u8 - b'A') as usize]),
        '0'..='9' => Stroke::plain(DIGITS[(c as u8 - b'0') as usize]),
        ' ' => Stroke::plain(KEY_SPACE),
        '\n' => Stroke::plain(KEY_ENTER),
        '\t' => Stroke::plain(KEY_TAB),
        '-' => Stroke::plain(KEY_MINUS),
        '=' => Stroke::plain(KEY_EQUAL),
        '[' => Stroke::plain(KEY_LEFTBRACE),
        ']' => Stroke::plain(KEY_RIGHTBRACE),
        ';' => Stroke::plain(KEY_SEMICOLON),
        '\'' => Stroke::plain(KEY_APOSTROPHE),
        '`' => Stroke::plain(KEY_GRAVE),
        '\\' => Stroke::plain(KEY_BACKSLASH),
        ',' => Stroke::plain(KEY_COMMA),
        '.' => Stroke::plain(KEY_DOT),
        '/' => Stroke::plain(KEY_SLASH),
        '!' => Stroke::shifted(DIGITS[1]),
        '@' => Stroke::shifted(DIGITS[2]),
        '#' => Stroke::shifted(DIGITS[3]),
        '$' => Stroke::shifted(DIGITS[4]),
        '%' => Stroke::shifted(DIGITS[5]),
        '^' => Stroke::shifted(DIGITS[6]),
        '&' => Stroke::shifted(DIGITS[7]),
        '*' => Stroke::shifted(DIGITS[8]),
        '(' => Stroke::shifted(DIGITS[9]),
        ')' => Stroke::shifted(DIGITS[0]),
        '_' => Stroke::shifted(KEY_MINUS),
        '+' => Stroke::shifted(KEY_EQUAL),
        '{' => Stroke::shifted(KEY_LEFTBRACE),
        '}' => Stroke::shifted(KEY_RIGHTBRACE),
        ':' => Stroke::shifted(KEY_SEMICOLON),
        '"' => Stroke::shifted(KEY_APOSTROPHE),
        '~' => Stroke::shifted(KEY_GRAVE),
        '|' => Stroke::shifted(KEY_BACKSLASH),
        '<' => Stroke::shifted(KEY_COMMA),
        '>' => Stroke::shifted(KEY_DOT),
        '?' => Stroke::shifted(KEY_SLASH),
        _ => return None,
    })
}

/// Named special keys for the CLI (`--key enter`).
pub fn code_for_name(name: &str) -> Option<u16> {
    Some(match name.to_ascii_lowercase().as_str() {
        "enter" | "return" => KEY_ENTER,
        "backspace" | "bs" => KEY_BACKSPACE,
        "space" => KEY_SPACE,
        "tab" => KEY_TAB,
        "esc" | "escape" => KEY_ESC,
        "delete" | "del" => KEY_DELETE,
        "left" => KEY_LEFT,
        "right" => KEY_RIGHT,
        "up" => KEY_UP,
        "down" => KEY_DOWN,
        "home" => KEY_HOME,
        "end" => KEY_END,
        "pageup" | "page_up" => KEY_PAGEUP,
        "pagedown" | "page_down" => KEY_PAGEDOWN,
        _ => return None,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn letters_and_digits() {
        assert_eq!(stroke_for_char('a'), Some(Stroke::plain(30)));
        assert_eq!(stroke_for_char('k'), Some(Stroke::plain(37)));
        assert_eq!(stroke_for_char('A'), Some(Stroke::shifted(30)));
        assert_eq!(stroke_for_char('0'), Some(Stroke::plain(11)));
        assert_eq!(stroke_for_char('1'), Some(Stroke::plain(2)));
    }

    #[test]
    fn unsupported() {
        assert_eq!(stroke_for_char('あ'), None);
    }
}
