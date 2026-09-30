"""Install the signed, notarized current build as /Applications/MacKit.app without launching it.

Maintainer release step (after build-app.sh with MACKIT_SIGN_IDENTITY, notarization and staple).
It never changes configuration: the only user-level change is re-pointing ~/.local/bin/mackit
when it still points into the pre-0.3.5 bundle name, done by the new App's own `mackit link`
(a recorded transaction that `mackit restore` undoes).

Migration from 'Tianli MacKit.app' (the name used up to 0.3.4, same bundle id):
the old copy is moved to ~/.Trash/mackit-rename-<stamp>/, not deleted.
"""
import datetime
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
NAME = "MacKit.app"
LEGACY_NAMES = ("Tianli MacKit.app",)
ENGINE = "Contents/Resources/core/bin/mackit"


def inspect(app):
    info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
    binary = app / "Contents/MacOS" / info["CFBundleExecutable"]
    return {"version": info["CFBundleShortVersionString"], "build": info["CFBundleVersion"],
            "bundle_id": info["CFBundleIdentifier"],
            "sha256": hashlib.sha256(binary.read_bytes()).hexdigest()}


def running(app):
    processes = subprocess.check_output(["ps", "-axo", "comm="], text=True).splitlines()
    return any(str(app / "Contents/MacOS/MacKit") == p.strip() for p in processes)


def migrate_legacy(applications, target, home, stamp, run=subprocess.run):
    """Move older same-bundle copies to the Trash and keep the mackit command working.

    Returns what was done. Only apps with the new bundle's identifier are moved; the command
    link is re-pointed only when it points into one of those old copies."""
    bundle_id = inspect(target)["bundle_id"]
    done = {"moved": [], "command_link": "unchanged"}
    link = home / ".local/bin/mackit"
    for name in LEGACY_NAMES:
        old = applications / name
        if not old.is_dir() or old.is_symlink() or inspect(old)["bundle_id"] != bundle_id:
            continue
        points_old = link.is_symlink() and os.readlink(link).startswith(str(old) + "/")
        if points_old:
            # The new App's own command records the change (mackit restore <transaction> undoes it).
            result = run([str(target / ENGINE), "--home", str(home), "link", "--json"],
                         capture_output=True, text=True, timeout=60)
            if result.returncode:
                raise SystemExit("mackit link failed; the old App was left in place: " + (result.stdout + result.stderr).strip())
            done["command_link"] = json.loads(result.stdout)
        trash = home / ".Trash" / f"mackit-rename-{stamp}"
        trash.mkdir(parents=True, exist_ok=True)
        try:
            os.rename(old, trash / name)
        except OSError:
            shutil.move(str(old), str(trash / name))
        done["moved"].append({"from": str(old), "to": str(trash / name)})
    return done


def main():
    applications = Path("/Applications")
    source = ROOT / "build/app" / NAME
    target = applications / NAME
    receipt = json.loads((ROOT / "perf/build-receipt.json").read_text())
    version = (ROOT / "VERSION").read_text().strip()
    expected = inspect(source)
    assert expected["version"] == version
    assert all(expected[k] == receipt["artifact"][k] for k in expected)
    subprocess.run(["codesign", "--verify", "--deep", "--strict", str(source)], check=True)
    subprocess.run(["xcrun", "stapler", "validate", str(source)], check=True)
    for app in [target, *(applications / n for n in LEGACY_NAMES)]:
        if app.exists() and running(app):
            raise SystemExit(f"{app.name} is running; preserve its session and retry after it closes.")
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    if target.exists() and inspect(target) == expected:
        print("The current build is already installed.")
    else:
        assert not target.is_symlink()
        if target.exists():
            assert inspect(target)["bundle_id"] == expected["bundle_id"]
        backup = ROOT / "build/installed-backup" / stamp / target.name
        stage = ROOT / "build/install-stage" / stamp / target.name
        stage.parent.mkdir(parents=True)
        subprocess.run(["ditto", str(source), str(stage)], check=True)
        subprocess.run(["codesign", "--verify", "--deep", "--strict", str(stage)], check=True)
        assert inspect(stage) == expected
        backup.parent.mkdir(parents=True)
        if target.exists():
            os.rename(target, backup)
        try:
            os.rename(stage, target)
            assert inspect(target) == expected
        except BaseException:
            if not target.exists() and backup.exists():
                os.rename(backup, target)
            raise
    subprocess.run(["codesign", "--verify", "--deep", "--strict", str(target)], check=True)
    subprocess.run(["xcrun", "stapler", "validate", str(target)], check=True)
    migration = migrate_legacy(applications, target, Path.home(), stamp)
    result = {"version": version, "artifact": inspect(target), "build_receipt": "perf/build-receipt.json",
              "installed_app": str(target), "legacy_migration": migration,
              "launched": False, "dock_finder_visual_confirmed": False}
    (ROOT / f"perf/install-receipt-{version}.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    sys.exit(main())
