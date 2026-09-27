"""Assemble from the public source archive and the frozen, relocatable engine."""
from pathlib import Path
import os, plistlib, shutil, tarfile, subprocess
ROOT=Path(__file__).resolve().parents[1]
version=(ROOT/"VERSION").read_text().strip()
app=ROOT/"build/app/Tianli MacKit.app"
if app.exists():
    if app.is_symlink():raise ValueError("Refusing to replace linked app")
    shutil.rmtree(app)
(app/"Contents/MacOS").mkdir(parents=True)
resources=app/"Contents/Resources";resources.mkdir()
with tarfile.open(ROOT/"dist/releases"/f"mackit-v{version}.tar.gz") as archive:
    archive.extractall(resources,filter="data")
(resources/f"mackit-v{version}").rename(resources/"core")
core=resources/"core"
shutil.copy2(ROOT/"build/frozen/mackit/mackit",core/"bin/mackit")
shutil.copytree(ROOT/"build/frozen/mackit/_internal",core/"bin/_internal",symlinks=True)
# Lightweight bundle: the app runs only bin/mackit, mackit, components, profiles and data
# (the same allowlist gui.ensure_source copies). Tests, docs, build scripts, the icon
# source set and READMEs stay in the public source archive, not in the installed app.
for name in ("tests","docs","scripts","macos","icon","README.md","README_EN.md"):
    target=core/name
    if target.is_dir() and not target.is_symlink():shutil.rmtree(target)
    elif target.exists():target.unlink()
# Drop the local symbol table from the embedded interpreter (about 1.7 MB); exported
# symbols stay, so extension loading and tracebacks are unchanged. The strip invalidates
# the freezer's signature: re-sign with the release identity, ad-hoc builds use --deep later.
libpython=next((core/"bin/_internal").glob("libpython*.dylib"))
subprocess.run(["strip","-x",str(libpython)],check=True)
identity=os.environ.get("MACKIT_SIGN_IDENTITY","-")
if identity!="-":subprocess.run(["codesign","--force","--options","runtime","--timestamp","--sign",identity,str(libpython)],check=True)
python_license=subprocess.check_output([str(ROOT/"build/app-venv/bin/python"),"-c","import sys;from pathlib import Path;print(Path(sys.base_prefix)/'lib/python3.12/LICENSE.txt')"],text=True).strip()
shutil.copy2(python_license,resources/"Python-LICENSE.txt")
plist=(ROOT/"macos/Info.plist").read_text().replace("__VERSION__",version)
(app/"Contents/Info.plist").write_text(plist)
plistlib.loads(plist.encode())
print(app)
