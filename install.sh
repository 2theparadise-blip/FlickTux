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
echo "Installing FlickTux (flktux)..."
echo "=================================================================="

# Check sudo
if [ "$(id -u)" -ne 0 ]; then
    echo "[!] This installer requires root privileges. Please run with sudo."
    exec sudo bash "$0" "$@"
fi

# 1. Install dependencies
echo "[*] Checking and installing system dependencies (including zinnia handwriting, xclip & touchegg)..."
apt-get update -qq
apt-get install -y -qq python3 python3-gi python3-gi-cairo python3-xlib gir1.2-gtk-3.0 xdotool xclip zinnia-utils tegaki-zinnia-japanese xserver-xorg-input-wacom xinput touchegg >/dev/null || true

# 2. Deploy source to /opt/flicktux
echo "[*] Copying files to ${INSTALL_DIR}..."
mkdir -p "${INSTALL_DIR}"
if [ "${SCRIPT_DIR}" != "${INSTALL_DIR}" ]; then
    cp -r "${SCRIPT_DIR}/flktux" "${INSTALL_DIR}/"
    [ -d "${SCRIPT_DIR}/bin" ] && cp -r "${SCRIPT_DIR}/bin" "${INSTALL_DIR}/"
    [ -d "${SCRIPT_DIR}/assets" ] && cp -r "${SCRIPT_DIR}/assets" "${INSTALL_DIR}/"
    [ -d "${SCRIPT_DIR}/desktop" ] && cp -r "${SCRIPT_DIR}/desktop" "${INSTALL_DIR}/"
    [ -d "${SCRIPT_DIR}/configs" ] && cp -r "${SCRIPT_DIR}/configs" "${INSTALL_DIR}/"
fi
chmod -R a+rX "${INSTALL_DIR}"
[ -f "${INSTALL_DIR}/bin/flktux" ] && chmod a+rx "${INSTALL_DIR}/bin/flktux"
[ -f "${INSTALL_DIR}/bin/flktux-settings" ] && chmod a+rx "${INSTALL_DIR}/bin/flktux-settings"

# 3. Install Icon to system paths (Standard Linux Mint / XDG icon theme hierarchy)
echo "[*] Installing application icons (hicolor 16x16 to 512x512 & pixmaps)..."
mkdir -p /usr/share/pixmaps
if [ -d "${INSTALL_DIR}/assets/pixmaps" ]; then
    cp -r "${INSTALL_DIR}/assets/pixmaps/"* /usr/share/pixmaps/
elif [ -f "${INSTALL_DIR}/assets/icon.png" ]; then
    cp "${INSTALL_DIR}/assets/icon.png" /usr/share/pixmaps/flicktux.png
fi

if [ -d "${INSTALL_DIR}/assets/icons/hicolor" ]; then
    cp -r "${INSTALL_DIR}/assets/icons/hicolor/"* /usr/share/icons/hicolor/
elif [ -f "${INSTALL_DIR}/assets/icon.png" ]; then
    mkdir -p /usr/share/icons/hicolor/512x512/apps
    cp "${INSTALL_DIR}/assets/icon.png" /usr/share/icons/hicolor/512x512/apps/flicktux.png
fi

# Update system icon cache so Mint/Cinnamon immediately recognizes new icons
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true
fi

# 4. Create symlinks in /usr/local/bin
echo "[*] Creating symlinks in ${BIN_DIR}..."
ln -sf "${INSTALL_DIR}/bin/flktux" "${BIN_DIR}/flktux"
ln -sf "${INSTALL_DIR}/bin/flktux-settings" "${BIN_DIR}/flktux-settings"

# 5. Install desktop launchers (Application Menu & Dock)
echo "[*] Installing application menu launchers (Applications & Dock)..."
DSRC="${SCRIPT_DIR}/desktop"
[ ! -d "${DSRC}" ] && DSRC="${INSTALL_DIR}/desktop"
cp "${DSRC}/flktux.desktop" "${DESKTOP_APPS}/flktux.desktop"
cp "${DSRC}/flktux-settings.desktop" "${DESKTOP_APPS}/flktux-settings.desktop"
chmod a+r "${DESKTOP_APPS}/flktux.desktop" "${DESKTOP_APPS}/flktux-settings.desktop"

# 6. Clean up desktop shortcuts (No icons on Desktop per user requirement)
echo "[*] Ensuring no shortcuts on user Desktop..."
TARGET_USERS=("${SUDO_USER:-}" "$(logname 2>/dev/null || true)" "gesenu")
for U in "${TARGET_USERS[@]}"; do
    if [ -n "${U}" ] && [ -d "/home/${U}" ]; then
        for D in "/home/${U}/デスクトップ" "/home/${U}/Desktop"; do
            if [ -d "${D}" ]; then
                rm -f "${D}/FlickTux.desktop" "${D}/ペンタブ感度設定.desktop" "${D}/flktux.desktop" "${D}/flktux-settings.desktop"
            fi
        done
        # 7. Configure F12 Global Keybinding in Cinnamon
        USER_UID=$(id -u "${U}" 2>/dev/null || echo 1000)
        su - "${U}" -c "
            export DBUS_SESSION_BUS_ADDRESS=\"unix:path=/run/user/${USER_UID}/bus\"
            dconf write /org/cinnamon/desktop/keybindings/custom-list \"['custom0']\" 2>/dev/null || true
            dconf write /org/cinnamon/desktop/keybindings/custom-keybindings/custom0/name \"'FlickTux Toggle'\" 2>/dev/null || true
            dconf write /org/cinnamon/desktop/keybindings/custom-keybindings/custom0/command \"'/usr/local/bin/flktux toggle'\" 2>/dev/null || true
            dconf write /org/cinnamon/desktop/keybindings/custom-keybindings/custom0/binding \"['F12']\" 2>/dev/null || true
        " 2>/dev/null || true

        # 8. Configure 3-Finger Swipe Gesture (Touchégg)
        echo "[*] Configuring 3-finger swipe gesture for user ${U}..."
        USER_CONF="/home/${U}/.config/touchegg"
        mkdir -p "${USER_CONF}"
        TSRC="${SCRIPT_DIR}/configs/touchegg.conf"
        [ ! -f "${TSRC}" ] && TSRC="${INSTALL_DIR}/configs/touchegg.conf"
        if [ -f "${TSRC}" ]; then
            cp "${TSRC}" "${USER_CONF}/touchegg.conf"
            chown -R "${U}:${U}" "${USER_CONF}"
            chmod 644 "${USER_CONF}/touchegg.conf"
            # Also deploy to /etc/touchegg/touchegg.conf as system fallback
            mkdir -p /etc/touchegg
            cp "${TSRC}" /etc/touchegg/touchegg.conf
            chmod 644 /etc/touchegg/touchegg.conf
        fi

        # Ensure Touchegg client autostart desktop entry for user session
        USER_AUTOSTART="/home/${U}/.config/autostart"
        mkdir -p "${USER_AUTOSTART}"
        cat << 'EOF' > "${USER_AUTOSTART}/touchegg.desktop"
[Desktop Entry]
Type=Application
Name=Touchégg
Comment=Touchégg Multi-touch Gesture Daemon Client
Exec=touchegg
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
EOF
        chown -R "${U}:${U}" "${USER_AUTOSTART}"
        break
    fi
done

# Restart Touchégg daemon
if command -v systemctl >/dev/null 2>&1; then
    systemctl enable touchegg >/dev/null 2>&1 || true
    systemctl restart touchegg >/dev/null 2>&1 || true
fi

echo "=================================================================="
echo "FlickTux (flktux) successfully installed!"
echo "   Launch via: F12 key (Global Toggle)"
echo "   Launch via: 3-Finger Swipe (Touch Gesture)"
echo "   Launch via: Plank Dock (Click FlickTux icon)"
echo "   Launch via: Application Menu (Accessories / System)"
echo "   Launch via: Terminal ('flktux toggle')"
echo "   Settings   : 'flktux-settings'"
echo "=================================================================="
