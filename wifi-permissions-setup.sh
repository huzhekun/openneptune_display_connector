#!/bin/sh
# Allow the display service user to manage Wi-Fi through NetworkManager.
#
# display.service runs unprivileged with NoNewPrivileges=true, so the connector
# can't use sudo; nmcli talks to NetworkManager over D-Bus and polkit decides.
# Installs a JavaScript rule (polkit >= 0.106) and, where the old local
# authority exists, the equivalent .pkla file (polkit 0.105).
set -eu

[ "$(id -u)" -eq 0 ] || { echo "Run as root"; exit 1; }

USER_NAME="${1:-mks}"
RULES_DIR="/etc/polkit-1/rules.d"
PKLA_DIR="/etc/polkit-1/localauthority/50-local.d"
NAME="50-display-connector-networkmanager"

mkdir -p "$RULES_DIR"
cat > "$RULES_DIR/$NAME.rules" <<EOF
// Installed by display_connector: lets $USER_NAME change Wi-Fi from the touchscreen.
polkit.addRule(function(action, subject) {
    if (action.id.indexOf("org.freedesktop.NetworkManager.") === 0 &&
        subject.user === "$USER_NAME") {
        return polkit.Result.YES;
    }
});
EOF
chmod 0644 "$RULES_DIR/$NAME.rules"

if [ -d /etc/polkit-1/localauthority ]; then
    mkdir -p "$PKLA_DIR"
    cat > "$PKLA_DIR/$NAME.pkla" <<EOF
[Let $USER_NAME change Wi-Fi from the touchscreen (display_connector)]
Identity=unix-user:$USER_NAME
Action=org.freedesktop.NetworkManager.*
ResultAny=yes
ResultInactive=yes
ResultActive=yes
EOF
    chmod 0644 "$PKLA_DIR/$NAME.pkla"
fi
