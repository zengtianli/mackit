"""Build the static site from versioned artifacts and shared measured metrics."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path.home() / 'Apps/apps-portal/site'))
from perf_block import standalone_section

out = ROOT / 'dist/site'
out.mkdir(parents=True, exist_ok=True)
version = (ROOT / 'VERSION').read_text().strip()
media = ROOT / 'site/media'
meta = json.loads((media / 'manifest.json').read_text())
for name in ('style.css', 'icon.svg', 'keys.html'):
    shutil.copy2(ROOT / 'site' / name, out / name)
sys.path.insert(0, str(Path.home() / 'Dev/tools/dev/lib/tools/macapp'))
from product_icons import render_icon
render_icon(ROOT / 'macos/Resources/AppIcon.icns', out / 'icon.png')
perf = json.loads((ROOT / 'perf/lightweight.json').read_text())
block = standalone_section(ROOT / 'perf/lightweight.json', version, accent='#476d59')
page = (ROOT / 'site/index.template.html').read_text()
page = page.replace('icon.svg', 'icon.png').replace('type="image/svg+xml"', 'type="image/png"')
fields = {
    '__LIGHTWEIGHT__': block,
    '__PKG_MB__': f"{perf['size']['download_bytes'] / 1_000_000:.1f}",
    '__VERSION__': version,
    '__CHAPTER2__': str(meta['chapters'][1]['start']),
    '__CHAPTER3__': str(meta['chapters'][2]['start']),
    '__MEDIA_VERSION__': meta['version'],
}
style_version = hashlib.sha256((ROOT / 'site/style.css').read_bytes()).hexdigest()[:10]
page = page.replace('style.css?v=__VERSION__', 'style.css?v=' + style_version)
keys = out / 'keys.html'
keys.write_text(re.sub(r'style\.css\?v=[^"\s]+', 'style.css?v=' + style_version, keys.read_text()))
for key, value in fields.items():
    page = page.replace(key, value)
assert '__VERSION__' not in page and '__PERF' not in page and '_MB__' not in page and '_MS__' not in page
(out / 'index.html').write_text(page)
shutil.copytree(media, out / 'media', dirs_exist_ok=True)
shutil.copytree(ROOT / 'dist/releases', out / 'downloads', dirs_exist_ok=True)
import subprocess
subprocess.run([sys.executable, str(Path.home() / 'Apps/apps-portal/site/perf_block.py'), str(ROOT)], check=True)
print(out)
