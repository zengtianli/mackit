#!/usr/bin/env python3
"""Compile the actual Mac app and exercise its nonactivating in-process UI self-test."""
import json
import hashlib
import os
from pathlib import Path
import platform
import plistlib
import shlex
import shutil
import subprocess
import sys

from _common import ROOT, OUT_DIR, finish, isolated_home


def source_candidate():
    build = ROOT / "build/accept-native-ui"
    app = build / "MacKit UI Acceptance.app"
    contents = app / "Contents"
    resources = contents / "Resources"
    executable = contents / "MacOS/MacKit"
    executable.parent.mkdir(parents=True, exist_ok=True)
    engine = resources / "core/bin/mackit"
    engine.parent.mkdir(parents=True, exist_ok=True)
    # Use current source, not an old installed/frozen engine. Only the test bundle gets this wrapper.
    engine.write_text("#!/bin/sh\nexec " + shlex.quote(sys.executable) + " "
                      + shlex.quote(str(ROOT / "bin/mackit")) + ' "$@"\n')
    engine.chmod(0o755)
    info = plistlib.loads((ROOT / "macos/Info.plist").read_bytes())
    info.update(CFBundleIdentifier="cyou.tianli.mackit.ui-acceptance", LSUIElement=True,
                CFBundleShortVersionString=(ROOT / "VERSION").read_text().strip())
    (contents / "Info.plist").write_bytes(plistlib.dumps(info))
    shutil.copy2(ROOT / "icon/AppIcon.icns", resources / "AppIcon.icns")
    sdk = subprocess.check_output(["xcrun", "--sdk", "macosx", "--show-sdk-path"], text=True).strip()
    command = ["xcrun", "swiftc", "-swift-version", "5", "-Onone", "-parse-as-library",
               "-target", platform.machine() + "-apple-macos14.0", "-sdk", sdk,
               *map(str, sorted((ROOT / "macos/Sources").glob("*.swift"))), "-o", str(executable)]
    subprocess.run(command, cwd=ROOT, check=True, timeout=120)
    return app


def main():
    installed = os.environ.get("MACKIT_ACCEPT_APP")
    app = Path(installed).resolve() if installed else source_candidate()
    executable = app / "Contents/MacOS/MacKit"
    if installed:
        receipt = json.loads((ROOT / "perf/build-receipt.json").read_text())
        info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
        assert info["CFBundleIdentifier"] == receipt["artifact"]["bundle_id"]
        assert info["CFBundleShortVersionString"] == (ROOT / "VERSION").read_text().strip()
        assert info["CFBundleVersion"] == receipt["artifact"]["build"]
        assert hashlib.sha256(executable.read_bytes()).hexdigest() == receipt["artifact"]["sha256"]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with isolated_home() as home:
        env = os.environ.copy()
        # Keep process HOME real so the app's production demo guard remains active;
        # the engine always receives the isolated --home explicitly.
        env.update(SOP_OUT_DIR=str(OUT_DIR.resolve()), PYTHONDONTWRITEBYTECODE="1")
        result = subprocess.run([str(executable), "--ui-self-test", "--demo-home", home],
                                cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
        data = json.loads(result.stdout)
        assert data["ok"] and all(data["checks"].values()), data
        assert len(data["screenshots"]) == 5
        for name in data["screenshots"]:
            assert (OUT_DIR / name).stat().st_size > 10000
        data["artifact"] = "installed receipt-matched application" if installed else "source-built acceptance candidate"
        finish("native_ui", f"原生界面进程内自检通过：{len(data['checks'])} 项断言、5 页离屏截图；未显示窗口或操作输入。", **data)


if __name__ == "__main__":
    main()
