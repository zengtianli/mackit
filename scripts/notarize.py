"""Submit a signed MacKit build to Apple notarization and wait for the verdict.

Usage: python3 scripts/notarize.py <App .zip or .dmg> <response.json>
Credentials come from the maintainer's App Store Connect API key through the shared asc helper;
nothing secret is stored here. Staple and validate separately after an Accepted verdict.
"""
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path.home() / 'Dev/tools/dev/lib/tools/macapp/ios'))
import asc

kid = asc._personal_env('ASC_KEY_ID')
issuer = asc._personal_env('ASC_ISSUER_ID')
key = Path.home() / '.appstoreconnect/private_keys' / f'AuthKey_{kid}.p8'
result = subprocess.run(['xcrun', 'notarytool', 'submit', sys.argv[1], '--key', str(key),
                         '--key-id', kid, '--issuer', issuer, '--wait', '--timeout', '5m',
                         '--output-format', 'json'], capture_output=True, text=True, timeout=360)
Path(sys.argv[2]).write_text(result.stdout)
if result.stderr:
    Path(sys.argv[2] + '.stderr').write_text(result.stderr)
if result.returncode:
    print('Notarization did not complete; inspect the saved local response before retrying.')
    sys.exit(result.returncode)
data = json.loads(result.stdout)
print(json.dumps({k: data.get(k) for k in ('id', 'status', 'message')}))
sys.exit(0 if data.get('status') == 'Accepted' else 1)
