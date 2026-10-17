#!/usr/bin/env bash
# ==============================================================================
# FlickTux (flktux) Installer for Linux Mint / Ubuntu
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="/opt/flicktux"
BIN_DIR="/usr/local/bin"
DESKTOP_APPS="/usr/share/applications"

echo "=================================================================="
echo "🐧 Installing FlickTux (flktux)..."
echo "=================================================================="

# Check sudo
if [ "$(id -u)" -ne 0 ]; then
    echo "⚠️ This installer requires root privileges. Please run with sudo."
    exec sudo bash "$0" "$@"
fi

# 1. Install dependencies
echo "📦 Checking and installing system dependencies..."
apt-get update -qq
apt-get install -y -qq python3 python3-gi python3-gi-cairo python3-xlib gir1.2-gtk-3.0 xdotool xserver-xorg-input-wacom xinput >/dev/null || true

# 2. Deploy source to /opt/flicktux
echo "📂 Copying files to ${INSTALL_DIR}..."
mkdir -p "${INSTALL_DIR}"
cp -r "${SCRIPT_DIR}/flktux" "${INSTALL_DIR}/"
cp -r "${SCRIPT_DIR}/bin" "${INSTALL_DIR}/"
chmod -R a+rX "${INSTALL_DIR}"
chmod a+rx "${INSTALL_DIR}/bin/flktux" "${INSTALL_DIR}/bin/flktux-settings"

# 3. Create symlinks in /usr/local/bin
echo "🔗 Creating symlinks in ${BIN_DIR}..."
ln -sf "${INSTALL_DIR}/bin/flktux" "${BIN_DIR}/flktux"
ln -sf "${INSTALL_DIR}/bin/flktux-settings" "${BIN_DIR}/flktux-settings"

# 4. Install desktop launchers
echo "🖥️ Installing desktop shortcuts..."
cp "${SCRIPT_DIR}/desktop/flktux.desktop" "${DESKTOP_APPS}/flktux.desktop"
cp "${SCRIPT_DIR}/desktop/flktux-settings.desktop" "${DESKTOP_APPS}/flktux-settings.desktop"
chmod a+r "${DESKTOP_APPS}/flktux*.desktop"

# 5. User desktop shortcuts if non-root user exists
CURRENT_USER="${SUDO_USER:-$(logname 2>/dev/null || echo "")}"
if [ -n "${CURRENT_USER}" ] && [ -d "/home/${CURRENT_USER}" ]; then
    USER_DESKTOP="$(su - "${CURRENT_USER}" -c 'xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/デスクトップ"')"
    if [ -d "${USER_DESKTOP}" ]; then
        cp "${SCRIPT_DIR}/desktop/flktux.desktop" "${USER_DESKTOP}/FlickTux.desktop"
        cp "${SCRIPT_DIR}/desktop/flktux-settings.desktop" "${USER_DESKTOP}/ペンタブ感度設定.desktop"
        chown "${CURRENT_USER}:${CURRENT_USER}" "${USER_DESKTOP}"/*.desktop
        chmod +x "${USER_DESKTOP}"/*.desktop
        su - "${CURRENT_USER}" -c "gio set '${USER_DESKTOP}/FlickTux.desktop' metadata::trusted true 2>/dev/null || true"
        su - "${CURRENT_USER}" -c "gio set '${USER_DESKTOP}/ペンタブ感度設定.desktop' metadata::trusted true 2>/dev/null || true"
    fi
fi

echo "=================================================================="
echo "🎉 FlickTux (flktux) successfully installed!"
echo "   Run from terminal: flktux"
echo "   Settings GUI     : flktux-settings"
echo "=================================================================="
