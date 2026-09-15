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
ssh "$VPS" 'test -s /var/www/mackit-next/index.html && test -s /var/www/mackit-next/media/tutorial.mp4 && if [ -d /var/www/mackit ]; then if [ -d /var/www/mackit-previous ]; then mv /var/www/mackit-previous /var/www/mackit-previous-$(date +%Y%m%d%H%M%S); fi; mv /var/www/mackit /var/www/mackit-previous; fi; mv /var/www/mackit-next /var/www/mackit'
http_verify_edge mackit.tianli.cyou / --expect 200
