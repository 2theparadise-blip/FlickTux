//! Pen and tablet input handling.

pub mod mapper;

#[cfg(target_os = "linux")]
pub mod evdev_listener;
