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
for name in ('style.css', 'keys.html'):
    shutil.copy2(ROOT / 'site' / name, out / name)
sys.path.insert(0, str(Path.home() / 'Dev/tools/dev/lib/tools/macapp'))
from product_icons import render_icon
render_icon(ROOT / 'icon/AppIcon.icns', out / 'icon.png')
(out / 'icon.svg').unlink(missing_ok=True)
perf = json.loads((ROOT / 'perf/lightweight.json').read_text())
reuse = perf.get('reuse') or {}
reference_note = ''
if str(perf['version']) != version:
    if reuse.get('release_version') != version or reuse.get('scope') != 'icon_only':
        raise SystemExit('Resource evidence is from another version without an explicit icon-only reference')
    reference_note = (f"下列为 v{perf['version']} 原版实测参考。v{version} 仅更新应用图标，"
                      "界面与业务代码未变；本轮未重新测量运行性能。当前安装包大小见下载区。")
block = standalone_section(ROOT / 'perf/lightweight.json', str(perf['version']), accent='#476d59')
if reference_note:
    block = block.replace('资源占用与响应速度。', '原版资源实测参考。')
    block = block.replace('数字来自所列设备实测，版本更新后重新测量。', '数字来自所列设备与版本的实测。')
    block = block.replace("<div class='perf-grid'>", f"<p>{reference_note}</p><div class='perf-grid'>", 1)
package = ROOT / 'dist/releases' / f'MacKit-{version}-arm64.dmg'
page = (ROOT / 'site/index.template.html').read_text()
page = page.replace('icon.svg', 'icon.png').replace('type="image/svg+xml"', 'type="image/png"')
icon_version = hashlib.sha256((out / 'icon.png').read_bytes()).hexdigest()[:10]
page = page.replace('icon.png"', f'icon.png?v={icon_version}"')
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
from perf_block import readme_block, summarize, update_readme
summary = summarize(perf, ROOT / 'perf/lightweight.json')
for name, lang in (('README.md', 'zh'), ('README_EN.md', 'en')):
    readme = ROOT / name
    rendered = readme_block(summary, lang)
    if reference_note:
        if lang == 'zh':
            note = reference_note
            rendered = rendered.replace('## 资源占用', '## 原版资源实测参考').replace('数字来自所列设备实测，版本更新后重新测量。', '数字来自所列设备与版本的实测。')
        else:
            note = (f"The figures below are reference measurements from v{perf['version']}. "
                    f"v{version} updates only the app icon; UI and business code are unchanged. "
                    "Runtime performance was not re-measured. See the download section for the current package size.")
            rendered = rendered.replace('## Resource use', '## Original-version resource reference').replace('Measured on the listed device; re-measured for each version.', 'Measured on the listed device and version.')
        rendered = rendered.replace('\n\n|', '\n\n' + note + '\n\n|', 1)
    update_readme(readme, rendered)
print(out)
