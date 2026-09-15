"""Create standalone, allowlisted configuration archives and checksums."""
from pathlib import Path
import hashlib,tarfile,zipfile
ROOT=Path(__file__).resolve().parents[1]
version=(ROOT/"VERSION").read_text().strip();prefix="mackit-v"+version
dist=ROOT/"dist/releases";dist.mkdir(parents=True,exist_ok=True)
roots=["bin","mackit","components","profiles","data","docs","tests","install.sh","VERSION","LICENSE","THIRD_PARTY.md","README.md","README_CN.md"]
files=[]
for name in roots:
 p=ROOT/name
 files.extend([p] if p.is_file() else [f for f in p.rglob("*") if (f.is_file() or f.is_symlink()) and "__pycache__" not in f.parts and f.name!=".DS_Store" and f.suffix!=".pyc"])
with tarfile.open(dist/(prefix+".tar.gz"),"w:gz") as archive:
 for f in sorted(files):archive.add(f,arcname=prefix+"/"+str(f.relative_to(ROOT)),recursive=False)
# ZIP symlinks are materialized so Finder extraction works without Unix symlink support.
with zipfile.ZipFile(dist/(prefix+".zip"),"w",zipfile.ZIP_DEFLATED) as archive:
 for f in sorted(files):
  if f.is_dir():
   for child in f.rglob("*"):
    if child.is_file():archive.write(child,prefix+"/"+str(child.relative_to(ROOT)))
  else:archive.write(f,prefix+"/"+str(f.relative_to(ROOT)))
sums="".join(hashlib.sha256((dist/name).read_bytes()).hexdigest()+"  "+name+"\n" for name in [prefix+".tar.gz",prefix+".zip"])
(dist/"SHA256SUMS").write_text(sums)
print(sums,end="")
