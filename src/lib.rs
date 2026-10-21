//! FlickTux (`flktux`) library.
//! Floating Japanese Flick Keyboard for Pen Tablets & Linux.

pub mod core;
pub mod input;
pub mod server;
pub mod ui;
#[cfg(target_os = "linux")]
pub mod uinput;
