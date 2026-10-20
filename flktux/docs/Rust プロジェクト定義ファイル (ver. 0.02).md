[package]
name = "linux-virtual-flick-keyboard"
version = "0.02.0"
edition = "2021"
description = "Multi-device virtual flick keyboard for Linux Mint / Ubuntu with pen-tablet stabilizer and fast uinput IME bridge"
license = "MIT"

[dependencies]
tokio = { version = "1.37", features = ["full"] }
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
evdev = { version = "0.12", features = ["tokio"] }
x11rb = { version = "0.13", features = ["allow-unsafe-code"] }
gtk4 = { version = "0.8", features = ["v4_10"] }
gdk4-x11 = "0.8"
anyhow = "1.0"
tracing = "0.1"
tracing-subscriber = "0.3"

[dev-dependencies]
approx = "0.5"