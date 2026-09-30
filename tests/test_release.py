"""Release metadata must bind to the built executable, not packaging-time HEAD."""
import copy
import os
import sys
import hashlib
import importlib.util
from pathlib import Path
import plistlib
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("release_checksums", ROOT / "scripts/release-checksums.py")
RELEASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RELEASE)
INSTALL_SPEC = importlib.util.spec_from_file_location("install_app", ROOT / "scripts/install-app.py")
INSTALL = importlib.util.module_from_spec(INSTALL_SPEC)
INSTALL_SPEC.loader.exec_module(INSTALL)


class ReleaseProvenanceTests(unittest.TestCase):
    def test_receipt_binding_and_rejection_of_stale_or_dirty_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            app = Path(directory)
            (app / "Contents/MacOS").mkdir(parents=True)
            binary = app / "Contents/MacOS/MacKit"
            binary.write_bytes(b"build fixture")
            version = (ROOT / "VERSION").read_text().strip()
            (app / "Contents/Info.plist").write_bytes(plistlib.dumps({
                "CFBundleShortVersionString": version, "CFBundleVersion": version,
                "CFBundleIdentifier": "cyou.tianli.mackit"}))
            commit = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
            receipt = {"artifact": {"version": version, "build": version,
                "bundle_id": "cyou.tianli.mackit", "executable": "Contents/MacOS/MacKit",
                "sha256": hashlib.sha256(binary.read_bytes()).hexdigest()},
                "source": {"commit": commit, "dirty": False, "sha256": "source-fixture"}}
            self.assertEqual(RELEASE.provenance(ROOT, app, receipt)["source_commit"], commit)
            dirty = copy.deepcopy(receipt)
            dirty["source"]["dirty"] = True
            with self.assertRaisesRegex(ValueError, "clean, committed"):
                RELEASE.provenance(ROOT, app, dirty)
            binary.write_bytes(b"different build")
            with self.assertRaisesRegex(ValueError, "executable"):
                RELEASE.provenance(ROOT, app, receipt)


class RenameMigrationTests(unittest.TestCase):
    """Installing MacKit.app moves the pre-0.3.5 'Tianli MacKit.app' to the Trash and keeps `mackit` working."""
    def app(self, path, bundle_id="cyou.tianli.mackit"):
        (path / "Contents/MacOS").mkdir(parents=True)
        (path / "Contents/MacOS/MacKit").write_bytes(b"x")
        (path / "Contents/Resources/core/bin").mkdir(parents=True)
        (path / "Contents/Info.plist").write_bytes(plistlib.dumps({"CFBundleIdentifier": bundle_id,
            "CFBundleExecutable": "MacKit", "CFBundleShortVersionString": "1", "CFBundleVersion": "1"}))
        return path

    def run_link(self, home):
        def run(args, **kwargs):  # the real CLI's link, from the source checkout
            return subprocess.run([sys.executable, str(ROOT / "bin/mackit"), "--home", str(home), "link", "--json"], **kwargs)
        return run

    def test_old_bundle_trashed_and_command_link_moved(self):
        with tempfile.TemporaryDirectory() as directory:
            apps, home = Path(directory) / "Applications", Path(directory) / "home"
            new = self.app(apps / "MacKit.app")
            old = self.app(apps / "Tianli MacKit.app")
            link = home / ".local/bin/mackit"
            link.parent.mkdir(parents=True)
            link.symlink_to(str(old / INSTALL.ENGINE))
            done = INSTALL.migrate_legacy(apps, new, home, "stamp", run=self.run_link(home))
            self.assertFalse(old.exists())
            self.assertTrue((home / ".Trash/mackit-rename-stamp/Tianli MacKit.app/Contents/Info.plist").is_file())
            self.assertEqual(done["command_link"]["changed"], 1)
            self.assertFalse(os.readlink(link).startswith(str(old)))

    def test_unrelated_link_and_other_bundle_left_alone(self):
        with tempfile.TemporaryDirectory() as directory:
            apps, home = Path(directory) / "Applications", Path(directory) / "home"
            new = self.app(apps / "MacKit.app")
            other = self.app(apps / "Tianli MacKit.app", bundle_id="example.other")
            link = home / ".local/bin/mackit"
            link.parent.mkdir(parents=True)
            link.symlink_to("/somewhere/else/mackit")
            done = INSTALL.migrate_legacy(apps, new, home, "stamp", run=self.run_link(home))
            self.assertEqual(done, {"moved": [], "command_link": "unchanged"})
            self.assertTrue(other.exists())
            self.assertEqual(os.readlink(link), "/somewhere/else/mackit")

