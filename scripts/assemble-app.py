"""Assemble from the public source archive and the frozen, relocatable engine."""
from pathlib import Path
import plistlib, shutil, tarfile,subprocess
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
python_license=subprocess.check_output([str(ROOT/"build/app-venv/bin/python"),"-c","import sys;from pathlib import Path;print(Path(sys.base_prefix)/'lib/python3.12/LICENSE.txt')"],text=True).strip()
shutil.copy2(python_license,resources/"Python-LICENSE.txt")
plist=(ROOT/"macos/Info.plist").read_text().replace("__VERSION__",version)
(app/"Contents/Info.plist").write_text(plist)
plistlib.loads(plist.encode())
print(app)
