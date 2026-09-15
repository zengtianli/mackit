"""Build a complete static site from versioned sources and release artifacts."""
from pathlib import Path
import json,shutil
ROOT=Path(__file__).resolve().parents[1];out=ROOT/"dist/site"
out.mkdir(parents=True,exist_ok=True)
version=(ROOT/"VERSION").read_text().strip()
media=ROOT/"site/media";meta=json.loads((media/"manifest.json").read_text())
for name in ["style.css","icon.svg","keys.html"]:shutil.copy2(ROOT/"site"/name,out/name)
page=(ROOT/"site/index.template.html").read_text().replace("__VERSION__",version).replace("__CHAPTER2__",str(meta["chapters"][1]["start"])).replace("__CHAPTER3__",str(meta["chapters"][2]["start"]))
(out/"index.html").write_text(page)
shutil.copytree(media,out/"media",dirs_exist_ok=True)
shutil.copytree(ROOT/"dist/releases",out/"downloads",dirs_exist_ok=True)
assert "__VERSION__" not in page
print(out)
