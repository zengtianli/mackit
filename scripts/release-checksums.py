"""Record checksums and verified build provenance without rebuilding any asset."""
from pathlib import Path
import hashlib
import json
import plistlib
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def provenance(root, app, receipt):
    """A packaging-time HEAD is not necessarily the commit that built the App."""
    artifact, source = receipt["artifact"], receipt["source"]
    info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
    version = (root / "VERSION").read_text().strip()
    if (info["CFBundleShortVersionString"] != version
            or artifact["version"] != version
            or artifact["build"] != info["CFBundleVersion"]
            or artifact["bundle_id"] != info["CFBundleIdentifier"]):
        raise ValueError("App identity/version does not match VERSION and build receipt")
    digest = hashlib.sha256((app / artifact["executable"]).read_bytes()).hexdigest()
    if digest != artifact["sha256"]:
        raise ValueError("App executable does not match build receipt")
    commit = source.get("commit", "")
    if source.get("dirty") is not False or not source.get("sha256") or len(commit) != 40:
        raise ValueError("A clean, committed build receipt is required")
    result = subprocess.run(["git", "-C", str(root), "rev-parse", "--verify", commit + "^{commit}"],
                            capture_output=True, text=True, check=True)
    if result.stdout.strip() != commit:
        raise ValueError("Build source commit cannot be resolved")
    return {"version": version, "build": artifact["build"], "source_commit": commit,
            "source_sha256": source["sha256"], "executable_sha256": digest,
            "build_receipt": "perf/build-receipt.json"}


def main():
    out = ROOT / "dist/releases"
    receipt = json.loads((ROOT / "perf/build-receipt.json").read_text())
    record = provenance(ROOT, ROOT / "build/app/MacKit.app", receipt)
    version = record["version"]
    files = sorted(p for p in out.iterdir() if p.is_file() and version in p.name
                   and p.suffix in (".zip", ".dmg", ".gz"))
    if not files:
        raise ValueError("No release assets found; no metadata was written")
    rows = [{"name": p.name, "bytes": p.stat().st_size,
             "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]
    record["assets"] = rows
    content = json.dumps(record, indent=2) + "\n"
    (out / "SHA256SUMS").write_text("".join(r["sha256"] + "  " + r["name"] + "\n" for r in rows))
    (out / "release.json").write_text(content)
    (ROOT / "perf/release.json").write_text(content)
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
