#!/bin/sh
# Build a reproducible Unraid payload archive. This is NOT a .plg installer.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
VERSION=${1:-0.6.0-dev}
OUT_DIR=${2:-"$ROOT/dist"}
STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT HUP INT TERM

case "$VERSION" in
  *[!A-Za-z0-9._+-]*|'') echo "Invalid version: $VERSION" >&2; exit 2 ;;
esac
mkdir -p "$OUT_DIR"
PKG="$STAGE/pkg"
APP="$PKG/usr/local/share/rp2040-fan-control/app"
PLUGIN="$PKG/usr/local/emhttp/plugins/rp2040-fan-control"
SBIN="$PKG/usr/local/sbin"
INSTALLER="$PKG/usr/local/share/rp2040-fan-control"
mkdir -p "$APP/fan_control" "$PLUGIN/pages" "$SBIN" "$INSTALLER"

# App copy used by the installer helper; never include per-host local config.
cp "$ROOT/src/unraid/rp2040_fan_control_webui_dev.py" "$APP/"
cp "$ROOT/src/unraid/fan_control/"*.py "$APP/fan_control/"
rm -f "$APP/fan_control/site_config_local.py"
cp "$ROOT/src/unraid/fan_control/site_config.example.py" "$APP/fan_control/"

# Bundle pinned pyserial into the persistent app payload; Unraid never runs pip.
# CI/build host must have Python 3 and pip available.
python3 -m pip install --disable-pip-version-check --no-compile --no-deps \
  --requirement "$ROOT/requirements.txt" --target "$APP/vendor"
cp "$ROOT/plugin/src/usr/local/emhttp/plugins/rp2040-fan-control/RP2040FanControl.page" "$PLUGIN/"
cp "$ROOT/plugin/src/usr/local/emhttp/plugins/rp2040-fan-control/pages/index.php" "$PLUGIN/pages/"
cp "$ROOT/plugin/scripts/rp2040-fan-control" "$SBIN/"
cp "$ROOT/plugin/scripts/install-from-payload.sh" "$INSTALLER/install.sh"
chmod 0755 "$SBIN/rp2040-fan-control" "$INSTALLER/install.sh"
find "$PKG" -type d -exec chmod 0755 {} \;
find "$PKG" -type f -exec chmod 0644 {} \;
chmod 0755 "$SBIN/rp2040-fan-control" "$INSTALLER/install.sh"

# This is a pre-release payload. A .plg can be rendered only after a real
# versioned HTTPS release URL and this archive's SHA-256 are supplied.
ARCHIVE="$OUT_DIR/rp2040-fan-control-$VERSION-payload.tar.gz"
# Normalize ownership, mtimes and gzip metadata so identical source yields the same hash.
# This build helper runs in the developer/CI environment (GNU tar + gzip), not on Unraid.
tar --sort=name --mtime="@${SOURCE_DATE_EPOCH:-0}" --owner=0 --group=0 --numeric-owner \
  -C "$PKG" -cf - . | gzip -n > "$ARCHIVE"
if command -v sha256sum >/dev/null 2>&1; then
  (cd "$OUT_DIR" && sha256sum "$(basename "$ARCHIVE")" > "$(basename "$ARCHIVE").sha256")
fi
printf 'Built payload only (not installable): %s\n' "$ARCHIVE"
