#!/usr/bin/env bash
# FlickTux Systemd User Service Installer for Linux Mint & Raspberry Pi (ARM64)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN_SRC="${SCRIPT_DIR}/target/release/flktux"

echo "=========================================================="
echo "  🐧 FlickTux: systemd User Service Setup"
echo "=========================================================="

# 1. Install binary if release build exists
if [[ -f "${BIN_SRC}" ]]; then
    echo "📦 Installing flktux binary to /usr/local/bin/flktux..."
    sudo cp "${BIN_SRC}" /usr/local/bin/flktux
    sudo chmod 755 /usr/local/bin/flktux
else
    echo "ℹ️  Release binary not found at ${BIN_SRC}. Skipping binary copy."
fi

# 2. Setup user systemd directory
SYSTEMD_USER_DIR="${HOME}/.config/systemd/user"
mkdir -p "${SYSTEMD_USER_DIR}"

# 3. Copy service unit
SERVICE_FILE="${SCRIPT_DIR}/systemd/flicktux.service"
echo "⚙️  Installing ${SERVICE_FILE} -> ${SYSTEMD_USER_DIR}/flicktux.service..."
cp "${SERVICE_FILE}" "${SYSTEMD_USER_DIR}/flicktux.service"

# 4. Reload and enable service
echo "🔄 Reloading systemd user daemon..."
systemctl --user daemon-reload
echo "✅ Enabling flicktux.service..."
systemctl --user enable flicktux.service

echo ""
echo "🎉 FlickTux systemd service installed successfully!"
echo "Commands to manage FlickTux:"
echo "  - Start now : systemctl --user start flicktux.service"
echo "  - Stop now  : systemctl --user stop flicktux.service"
echo "  - Status    : systemctl --user status flicktux.service"
echo "  - Logs      : journalctl --user -u flicktux.service -f"
echo "=========================================================="
