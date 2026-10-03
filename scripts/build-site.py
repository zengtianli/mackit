"""Build the static site from versioned artifacts and shared measured metrics."""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path.home() / 'Apps/apps-portal/site'))
from perf_block import standalone_section
import product_facts

out = ROOT / 'dist/site'
out.mkdir(parents=True, exist_ok=True)
version = (ROOT / 'VERSION').read_text().strip()
media = ROOT / 'site/media'
meta = json.loads((media / 'manifest.json').read_text())
for name in ('style.css', 'keys.html'):
    shutil.copy2(ROOT / 'site' / name, out / name)
sys.path.insert(0, str(Path.home() / 'Dev/tools/dev/lib/tools/macapp'))
from product_icons import render_icon
render_icon(ROOT / 'icon/AppIcon.icns', out / 'icon.png')
(out / 'icon.svg').unlink(missing_ok=True)
perf = json.loads((ROOT / 'perf/lightweight.json').read_text())
measured_version = perf['version'].split(' ')[0]
historical = measured_version != version and os.environ.get('APP_RELEASE_KEEP_HISTORY') == '1'
block = standalone_section(ROOT / 'perf/lightweight.json', measured_version if historical else version, accent='#476d59')
if historical:
    block = block.replace('资源占用与响应速度。', f'历史实测 · v{measured_version}。').replace('数字来自所列设备实测，版本更新后重新测量。', f'以下为 v{measured_version} 的历史实测，不代表当前 v{version}；本轮未重复采样。')
package = ROOT / 'dist/releases' / f'MacKit-{version}-arm64.dmg'
page = (ROOT / 'site/index.template.html').read_text()
page = page.replace('icon.svg', 'icon.png').replace('type="image/svg+xml"', 'type="image/png"')
icon_version = hashlib.sha256((out / 'icon.png').read_bytes()).hexdigest()[:10]
page = page.replace('icon.png"', f'icon.png?v={icon_version}"')
for image_name in ('app.png', 'window.png', 'window-hotkeys.png'):
    image_version = hashlib.sha256((media / image_name).read_bytes()).hexdigest()[:10]
    page = page.replace(f'media/{image_name}', f'media/{image_name}?v={image_version}')
fields = {
    '__LIGHTWEIGHT__': block,
    '__PKG_MB__': f"{package.stat().st_size / 1_000_000:.1f}",
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
# Portal-facing numbers, published at the homepage root with this page (products.yaml id: mackit).
facts = product_facts.from_repo(ROOT, product_id='mackit', icon='icon.png')
assert facts['version'] == version, f"facts.json version {facts['version']} (sop.release) differs from VERSION {version}"
product_facts.write(out, facts)
import subprocess
subprocess.run([sys.executable, str(Path.home() / 'Apps/apps-portal/site/perf_block.py'), str(ROOT)], check=True)
print(out)
