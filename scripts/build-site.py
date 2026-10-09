"""Build the static site from versioned artifacts and shared measured metrics."""
from pathlib import Path
from html import escape
import hashlib
import json
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path.home() / 'Apps/apps-portal/site'))
from perf_block import standalone_section
import product_facts

version = (ROOT / 'VERSION').read_text().strip()
release = json.loads((ROOT / 'perf/release.json').read_text())
assert release['version'] == version, 'Release evidence must match VERSION'
package = next(asset for asset in release['assets']
               if asset['name'] == f'MacKit-{version}-arm64.dmg')
release_url = f'https://github.com/zengtianli/mackit/releases/tag/v{version}'
media = ROOT / 'site/media'
meta = json.loads((media / 'manifest.json').read_text())
perf = json.loads((ROOT / 'perf/lightweight.json').read_text())
measured_version = perf['version'].split(' ')[0]
measured_build = perf['version'].partition(' (')[2].removesuffix(')')
local_measurement = (measured_version == version and measured_build
                     and measured_build != str(release.get('build', '')))
historical = measured_version != version
# Render the measured version faithfully, including unmeasured values/reasons.
block = standalone_section(ROOT / 'perf/lightweight.json', measured_version, accent='#476d59')
if historical or local_measurement:
    label = '历史实测' if historical else '本地验收构建'
    scope = (f"<p>{label} {escape(perf['version'])} 的运行实测；当前公开发行 "
             f"v{version} ({escape(str(release.get('build', '')))})。"
             "以下运行指标不代表当前公开发行；下载大小取公开 DMG。"
             "当前安装版本的运行资源未测，本轮只整理站点，未重新采样。</p>")
    # Keep the scope statement inside the one shared-rendered resource section.
    block = block.replace("<div class='section-title'>", "<div class='section-title'>" + scope, 1)

out = ROOT / 'dist/site'
# Rebuild the public directory, so stale downloads/scripts cannot remain public.
if out.exists():
    shutil.rmtree(out)
out.mkdir(parents=True)
shutil.copy2(ROOT / 'site/style.css', out / 'style.css')
sys.path.insert(0, str(Path.home() / 'Dev/tools/dev/lib/tools/macapp'))
from product_icons import render_icon
render_icon(ROOT / 'icon/AppIcon.icns', out / 'icon.png')

page = (ROOT / 'site/index.template.html').read_text()
icon_version = hashlib.sha256((out / 'icon.png').read_bytes()).hexdigest()[:10]
page = page.replace('icon.png"', f'icon.png?v={icon_version}"')
for image_name in ('app.png', 'window.png', 'window-hotkeys.png'):
    image_version = hashlib.sha256((media / image_name).read_bytes()).hexdigest()[:10]
    page = page.replace(f'media/{image_name}', f'media/{image_name}?v={image_version}')
fields = {
    '__LIGHTWEIGHT__': block,
    '__PKG_MB__': f"{package['bytes'] / 1_000_000:.1f}",
    '__VERSION__': version,
    '__RELEASE_URL__': release_url,
    '__CHAPTER2__': str(meta['chapters'][1]['start']),
    '__CHAPTER3__': str(meta['chapters'][2]['start']),
    '__MEDIA_VERSION__': meta['version'],
}
style_version = hashlib.sha256((ROOT / 'site/style.css').read_bytes()).hexdigest()[:10]
page = page.replace('style.css?v=__VERSION__', 'style.css?v=' + style_version)
for key, value in fields.items():
    page = page.replace(key, value)
assert not re.search(r'__[A-Z0-9_]+__', page), 'Unfilled homepage placeholder'
(out / 'index.html').write_text(page)

# Reuse the native-declaration handbook rows with the script-free site template.
handbook = (ROOT / 'site/keys.html').read_text()
rows = re.search(r'<tbody>(.*?)</tbody>', handbook, re.S).group(1)
keys = (ROOT / 'site/keys.template.html').read_text().replace('__ROWS__', rows)
keys = keys.replace('style.css?v=__VERSION__', 'style.css?v=' + style_version)
assert not re.search(r'__[A-Z0-9_]+__', keys), 'Unfilled handbook placeholder'
(out / 'keys.html').write_text(keys)
shutil.copytree(media, out / 'media')
(out / 'release.json').write_text(json.dumps(release, ensure_ascii=False, indent=2) + '\n')
(out / 'SHA256SUMS').write_text(''.join(
    f"{asset['sha256']}  {asset['name']}\n" for asset in release['assets']))

# Portal-facing numbers retain the exact measurement and release scope.
facts = product_facts.from_repo(ROOT, product_id='mackit', icon='icon.png')
assert facts['version'] == version
if historical or local_measurement:
    label = '历史实测' if historical else '本地验收构建'
    facts.update(measurement_scope=label, measurement_version=perf['version'],
                 release_download_bytes=package['bytes'])
    facts['card_line'] = f"{label} {perf['version']} 实测（不代表当前公开发行 v{version}） · " + facts['card_line']
    facts['card_text'] = product_facts.card_text(facts['card_line'])
product_facts.write(out, facts)

# A digest manifest cannot hash itself; cover every other public file.
manifest = {
    'schema_version': 1,
    'product': 'mackit',
    'version': version,
    'excludes': ['site-manifest.json'],
    'files': [{'path': str(path.relative_to(out)),
               'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
              for path in sorted(out.rglob('*')) if path.is_file()],
}
(out / 'site-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
print(out)
