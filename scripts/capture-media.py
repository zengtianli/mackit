"""Re-capture the product page's app screenshots offscreen from the installed release (Chapter sop.capture).

    python3 scripts/capture-media.py

Builds build/media-capture/MacKit Media Capture.app from macos/Sources plus scripts/capture/main.swift (the
production views; the App's own @main in UISelfTest.swift is left out) with a private bundle id and LSUIElement,
whose engine is a one-line wrapper around the installed /Applications/MacKit.app engine. Each screenshot is a
separate process started with the App's own `-page` / `-section` verification arguments on the real HOME
(read-only snapshot and window status). The window sits outside every display, never becomes key or active,
and receives no input; the window server composites it and the process reads back its own window only.

Writes site/media/app.png, window.png, window-hotkeys.png, perf/media-capture.json and the app_screenshots
record in site/media/manifest.json. The CLI replay video and terminal.png are not touched.
Exit 75 (defer) when the installed App is not the current VERSION: screenshots must show the released build.
"""
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import plistlib
import shlex
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
INSTALLED = Path(os.environ.get("MACKIT_CAPTURE_APP", "/Applications/MacKit.app"))
DEFER = 75
SHOTS = [("app.png", ["-page", "keys"]),
         ("window.png", ["-page", "window"]),
         ("window-hotkeys.png", ["-page", "window", "-section", "hotkeys"])]
METHOD = ("Production SwiftUI views (macos/Sources) in a window outside every display that never becomes key or "
          "active; window-server image of the capture process's own window. Installed release engine on the real "
          "HOME (read-only snapshot). No input events, activation or screen recording.")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build(version):
    app = ROOT / "build/media-capture/MacKit Media Capture.app"
    if app.exists():
        shutil.rmtree(app)
    contents = app / "Contents"
    (contents / "MacOS").mkdir(parents=True)
    engine = contents / "Resources/core/bin/mackit"
    engine.parent.mkdir(parents=True)
    engine.write_text("#!/bin/sh\nexec " + shlex.quote(str(INSTALLED / "Contents/Resources/core/bin/mackit")) + ' "$@"\n')
    engine.chmod(0o755)
    info = plistlib.loads((ROOT / "macos/Info.plist").read_bytes())
    info.update(CFBundleIdentifier="cyou.tianli.mackit.media-capture", LSUIElement=True,
                CFBundleShortVersionString=version, CFBundleExecutable="MacKit")
    (contents / "Info.plist").write_bytes(plistlib.dumps(info))
    shutil.copy2(ROOT / "icon/AppIcon.icns", contents / "Resources/AppIcon.icns")
    sources = sorted(p for p in (ROOT / "macos/Sources").glob("*.swift") if p.name != "UISelfTest.swift")
    sdk = subprocess.check_output(["xcrun", "--sdk", "macosx", "--show-sdk-path"], text=True).strip()
    subprocess.run(["xcrun", "swiftc", "-swift-version", "5", "-O", "-parse-as-library",
                    "-target", platform.machine() + "-apple-macos14.0", "-sdk", sdk,
                    *map(str, sources), str(ROOT / "scripts/capture/main.swift"),
                    "-o", str(contents / "MacOS/MacKit")], cwd=ROOT, check=True, timeout=600)
    subprocess.run(["codesign", "--force", "--sign", "-", str(app)], check=True, capture_output=True)
    return app, sources


def main():
    version = (ROOT / "VERSION").read_text().strip()
    try:
        installed = plistlib.loads((INSTALLED / "Contents/Info.plist").read_bytes())
    except OSError:
        print(f"{INSTALLED} is not installed; capture after installing {version}.")
        return DEFER
    if installed.get("CFBundleShortVersionString") != version:
        print(f"Installed {installed.get('CFBundleShortVersionString')} is not VERSION {version}; capture after installing it.")
        return DEFER
    app, sources = build(version)
    executable = app / "Contents/MacOS/MacKit"
    media = ROOT / "site/media"
    records = []
    with tempfile.TemporaryDirectory(prefix="mackit-capture-") as tmp:
        staged = []
        for name, args in SHOTS:
            out = Path(tmp) / name
            result = subprocess.run([str(executable), *args, "--out", str(out)], cwd=ROOT,
                                    capture_output=True, text=True, timeout=180)
            lines = [l for l in result.stdout.splitlines() if l.startswith("{")]
            data = json.loads(lines[-1]) if lines else {"ok": False, "error": (result.stdout + result.stderr)[-800:]}
            if result.returncode or not data.get("ok"):
                raise SystemExit(f"{name}: {data.get('error')}")
            if (data["width"], data["height"]) != (1080, 790) or out.stat().st_size < 50_000:
                raise SystemExit(f"{name}: unexpected image {data['width']}x{data['height']} {out.stat().st_size} B")
            if data["on_screen"] or data["key"] or data["active"] or data["app_version"] != version:
                raise SystemExit(f"{name}: capture conditions not met: {data}")
            staged.append((name, out))
            records.append({"file": "site/media/" + name, "arguments": args, "page": data["page"], "title": data["title"],
                            "window_frame": data["window_frame"], "width": data["width"], "height": data["height"],
                            "app_version": data["app_version"], "captured_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds")})
        for (name, out), record in zip(staged, records):
            shutil.copyfile(out, media / name)
            record["sha256"] = sha256(media / name)
    evidence = {"version": version, "installed_app": str(INSTALLED),
                "installed_executable_sha256": sha256(INSTALLED / "Contents/MacOS/MacKit"),
                "ui_sources_sha256": {str(p.relative_to(ROOT)): sha256(p) for p in sources},
                "method": METHOD, "records": records}
    (ROOT / "perf/media-capture.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
    manifest_path = media / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["app_screenshots"] = {
        "version": version, "executable_sha256": evidence["installed_executable_sha256"],
        "evidence": "../../perf/media-capture.json", "captured_at": records[-1]["captured_at"],
        "scope": "App screenshots (app.png, window.png, window-hotkeys.png) re-captured offscreen from the production "
                 "views with the installed release engine; the CLI replay video and terminal.png keep their own labelled version."}
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"ok": True, "version": version, "files": [r["file"] for r in records]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
