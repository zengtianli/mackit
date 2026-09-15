#!/bin/bash
# Standalone macOS application. Local Xcode selection reuses the shared resolver;
# public builders can use their selected Xcode with xcrun normally.
set -euo pipefail
MACKIT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$MACKIT_DIR"
if [ -f "$HOME/Dev/tools/dev/lib/tools/macapp/xcode_env.sh" ]; then
  source "$HOME/Dev/tools/dev/lib/tools/macapp/xcode_env.sh"
  xcode_env_use macosx
fi
PYTHON="${MACKIT_BUILD_PYTHON:-$MACKIT_DIR/build/app-venv/bin/python}"
if [ ! -x "$PYTHON" ]; then
  echo 'Create the build environment first: uv venv --python 3.12 build/app-venv && uv pip install --python build/app-venv/bin/python pyinstaller==6.22.0' >&2
  exit 1
fi
VERSION="$(cat VERSION)"
ARCH="$(uname -m)"
APP="$MACKIT_DIR/build/app/Tianli MacKit.app"
IDENTITY="${MACKIT_SIGN_IDENTITY:--}"
mkdir -p build/native dist/releases
xcrun swiftc -swift-version 5 -O -parse-as-library -target "$ARCH-apple-macos14.0" -sdk "$(xcrun --sdk macosx --show-sdk-path)" macos/Sources/*.swift -o build/native/MacKit
SIGN_ARGS=()
if [ "$IDENTITY" != '-' ]; then SIGN_ARGS=(--codesign-identity "$IDENTITY"); fi
"$PYTHON" -m PyInstaller --noconfirm --clean --onedir --name mackit --paths "$MACKIT_DIR" --distpath build/frozen --workpath build/pyinstaller --specpath build --target-arch "$ARCH" "${SIGN_ARGS[@]}" bin/mackit
python3 scripts/build-release.py
python3 scripts/assemble-app.py
cp build/native/MacKit "$APP/Contents/MacOS/MacKit"
cp macos/Resources/AppIcon.icns "$APP/Contents/Resources/AppIcon.icns"
if [ "$IDENTITY" = '-' ]; then
  codesign --force --deep --sign - "$APP"
else
  codesign --force --options runtime --timestamp --sign "$IDENTITY" "$APP/Contents/MacOS/MacKit"
  codesign --force --options runtime --timestamp --sign "$IDENTITY" "$APP"
fi
codesign --verify --deep --strict "$APP"
printf '%s\n' "$APP"
echo "Use scripts/package-app.sh after validation and notarization."
