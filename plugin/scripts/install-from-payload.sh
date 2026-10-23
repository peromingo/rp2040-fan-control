#!/bin/sh
# Installer engine executed by the Unraid .plg after its versioned payload
# archive has been checksum-verified and extracted into a temporary directory.
set -eu

STAGE=${1:?usage: install-from-payload.sh EXTRACTED_PAYLOAD_ROOT}
case "$STAGE" in /*) ;; *) echo 'payload stage must be an absolute path' >&2; exit 2 ;; esac
[ -d "$STAGE" ] || { echo 'payload stage does not exist' >&2; exit 1; }
[ "$(id -u)" -eq 0 ] || { echo 'installer must run as root' >&2; exit 1; }

PLUGIN_DIR=/boot/config/plugins/rp2040-fan-control
APP_DIR="$PLUGIN_DIR/app"
WEB_ROOT=/usr/local/emhttp/plugins
WEB_DIR="$WEB_ROOT/rp2040-fan-control"
PLUGIN_SBIN=/usr/local/sbin
WRAPPER="$PLUGIN_SBIN/rp2040-fan-control"
SOURCE_APP="$STAGE/usr/local/share/rp2040-fan-control/app"
SOURCE_WEB="$STAGE/usr/local/emhttp/plugins/rp2040-fan-control"
SOURCE_WRAPPER="$STAGE/usr/local/sbin/rp2040-fan-control"

[ -d "$SOURCE_APP/fan_control" ] || { echo 'payload app is incomplete' >&2; exit 1; }
[ -f "$SOURCE_APP/rp2040_fan_control_webui_dev.py" ] || { echo 'payload daemon is missing' >&2; exit 1; }
[ -f "$SOURCE_WEB/RP2040FanControl.page" ] || { echo 'payload WebUI is missing' >&2; exit 1; }
[ -f "$SOURCE_WEB/pages/index.php" ] || { echo 'payload PHP page is missing' >&2; exit 1; }
[ -f "$SOURCE_WRAPPER" ] || { echo 'payload service wrapper is missing' >&2; exit 1; }

[ ! -L "$PLUGIN_DIR" ] || { echo 'refusing symlink at persistent plugin directory' >&2; exit 1; }
[ ! -L "$APP_DIR" ] || { echo 'refusing symlink at persistent app directory' >&2; exit 1; }
if [ -L "$APP_DIR/fan_control/site_config_local.py" ]; then
    echo 'refusing symlink at local hardware configuration' >&2
    exit 1
fi
[ ! -L "$WEB_DIR" ] || { echo 'refusing symlink at WebUI plugin directory' >&2; exit 1; }
[ ! -L "$WRAPPER" ] || { echo 'refusing symlink at service wrapper path' >&2; exit 1; }

if [ ! -e "$PLUGIN_DIR" ]; then
    (umask 027; mkdir -p "$PLUGIN_DIR") || { echo 'could not create persistent plugin directory' >&2; exit 1; }
    chmod 0750 "$PLUGIN_DIR"
else
    [ -d "$PLUGIN_DIR" ] || { echo 'persistent plugin path is not a directory' >&2; exit 1; }
    owner="$(stat -c '%u' "$PLUGIN_DIR" 2>/dev/null)" || { echo 'could not verify persistent plugin directory owner' >&2; exit 1; }
    [ "$owner" = 0 ] || { echo 'persistent plugin directory must belong to root' >&2; exit 1; }
    mode="$(stat -c '%a' "$PLUGIN_DIR" 2>/dev/null)" || { echo 'could not verify persistent plugin directory permissions' >&2; exit 1; }
    case "$mode" in
        *[2367]|*[2367][0-7]) echo 'persistent plugin directory has group/world write permission; refusing to alter existing permissions' >&2; exit 1 ;;
    esac
fi

# Never replace files while this plugin's own daemon is running.
if [ -x "$WRAPPER" ]; then
    "$WRAPPER" stop || { echo 'could not stop existing daemon; update aborted' >&2; exit 1; }
fi

# Stage the app on the same persistent filesystem, retaining the local hardware
# map if present. The first-install example remains disabled by placeholders.
APP_STAGE=
WEB_STAGE=
WRAPPER_STAGE=
APP_BACKUP="$PLUGIN_DIR/.app-backup.$$"
WEB_BACKUP="$WEB_ROOT/.rp2040-web-backup.$$"
WRAPPER_BACKUP="$PLUGIN_SBIN/.rp2040-fan-control-backup.$$"
[ ! -e "$APP_BACKUP" ] || { echo 'stale app backup path exists; refusing to continue' >&2; exit 1; }
[ ! -e "$WEB_BACKUP" ] || { echo 'stale WebUI backup path exists; refusing to continue' >&2; exit 1; }
[ ! -e "$WRAPPER_BACKUP" ] || { echo 'stale wrapper backup path exists; refusing to continue' >&2; exit 1; }
APP_SWAPPED=0
WEB_SWAPPED=0
WRAPPER_SWAPPED=0
APP_BACKED_UP=0
WEB_BACKED_UP=0
WRAPPER_BACKED_UP=0
cleanup() {
    rc=$?
    rollback_failed=0
    if [ "$rc" -ne 0 ]; then
        if [ "$WRAPPER_SWAPPED" -eq 1 ]; then rm -f "$WRAPPER" || rollback_failed=1; fi
        if [ "$WRAPPER_BACKED_UP" -eq 1 ] && [ -f "$WRAPPER_BACKUP" ]; then
            mv "$WRAPPER_BACKUP" "$WRAPPER" || { echo "rollback failed; wrapper backup retained at $WRAPPER_BACKUP" >&2; rollback_failed=1; }
        fi
        if [ "$WEB_SWAPPED" -eq 1 ]; then rm -rf "$WEB_DIR" || rollback_failed=1; fi
        if [ "$WEB_BACKED_UP" -eq 1 ] && [ -d "$WEB_BACKUP" ]; then
            mv "$WEB_BACKUP" "$WEB_DIR" || { echo "rollback failed; WebUI backup retained at $WEB_BACKUP" >&2; rollback_failed=1; }
        fi
        if [ "$APP_SWAPPED" -eq 1 ]; then rm -rf "$APP_DIR" || rollback_failed=1; fi
        if [ "$APP_BACKED_UP" -eq 1 ] && [ -d "$APP_BACKUP" ]; then
            mv "$APP_BACKUP" "$APP_DIR" || { echo "rollback failed; app backup retained at $APP_BACKUP" >&2; rollback_failed=1; }
        fi
    fi
    [ -z "$APP_STAGE" ] || rm -rf "$APP_STAGE"
    [ -z "$WEB_STAGE" ] || rm -rf "$WEB_STAGE"
    [ -z "$WRAPPER_STAGE" ] || rm -f "$WRAPPER_STAGE"
    # Backups are deleted only after a successful commit. If rollback itself
    # fails, keep every remaining backup for manual recovery.
    if [ "$rc" -eq 0 ]; then
        [ ! -d "$APP_BACKUP" ] || rm -rf "$APP_BACKUP"
        [ ! -d "$WEB_BACKUP" ] || rm -rf "$WEB_BACKUP"
        [ ! -f "$WRAPPER_BACKUP" ] || rm -f "$WRAPPER_BACKUP"
    elif [ "$rollback_failed" -ne 0 ]; then
        echo 'installer rollback was incomplete; inspect and preserve the reported backup paths' >&2
    fi
    exit "$rc"
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM

APP_STAGE=$(mktemp -d "$PLUGIN_DIR/.app-stage.XXXXXX")
WEB_STAGE=$(mktemp -d "$WEB_ROOT/.rp2040-web-stage.XXXXXX")
WRAPPER_STAGE=$(mktemp "$PLUGIN_SBIN/.rp2040-fan-control.XXXXXX")
install -m 0755 "$SOURCE_WRAPPER" "$WRAPPER_STAGE"

cp -R "$SOURCE_APP/." "$APP_STAGE/"
if [ -f "$APP_DIR/fan_control/site_config_local.py" ]; then
    cp -p "$APP_DIR/fan_control/site_config_local.py" "$APP_STAGE/fan_control/site_config_local.py"
else
    cp "$APP_STAGE/fan_control/site_config.example.py" "$APP_STAGE/fan_control/site_config_local.py"
fi
chmod 0600 "$APP_STAGE/fan_control/site_config_local.py"

cp -R "$SOURCE_WEB/." "$WEB_STAGE/"
chmod 0644 "$WEB_STAGE/RP2040FanControl.page" "$WEB_STAGE/pages/index.php"

if [ -d "$APP_DIR" ]; then APP_BACKED_UP=1; mv "$APP_DIR" "$APP_BACKUP"; fi
APP_SWAPPED=1
mv "$APP_STAGE" "$APP_DIR"
if [ -d "$WEB_DIR" ]; then WEB_BACKED_UP=1; mv "$WEB_DIR" "$WEB_BACKUP"; fi
WEB_SWAPPED=1
mv "$WEB_STAGE" "$WEB_DIR"
if [ -f "$WRAPPER" ]; then WRAPPER_BACKED_UP=1; mv "$WRAPPER" "$WRAPPER_BACKUP"; fi
WRAPPER_SWAPPED=1
mv "$WRAPPER_STAGE" "$WRAPPER"
WRAPPER_STAGE=
# Runtime IPC is created by the service on start, not by installation.
# Startup is intentionally opt-in; never create ENABLE automatically.

echo 'rp2040-fan-control: files installed; daemon remains disabled until configured and ENABLE is created.'
