#!/bin/bash
set -euo pipefail
MACKIT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$MACKIT_DIR"
VERSION="$(cat VERSION)"
ARCH="$(uname -m)"
APP="$MACKIT_DIR/build/app/Tianli MacKit.app"
codesign --verify --deep --strict "$APP"
STAGE="$MACKIT_DIR/build/dmg-stage"
python3 - <<'PY'
from pathlib import Path
import shutil
p=Path('build/dmg-stage')
if p.exists():
    if p.is_symlink():raise ValueError('Linked staging directory')
    shutil.rmtree(p)
p.mkdir()
PY
ditto "$APP" "$STAGE/Tianli MacKit.app"
ln -s /Applications "$STAGE/Applications"
DMG="$MACKIT_DIR/dist/releases/MacKit-$VERSION-$ARCH.dmg"
if [ -e "$DMG" ]; then mv "$DMG" "$MACKIT_DIR/build/previous-MacKit.dmg"; fi
hdiutil create -volname "Tianli MacKit" -srcfolder "$STAGE" -ov -format UDZO "$DMG"
ditto -c -k --sequesterRsrc --keepParent "$APP" "$MACKIT_DIR/dist/releases/MacKit-$VERSION-$ARCH.zip"
python3 scripts/release-checksums.py
printf '%s\n' "$DMG"
