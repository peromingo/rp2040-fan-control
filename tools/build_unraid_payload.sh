#!/bin/sh
# Compatibility entry point; the source builder also emits the installable PLG.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SOURCE_VERSION=$(sed -n 's/^__version__ = "\([^"]*\)"$/\1/p' "$ROOT/src/unraid/fan_control/version.py")
VERSION=${1:-"$SOURCE_VERSION"}
OUT_DIR=${2:-"$ROOT/dist"}
[ "$VERSION" = "$SOURCE_VERSION" ] || { echo "Version must match version.py: $SOURCE_VERSION" >&2; exit 2; }
python3 "$ROOT/tools/build_integration_plg.py" "$OUT_DIR"
cp "$OUT_DIR/payload.tar.gz" "$OUT_DIR/rp2040-fan-control-$VERSION-payload.tar.gz"
(cd "$OUT_DIR" && sha256sum "rp2040-fan-control-$VERSION-payload.tar.gz" > "rp2040-fan-control-$VERSION-payload.tar.gz.sha256")
