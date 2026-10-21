#!/usr/bin/env bash
# Install the udev rule so flktux can use /dev/uinput without sudo.
set -euo pipefail
cd "$(dirname "$0")"

sudo install -m 0644 udev/99-flicktux.rules /etc/udev/rules.d/99-flicktux.rules
echo uinput | sudo tee /etc/modules-load.d/flicktux-uinput.conf >/dev/null
sudo modprobe uinput || true
sudo usermod -aG input "$USER" || true
sudo udevadm control --reload-rules
sudo udevadm trigger --subsystem-match=misc --sysname-match=uinput
echo "Done. Log out and back in (for the 'input' group), then try:"
echo "  cargo run -- emit --text konnichiha"
