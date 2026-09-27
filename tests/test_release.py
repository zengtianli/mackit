"""Release metadata must bind to the built executable, not packaging-time HEAD."""
import copy
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
