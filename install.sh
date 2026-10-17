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
[ -d "${SCRIPT_DIR}/assets" ] && cp -r "${SCRIPT_DIR}/assets" "${INSTALL_DIR}/"
chmod -R a+rX "${INSTALL_DIR}"
chmod a+rx "${INSTALL_DIR}/bin/flktux" "${INSTALL_DIR}/bin/flktux-settings"

# 3. Install Icon to system paths
echo "🎨 Installing application icons..."
if [ -f "${INSTALL_DIR}/assets/icon.png" ]; then
    mkdir -p /usr/share/pixmaps
    cp "${INSTALL_DIR}/assets/icon.png" /usr/share/pixmaps/flicktux.png
    mkdir -p /usr/share/icons/hicolor/512x512/apps
    cp "${INSTALL_DIR}/assets/icon.png" /usr/share/icons/hicolor/512x512/apps/flicktux.png
fi

# 4. Create symlinks in /usr/local/bin
echo "🔗 Creating symlinks in ${BIN_DIR}..."
ln -sf "${INSTALL_DIR}/bin/flktux" "${BIN_DIR}/flktux"
ln -sf "${INSTALL_DIR}/bin/flktux-settings" "${BIN_DIR}/flktux-settings"

# 5. Install desktop launchers
echo "🖥️ Installing desktop shortcuts..."
cp "${SCRIPT_DIR}/desktop/flktux.desktop" "${DESKTOP_APPS}/flktux.desktop"
cp "${SCRIPT_DIR}/desktop/flktux-settings.desktop" "${DESKTOP_APPS}/flktux-settings.desktop"
chmod a+r "${DESKTOP_APPS}/flktux*.desktop"

# 6. User desktop shortcuts
TARGET_USERS=("${SUDO_USER:-}" "$(logname 2>/dev/null || true)" "gesenu")
for U in "${TARGET_USERS[@]}"; do
    if [ -n "${U}" ] && [ -d "/home/${U}" ]; then
        for D in "/home/${U}/デスクトップ" "/home/${U}/Desktop"; do
            if [ -d "${D}" ]; then
                cp "${SCRIPT_DIR}/desktop/flktux.desktop" "${D}/FlickTux.desktop"
                cp "${SCRIPT_DIR}/desktop/flktux-settings.desktop" "${D}/ペンタブ感度設定.desktop"
                chown "${U}:${U}" "${D}"/FlickTux.desktop "${D}"/ペンタブ感度設定.desktop
                chmod +x "${D}"/FlickTux.desktop "${D}"/ペンタブ感度設定.desktop
                su - "${U}" -c "DISPLAY=:0 gio set '${D}/FlickTux.desktop' metadata::trusted true 2>/dev/null || true"
                su - "${U}" -c "DISPLAY=:0 gio set '${D}/ペンタブ感度設定.desktop' metadata::trusted true 2>/dev/null || true"
            fi
        done
        break
    fi
done

echo "=================================================================="
echo "🎉 FlickTux (flktux) successfully installed!"
echo "   Run from terminal: flktux"
echo "   Settings GUI     : flktux-settings"
echo "=================================================================="
