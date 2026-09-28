#!/bin/bash
# Maintainer deployment; reuses the station deployment engine.
set -euo pipefail
MACKIT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$MACKIT_DIR"
python3 scripts/build-handbook.py
python3 scripts/build-site.py
source "${DEPLOY_LIB:-$HOME/Dev/tools/dev/lib/deploy}/core.sh"
vps_load
rsync -az --delete "$MACKIT_DIR/dist/site/" "$VPS:/var/www/mackit-next/"
had_previous="$(ssh "$VPS" 'set -eu; test -s /var/www/mackit-next/index.html; test -s /var/www/mackit-next/media/tutorial.mp4; previous=no; if [ -d /var/www/mackit ]; then if [ -d /var/www/mackit-previous ]; then mv /var/www/mackit-previous /var/www/mackit-previous-$(date +%Y%m%d%H%M%S)-$$; fi; mv /var/www/mackit /var/www/mackit-previous; previous=yes; fi; mv /var/www/mackit-next /var/www/mackit; printf "%s\n" "$previous"')"
if http_verify_edge mackit.tianli.cyou / --expect 200; then
    exit 0
else
    verify_status=$?
fi
# Only restore the previous site saved by this successful swap, never a stale backup.
if [ "$had_previous" = yes ]; then
    if ssh "$VPS" 'set -eu; test -d /var/www/mackit-previous; mv /var/www/mackit /var/www/mackit-failed-$(date +%Y%m%d%H%M%S)-$$; mv /var/www/mackit-previous /var/www/mackit'; then
        echo "MacKit verification failed; restored the previous site and preserved the failed deployment." >&2
    else
        echo "MacKit verification failed and rollback failed; inspect /var/www/mackit* on the deployment host." >&2
    fi
else
    echo "MacKit verification failed; no previous site was saved by this deployment." >&2
fi
exit "$verify_status"
