from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
version=(ROOT/"VERSION").read_text().strip();out=ROOT/"dist/releases"
files=sorted(p for p in out.iterdir() if p.is_file() and version in p.name and p.suffix in (".zip",".dmg",".gz"))
rows=[{"name":p.name,"bytes":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]
(out/"SHA256SUMS").write_text("".join(r['sha256']+"  "+r['name']+"\n" for r in rows))
(out/"release.json").write_text(json.dumps({"version":version,"assets":rows},indent=2)+"\n")
print(json.dumps(rows,indent=2))
