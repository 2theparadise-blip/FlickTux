//! `VirtualKeyboard`: registers "FlickTux Virtual Keyboard" and injects keystrokes.

use std::io;
use std::thread::sleep;
use std::time::Duration;

use evdev::uinput::VirtualDevice;
use evdev::{AttributeSet, EventType, InputEvent, KeyCode};

use crate::core::keys::{Stroke, KEY_BACKSPACE, KEY_LEFTCTRL, KEY_LEFTSHIFT};
use crate::core::romaji;

pub const DEVICE_NAME: &str = "FlickTux Virtual Keyboard";

pub struct VirtualKeyboard {
    dev: VirtualDevice,
}

impl VirtualKeyboard {
    /// Create the device. Needs write access to `/dev/uinput` (see `udev/`).
    pub fn new() -> io::Result<Self> {
        let mut keys = AttributeSet::<KeyCode>::new();
        // Register every regular keycode 1..=248 so any key can be sent later.
        for code in 1u16..=248 {
            keys.insert(KeyCode::new(code));
        }
        let dev = VirtualDevice::builder()?
            .name(DEVICE_NAME)
            .with_keys(&keys)?
            .build()?;
        // Give the desktop a moment to notice the new device.
        sleep(Duration::from_millis(300));
        Ok(Self { dev })
    }

    fn key_event(code: u16, value: i32) -> InputEvent {
        InputEvent::new(EventType::KEY.0, code, value)
    }

    /// Press and release one key (each phase is its own SYN frame).
    pub fn tap_code(&mut self, code: u16) -> io::Result<()> {
        self.tap(Stroke::plain(code))
    }

    pub fn tap(&mut self, s: Stroke) -> io::Result<()> {
        if s.ctrl {
            self.dev.emit(&[Self::key_event(KEY_LEFTCTRL, 1)])?;
        }
        if s.shift {
            self.dev.emit(&[Self::key_event(KEY_LEFTSHIFT, 1)])?;
        }
        self.dev.emit(&[Self::key_event(s.code, 1)])?;
        self.dev.emit(&[Self::key_event(s.code, 0)])?;
        if s.shift {
            self.dev.emit(&[Self::key_event(KEY_LEFTSHIFT, 0)])?;
        }
        if s.ctrl {
            self.dev.emit(&[Self::key_event(KEY_LEFTCTRL, 0)])?;
        }
        Ok(())
    }

    pub fn tap_all(&mut self, strokes: &[Stroke]) -> io::Result<()> {
        for s in strokes {
            self.tap(*s)?;
        }
        Ok(())
    }

    /// Send ASCII text as keystrokes (romaji goes to the IME as-is).
    pub fn type_ascii(&mut self, text: &str) -> io::Result<()> {
        let strokes = romaji::ascii_to_strokes(text).map_err(bad_char)?;
        self.tap_all(&strokes)
    }

    /// Send kana text via romaji keystrokes.
    pub fn type_kana(&mut self, text: &str) -> io::Result<()> {
        let strokes = romaji::kana_to_strokes(text).map_err(bad_char)?;
        self.tap_all(&strokes)
    }

    /// Replace the previous kana (dakuten / small-kana toggle):
    /// BackSpace x `erase`, then the new text, with no delay in between.
    pub fn replace_kana(&mut self, erase: usize, new_text: &str) -> io::Result<()> {
        let strokes = romaji::kana_to_strokes(new_text).map_err(bad_char)?;
        for _ in 0..erase {
            self.tap_code(KEY_BACKSPACE)?;
        }
        self.tap_all(&strokes)
    }
}

fn bad_char(c: char) -> io::Error {
    io::Error::new(io::ErrorKind::InvalidInput, format!("unsupported character: {c:?}"))
}
