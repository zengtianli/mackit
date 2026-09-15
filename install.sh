#!/bin/sh
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if ! command -v python3 >/dev/null 2>&1; then
 echo "MacKit needs Python 3.11+. Install with: brew install python" >&2; exit 1
fi
python3 -c 'import sys; assert sys.version_info >= (3,11), "MacKit needs Python 3.11+"'
if [ "${1:-}" = "--apply" ]; then
 shift
 exec python3 "$HERE/bin/mackit" apply "$@"
fi
python3 "$HERE/bin/mackit" plan "$@"
echo ""
echo "Preview only. To install with backups: ./install.sh --apply"

