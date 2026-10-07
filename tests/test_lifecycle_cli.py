"""`mackit config …`, `mackit update check` and `mackit update install`, end to end and off screen.

The command line is the Python engine; the items of the “配置与更新…” window belong to the App bundle (its preference
domain, its version, its release channel). So the engine forwards those words to the compiled App binary, which runs
the shared command layer (macos/Sources/AppLifecycleCLI.swift) on the window's own configuration factory
(macos/Sources/Lifecycle.swift) and returns before any NSApplication exists. This test drives that chain as real
processes:

1. the engine from source forwards the words unchanged and brings stdout, stderr and the exit code back unchanged;
   plain `mackit update` keeps its own meaning;
2. the commands read and write the settings the window's configuration does (the remembered preset and components
   that `mackit select` and the 安装配置 page write), and the engine reads what a command imported;
3. `update check` reads only the isolated release record; `update install` previews, asks for --yes and then really
   replaces a throwaway bundle placed under the isolated support folder (its backup and its "Trash" are there too);
4. `config status` reports the sentence under the window's switch (`sync_status`) and says where it comes from;
5. a running App follows the command and never writes an old value back: the binary is started a second time as the
   App itself (`--lifecycle-follow-probe`: the production model and the production lifecycle wiring, activation
   policy prohibited, the shared window built but never ordered in). Every verdict also reads the stored value through
   a fresh process. Two commands back to back are part of it, for the switch and for imports made while sync is on.

Everything is isolated: a copy of the binary inside a throwaway bundle with a test bundle identifier, a throwaway
named preference domain, a temporary home, temporary support and "cloud" directories, a private notification channel.
No window is shown, nothing reaches the Dock, no network, no installed App is signalled, the owner's settings, iCloud
Drive and Karabiner are never opened.

The App binary: MACKIT_NATIVE names one (the build's compiled binary); otherwise this file compiles the current
sources into build/lifecycle-test/MacKit (never the build that gets signed and installed).
MACKIT_APP=<MacKit.app> also runs AssembledBundleTests on an assembled or installed bundle: read commands on the bundle
itself, and `update install --yes` on a re-identified copy of it, never on the bundle that was named.
"""
import hashlib
import json
import os
from pathlib import Path
import platform
import plistlib
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mackit import cli  # noqa: E402

BUNDLE = "test.tianli.mackit.lifecycle"
PRODUCT = "cyou.tianli.mackit"
SUITE_PREFIX = "test.tianli.mackit."
HEADQUARTERS = Path.home() / "Dev/tools/dev/lib/tools/macapp/swift-shared/AppLifecycleCLI.swift"
SEED = {"profile": "developer", "components": ["nvim", "zsh"]}
OFF = "iCloud 配置同步已关闭"
SWITCH = "appLifecycle.configuration.enabled"


def native_binary():
    """The compiled App binary to test: the one named by MACKIT_NATIVE, else the current sources compiled on demand."""
    named = os.environ.get("MACKIT_NATIVE")
    if named:
        return Path(named) if Path(named).is_file() else None
    sources = sorted((ROOT / "macos/Sources").glob("*.swift"))
    binary = ROOT / "build/lifecycle-test/MacKit"
    if binary.is_file() and binary.stat().st_mtime >= max(p.stat().st_mtime for p in sources):
        return binary
    try:
        sdk = subprocess.check_output(["xcrun", "--sdk", "macosx", "--show-sdk-path"], text=True, timeout=60).strip()
        binary.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["xcrun", "swiftc", "-swift-version", "5", "-Onone", "-parse-as-library", "-target",
                        platform.machine() + "-apple-macos14.0", "-sdk", sdk, *map(str, sources), "-o", str(binary)],
                       cwd=ROOT, check=True, capture_output=True, timeout=300)
    except (OSError, subprocess.SubprocessError):
        return None
    return binary


NATIVE = native_binary()


def write_selection(home, value):
    path = home / ".config/mackit/portable-preferences.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")
    path.chmod(0o600)
    return path


def sign(app):
    """An ad-hoc signature over the whole throwaway bundle: the installer verifies both the App it replaces and the new one."""
    subprocess.run(["/usr/bin/codesign", "--force", "--deep", "--sign", "-", str(app)], check=True, capture_output=True, timeout=300)


def facts(app):
    info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
    return {"version": info["CFBundleShortVersionString"], "build": info["CFBundleVersion"]}


def publish(feed, app, bundle_id, name="MacKit-next.zip"):
    """The isolated channel's release record for `app`, with the archive beside it as the private channel keeps it."""
    feed.mkdir(parents=True, exist_ok=True)
    archive = feed / name
    archive.unlink(missing_ok=True)
    subprocess.run(["/usr/bin/ditto", "-c", "-k", "--keepParent", str(app), str(archive)], check=True, capture_output=True, timeout=300)
    (feed / "release.json").write_text(json.dumps(dict(facts(app), bundle_id=bundle_id, channel="isolated", filename=name,
                                                        sha256=hashlib.sha256(archive.read_bytes()).hexdigest(), size_bytes=archive.stat().st_size)))


def body_of(done):
    return json.loads(done.stdout)


def forget(suite):
    subprocess.run(["/usr/bin/defaults", "delete", suite], capture_output=True, timeout=30)
    (Path.home() / "Library/Preferences" / (suite + ".plist")).unlink(missing_ok=True)


class Isolated:
    """What both test classes share: the command's answer as JSON, the stored values read by fresh processes, and the
    follow scenario. A subclass provides `mackit(*words, env=None, home=None, cwd=None)` (the command as typed) and
    `env`, `home`, `suite`, `root`, `cloud`, `selection`, `probe_binary`, `followers`."""

    def call(self, *words, expect=0, env=None, home=None):
        done = self.mackit(*words, "--json", env=env, home=home)
        self.assertEqual(done.returncode, expect, (words, done.stdout, done.stderr))
        body = json.loads(done.stdout)
        self.assertIs(body["ok"], expect == 0, body)
        if expect:
            self.assertTrue(body["error"]["code"] and body["error"]["message"], body)
        return body

    def stored_switch(self):
        """The stored switch, read by a process that shares no code with the App: `defaults read` of the test domain."""
        done = subprocess.run(["/usr/bin/defaults", "read", self.suite, SWITCH], capture_output=True, text=True, timeout=30)
        return done.stdout.strip() == "1" if done.returncode == 0 else False

    def exported(self, env=None):
        """The portable values as a fresh process of the command reads them."""
        done = self.mackit("config", "export", "-o", "-", env=env)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        return json.loads(done.stdout)["values"]

    def envelope(self, profile, components):
        return {"version": 1, "product": PRODUCT, "values": {"file.0.profile": profile, "file.0.components": components}}

    def follow_scenario(self):
        """A running App follows the command and never writes an old value back. `self.probe_binary` is started as the
        App itself; `self.mackit` runs the commands. Every verdict also reads the stored value through fresh processes."""
        live = dict(self.env, APP_LIFECYCLE_FOLLOW_CHANNEL="test." + uuid.uuid4().hex)
        state = self.root / "app.json"
        state.unlink(missing_ok=True)
        others = self.call("config", "status")["app_running"]  # another instance of this bundle, when the installed one is under test
        complaints = self.root / "app.err"
        with complaints.open("wb") as errors:
            process = subprocess.Popen([str(self.probe_binary), "--lifecycle-follow-probe", str(state), "--home", str(self.home)], env=live,
                                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=errors)
        self.followers.append(process)

        # time.monotonic() does not advance while the Mac sleeps: a wait that spans a sleep neither fails nor passes because of it.
        def seen():
            for _ in range(40):
                try:
                    return json.loads(state.read_text())
                except (OSError, ValueError):
                    time.sleep(0.02)
            raise AssertionError("app state unreadable: " + complaints.read_text())

        def reaches(test, seconds=8.0):
            deadline = time.monotonic() + seconds
            while time.monotonic() < deadline:
                if state.exists() and test(seen()):
                    return True
                time.sleep(0.05)
            return False

        def holds(want, seconds=1.0, app=True):
            """The stored switch (read by two fresh processes) stays put and, with `app`, so do the App's configuration and
            the window's switch. The readings that differed are kept in self.unheld, for the failure message."""
            deadline = time.monotonic() + seconds
            while time.monotonic() < deadline:
                now = seen()
                read = {"app": now["enabled"], "window": now["window_switch"]} if app else {}
                read.update({"stored": self.stored_switch(), "config status": self.call("config", "status")["sync_enabled"]})
                self.unheld = {name: value for name, value in read.items() if value is not want}
                if self.unheld:
                    return False
                time.sleep(0.05)
            return True

        self.assertTrue(reaches(lambda s: s["loaded"] and not s["busy"], 30), complaints.read_text() or "the app did not report")
        first = seen()
        # The App is running as an app, and nothing of it is on screen.
        self.assertEqual((first["policy_prohibited"], first["windows_on_screen"], first["active"], first["error"]), (True, 0, False, ""))
        self.assertTrue(all(first["window_built"].values()), first["window_built"])  # the shared window, built as the menu item builds it
        self.assertEqual((first["enabled"], first["window_switch"], first["status"]), (False, False, OFF))
        self.assertEqual((first["profile"], first["components"]), (SEED["profile"], SEED["components"]))  # the model read the seeded selection

        def sentence():
            """`sync_status` of `config status`, as a fresh process of the command reads it."""
            return self.call("config", "status", env=live)["sync_status"]

        def shows_the_apps_sentence(seconds=5.0):
            """The command reports the sentence the running App holds right now, and says it is the App's."""
            deadline = time.monotonic() + seconds
            while time.monotonic() < deadline:
                told, held = sentence(), seen()["status"]
                if (told["text"], told["from"], told["live"]) == (held, "app", True) and told["at"]:
                    return True
                time.sleep(0.05)
            return False

        # The App is running: whatever the command reports is live, and before any pass it is the closed sentence.
        at_start = sentence()
        self.assertEqual((at_start["text"], at_start["live"]), (OFF, True), at_start)
        self.assertIn(at_start["from"], ("app", "derived"))
        for attempt in range(3):
            on = self.call("config", "sync", "on", "--yes", env=live)
            self.assertTrue(on["changed"] and on["app_running"], on)  # the command saw the running App
            self.assertTrue(reaches(lambda s: s["enabled"] is True and s["window_switch"] is True and s["status"] != OFF), f"follows sync on ({attempt + 1})")
            self.assertTrue(holds(True), f"sync on is not written back ({attempt + 1})")
            self.assertTrue(shows_the_apps_sentence(), f"config status reports the running App's sentence, sync on ({attempt + 1}): {sentence()} / {seen()['status']}")
            self.assertNotEqual(sentence()["text"], OFF)
            self.call("config", "sync", "off", "--yes", env=live)
            self.assertTrue(reaches(lambda s: s["enabled"] is False and s["window_switch"] is False and s["status"] == OFF), f"follows sync off ({attempt + 1})")
            self.assertTrue(holds(False), f"sync off is not written back ({attempt + 1})")
            self.assertTrue(shows_the_apps_sentence(), f"config status reports the running App's sentence, sync off ({attempt + 1}): {sentence()}")
            self.assertEqual(sentence()["text"], OFF)
        # Two commands back to back: whatever the App does about the first must not undo the second after it has returned.
        for attempt in range(3):
            self.call("config", "sync", "on", "--yes", env=live)
            self.call("config", "sync", "off", "--yes", env=live)
            self.assertFalse(self.stored_switch(), f"off is stored when the second command returns ({attempt + 1})")
            # What must never come back is the stored switch: fresh processes read it from the moment the second command
            # returned. The window is allowed to finish following first: the App adopts an announcement 0.3 s after it
            # arrives, so when the two commands are more than that apart it shows 开 for a moment after `off` has returned
            # (measured on a loaded Mac: the window's switch on for about half a second, the stored switch off throughout).
            self.assertTrue(holds(False, 1.5, app=False), f"on, off back to back: the stored switch stays off ({attempt + 1}): {self.unheld}")
            self.assertTrue(reaches(lambda s: s["enabled"] is False and s["window_switch"] is False and s["status"] == OFF), f"settles off after on, off ({attempt + 1})")
            self.assertTrue(holds(False, 1.0), f"on, off back to back stays off once the window has followed ({attempt + 1}): {self.unheld}")
        self.call("config", "sync", "on", "--yes", env=live)
        self.call("config", "sync", "off", "--yes", env=live)
        self.call("config", "sync", "on", "--yes", env=live)
        self.assertTrue(self.stored_switch(), "on is stored when the third command returns")
        self.assertTrue(reaches(lambda s: s["enabled"] is True and s["window_switch"] is True and s["status"] != OFF), "settles on after on, off, on")
        self.assertTrue(holds(True, 1.5), "on, off, on back to back stays on")
        self.call("config", "sync", "off", "--yes", env=live)
        self.assertTrue(reaches(lambda s: s["enabled"] is False and s["window_switch"] is False and s["status"] == OFF), "back to off")

        cloud = self.cloud / (PRODUCT + ".json")

        def carry(profile, components):
            path = self.root / ("carry-" + uuid.uuid4().hex + ".json")
            path.write_text(json.dumps(self.envelope(profile, components)))
            return path

        def stays(profile, components, seconds=1.5, mirrored=False):
            """From the moment the command returned: the selection file, a fresh process's export and (with sync on) the
            cloud copy keep the imported values for the whole window; returns the first reading that differs, or None."""
            want = {"file.0.profile": profile, "file.0.components": components}
            deadline = time.monotonic() + seconds
            while time.monotonic() < deadline:
                on_disk = json.loads(self.selection.read_text())
                if on_disk != {"profile": profile, "components": components}:
                    return ("file", on_disk)
                fresh = self.exported(env=live)
                if fresh != want:
                    return ("export", fresh)
                if mirrored and json.loads(cloud.read_text())["values"] != want:
                    return ("cloud", json.loads(cloud.read_text())["values"])
                time.sleep(0.05)
            return None

        # An import with sync off: the App re-reads the selection (through its engine, as a refresh does) and leaves the switch alone.
        self.assertTrue(reaches(lambda s: not s["busy"]))
        before = seen()
        self.call("config", "import", str(carry("tianli", ["ghostty", "nvim"])), "--yes", env=live)
        self.assertIsNone(stays("tianli", ["ghostty", "nvim"]))
        self.assertTrue(reaches(lambda s: s["changes"] > before["changes"] and s["profile"] == "tianli" and s["components"] == ["ghostty", "nvim"]),
                        "the app re-reads the imported selection")
        self.assertTrue(holds(False, 0.6), "an import leaves the switch alone")
        # Sync is off: the import did not leave the machine (the cloud copy is still what the rounds above mirrored).
        self.assertEqual(json.loads(cloud.read_text())["values"], {"file.0.profile": SEED["profile"], "file.0.components": SEED["components"]})

        # Sync on and the App running: an import must not be undone by an old value coming back from the App or the cloud copy.
        self.call("config", "sync", "on", "--yes", env=live)
        self.assertTrue(reaches(lambda s: s["enabled"] is True and s["status"] != OFF and not s["busy"]))
        self.assertEqual(json.loads(cloud.read_text())["values"]["file.0.components"], ["ghostty", "nvim"])
        for profile, components in (("developer", ["tmux", "zsh"]), ("tianli", ["atuin"]), ("developer", ["btop", "fd", "glow"])):
            answer = self.call("config", "import", str(carry(profile, components)), "--yes", env=live)
            self.assertTrue(answer["sync"]["completed"], answer)
            self.assertIsNone(stays(profile, components, mirrored=True), f"import of {components} with sync on")
            self.assertTrue(reaches(lambda s: s["profile"] == profile and s["components"] == components), f"the app re-reads {components}")
        # Two imports back to back: the second one stands.
        self.call("config", "import", str(carry("tianli", ["lazygit", "yazi"])), "--yes", env=live)
        self.call("config", "import", str(carry("developer", ["starship"])), "--yes", env=live)
        self.assertIsNone(stays("developer", ["starship"], 2.0, mirrored=True), "the second of two imports stands")
        self.assertTrue(reaches(lambda s: s["profile"] == "developer" and s["components"] == ["starship"] and not s["busy"]), "the app settles on the second import")
        self.assertTrue(holds(True, 0.6), "imports leave the switch on")
        self.assertEqual(stat.S_IMODE(self.selection.stat().st_mode), 0o600)
        # Turning sync off afterwards keeps the imported selection.
        self.call("config", "sync", "off", "--yes", env=live)
        self.assertTrue(reaches(lambda s: s["enabled"] is False and s["window_switch"] is False and s["status"] == OFF))
        self.assertIsNone(stays("developer", ["starship"], 0.6))

        last = seen()
        self.assertEqual((last["policy_prohibited"], last["windows_on_screen"], last["active"], last["error"]), (True, 0, False, ""))
        self.assertGreater(last["tick"], first["tick"])
        process.terminate()
        process.wait(timeout=10)
        self.followers.remove(process)
        after = self.call("config", "status")
        self.assertIs(after["app_running"], others)
        if not others:  # nobody shows a sentence any more: what is reported is what was left behind, and it says so
            self.assertEqual((after["sync_status"]["text"], after["sync_status"]["live"]), (OFF, False), after)
            self.assertIn(after["sync_status"]["from"], ("record", "derived"))


@unittest.skipUnless(NATIVE, "no compiled App binary: set MACKIT_NATIVE, or install Xcode so this test can compile macos/Sources")
class LifecycleCommandTests(Isolated, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory(prefix="mackit-lifecycle-")
        cls.root = Path(cls.folder.name).resolve()
        app = cls.root / "MacKit.app"
        (app / "Contents/MacOS").mkdir(parents=True)
        cls.binary = cls.probe_binary = app / "Contents/MacOS/MacKit"
        shutil.copy2(NATIVE, cls.binary)
        (app / "Contents/Info.plist").write_bytes(plistlib.dumps({
            "CFBundleIdentifier": BUNDLE, "CFBundleExecutable": "MacKit", "CFBundlePackageType": "APPL",
            "CFBundleShortVersionString": "1.2", "CFBundleVersion": "7", "LSUIElement": True}))
        # The running App reads its snapshot through the bundle's engine: the current source, as scripts/accept/native_ui.py does.
        engine = app / "Contents/Resources/core/bin/mackit"
        engine.parent.mkdir(parents=True)
        engine.write_text("#!/bin/sh\nexec " + shlex.quote(sys.executable) + " " + shlex.quote(str(ROOT / "bin/mackit")) + ' "$@"\n')
        engine.chmod(0o755)
        cls.suite = SUITE_PREFIX + uuid.uuid4().hex
        cls.home, cls.support, cls.cloud = cls.root / "home", cls.root / "support", cls.root / "cloud"
        cls.env = dict(os.environ, APP_LIFECYCLE_SUPPORT_DIR=str(cls.support), APP_LIFECYCLE_CLOUD_DIR=str(cls.cloud),
                       MACKIT_LIFECYCLE_SUITE=cls.suite, MACKIT_NATIVE=str(cls.binary), PYTHONDONTWRITEBYTECODE="1")
        cls.env.pop("APP_LIFECYCLE_FOLLOW_CHANNEL", None)
        cls.followers = []
        cls.real_selection = Path.home() / ".config/mackit/portable-preferences.json"
        cls.real_before = cls.real_selection.read_bytes() if cls.real_selection.exists() else None

    @classmethod
    def tearDownClass(cls):
        for process in cls.followers:
            process.kill()
            process.wait(timeout=10)
        forget(cls.suite)
        cls.folder.cleanup()
        now = cls.real_selection.read_bytes() if cls.real_selection.exists() else None
        assert now == cls.real_before, "a lifecycle test touched the owner's remembered selection"

    def setUp(self):
        """Every test starts from the same settings: sync off, the seeded selection, no support or cloud folder."""
        subprocess.run(["/usr/bin/defaults", "delete", self.suite], capture_output=True, timeout=30)
        for folder in (self.home, self.support, self.cloud):
            shutil.rmtree(folder, ignore_errors=True)
        self.selection = write_selection(self.home, SEED)

    # The command as an agent types it: the engine from source, which forwards to the binary named by MACKIT_NATIVE.
    def mackit(self, *words, env=None, home=None, cwd=None):
        return subprocess.run([sys.executable, str(ROOT / "bin/mackit"), "--home", str(home or self.home), *words], env=env or self.env,
                              cwd=cwd, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=90)

    def direct(self, *words, env=None, home=None):
        return subprocess.run([str(self.binary), "--home", str(home or self.home), *words], env=env or self.env, capture_output=True, text=True,
                              stdin=subprocess.DEVNULL, timeout=90)

    def test_help_lines_are_the_shared_layers_own_and_reach_the_top_level_help(self):
        shared = self.direct("config", "--help")
        self.assertEqual(shared.returncode, 0)
        top = self.mackit("--help").stdout
        for line in cli.LIFECYCLE_READS + cli.LIFECYCLE_WRITES:
            self.assertIn(line + "\n", shared.stdout)  # the engine's copy of the line is the shared layer's line
            self.assertIn("\n" + line + "\n", top)     # and it is listed at the start of a line in `mackit --help`
        # Every line the shared layer lists under 读 / 写 is in the engine's copy: none was added there and missed here.
        listed = shared.stdout.split("读（不写任何文件或状态）:\n")[1].split("--json：")[0].replace("写:\n", "")
        self.assertEqual(listed.splitlines(), list(cli.LIFECYCLE_READS + cli.LIFECYCLE_WRITES))
        self.assertTrue(any(line.startswith("  update install ") for line in cli.LIFECYCLE_WRITES))
        self.assertIn("同步状态", cli.LIFECYCLE_READS[0])
        # Upgrading and the sync sentence have commands now: nothing is listed as having none, in either help.
        for stale in ("暂无命令", "No command yet", "不做静默安装", "held by the running App"):
            self.assertNotIn(stale, shared.stdout)
            self.assertNotIn(stale, top)
        self.assertFalse(hasattr(cli, "LIFECYCLE_NO_COMMAND"))
        window_only = top.split("仅在窗口中 Window only")[1].split("Without --home")[0]
        self.assertNotIn("升级到新版", window_only)
        self.assertIn("配置与更新…", window_only)  # opening the window itself stays a window-only item
        for word in ("config", "update"):  # both verbs are listed as commands by argparse too
            self.assertIn("\n    " + word + " ", top)
        for code in ("confirmation_required", "file_exists", "isolated_home", "app_missing", "manual_install", "needs_product_installer",
                     "upgrade_failed", "app_busy", "replace_failed", "cleanup_failed"):
            self.assertIn(code, top)
            if code not in ("isolated_home", "app_missing"):  # those two are MacKit's own, the rest are the shared layer's
                self.assertIn(code, shared.stdout)
        for field in ("sync_status", "old_app_cleanup", "would_install"):
            self.assertIn(field, top)
            self.assertIn(field, shared.stdout)
        forwarded = self.mackit("config", "--help")
        self.assertEqual((forwarded.returncode, forwarded.stdout), (0, shared.stdout))
        self.assertIn("退出码", shared.stdout)
        self.assertIn("usage: mackit config", shared.stdout)  # the product's command name, not the binary's

    def test_words_output_and_exit_code_pass_through_unchanged(self):
        cases = ((("config", "status", "--json"), 0), (("config", "status"), 0), (("config", "--json"), 0),
                 (("config", "bogus", "--json"), 2), (("config", "status", "--no-such", "--json"), 2), (("config", "bogus"), 2),
                 (("update", "bogus", "--json"), 2), (("config", "export", "--json"), 2), (("config", "sync", "maybe", "--json"), 2),
                 (("config", "sync", "on", "--json"), 2), (("config", "import", str(self.root / "absent.json"), "--yes", "--json"), 1),
                 (("update", "check", "--json"), 1), (("update", "check"), 1), (("update", "check", "--no-such", "--json"), 2),
                 (("update", "install", "--json"), 1), (("update", "install", "--yes", "--json"), 1), (("update", "install", "--dry-run"), 1),
                 (("update", "install", "--no-such", "--json"), 2), (("update", "install", "extra", "--yes", "--json"), 2))
        for words, code in cases:
            ours, theirs = self.mackit(*words), self.direct(*words)
            self.assertEqual((ours.returncode, ours.stdout, ours.stderr), (theirs.returncode, theirs.stdout, theirs.stderr), words)
            self.assertEqual(ours.returncode, code, (words, ours.stdout, ours.stderr))
            if "--json" in words:
                body = json.loads(ours.stdout)
                self.assertIs(body["ok"], code == 0)
                self.assertEqual(body["command"].split()[0], words[0])
                if code:
                    self.assertTrue(body["error"]["code"] and body["error"]["message"])
            elif code:
                self.assertEqual(ours.stdout, "")  # text-mode errors go to stderr
                self.assertTrue(ours.stderr.strip())
        self.assertEqual(self.call("config", "bogus", expect=2)["error"]["code"], "usage")
        self.assertEqual(self.call("config", "status", "--no-such", expect=2)["error"]["code"], "usage")
        self.assertEqual(self.call("config", "sync", "on", expect=2)["error"]["code"], "confirmation_required")
        self.assertEqual(self.call("update", "check", expect=1)["error"]["code"], "check_incomplete")
        # No release record: update install stops at the lookup, with or without --yes, and names the channel it read.
        unread = self.call("update", "install", "--yes", expect=1)
        self.assertEqual((unread["error"]["code"], unread["command"], unread["source"]),
                         ("check_incomplete", "update install", {"kind": "private_cloud", "channel": "isolated"}))
        self.assertEqual(self.call("update", "install", "--no-such", expect=2)["error"]["code"], "usage")
        # --home=<dir> is the same as --home <dir>.
        joined = subprocess.run([sys.executable, str(ROOT / "bin/mackit"), "--home=" + str(self.home), "config", "status", "--json"],
                                env=self.env, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=90)
        self.assertEqual((joined.returncode, json.loads(joined.stdout)["keys"]), (0, ["file.0.components", "file.0.profile"]))
        # A relative path is resolved where the command was typed, not where the App binary lives.
        done = self.mackit("config", "export", "-o", "here.json", "--json", cwd=self.root)
        self.assertEqual((done.returncode, json.loads(done.stdout)["path"]), (0, str(self.root / "here.json")))

    def test_plain_update_keeps_its_own_meaning(self):
        """`mackit update` was a command before the window's items were: only `update <word>` goes to the App."""
        self.assertIsNone(cli.lifecycle_words(["update"]))
        self.assertIsNone(cli.lifecycle_words(["--home", "/x", "update", "--json"]))
        self.assertIsNone(cli.lifecycle_words(["status", "--json"]))
        self.assertIsNone(cli.lifecycle_words(["--version", "config"]))
        self.assertEqual(cli.lifecycle_words(["--home", "/x", "update", "check", "--json"]), ["--home", "/x", "update", "check", "--json"])
        self.assertEqual(cli.lifecycle_words(["--home", "/x", "update", "install", "--yes"]), ["--home", "/x", "update", "install", "--yes"])
        # Only update install waits long: longer than every step the shared layer bounds by itself, put together
        # (Product.timeout 30, upgradeTimeout 330 twice, quitTimeout 20), so the App's own answer always arrives first.
        shared = (ROOT / "macos/Sources/AppLifecycleCLI.swift").read_text()
        for bound in ("var timeout: TimeInterval = 30", "var upgradeTimeout: TimeInterval = 330", "var quitTimeout: TimeInterval = 20"):
            self.assertIn(bound, shared)
        self.assertGreater(cli.LIFECYCLE_INSTALL_SECONDS, 30 + 330 + 20 + 330)
        self.assertEqual(cli.lifecycle_seconds(["--home", "/x", "update", "install", "--yes", "--json"]), cli.LIFECYCLE_INSTALL_SECONDS)
        self.assertEqual(cli.lifecycle_seconds(["--home", "/x", "update", "--json", "install"]), cli.LIFECYCLE_INSTALL_SECONDS)
        for quick in (["update", "check"], ["config", "sync", "on", "--yes"], ["config", "import", "install", "--yes"], ["config"]):
            self.assertEqual(cli.lifecycle_seconds(["--home", "/x", *quick]), cli.LIFECYCLE_SECONDS, quick)
        self.assertEqual(cli.lifecycle_words(["config"]), ["--home", str(Path.home().absolute()), "config"])
        pull = self.mackit("update")
        self.assertEqual((pull.returncode, pull.stdout), (1, ""))
        self.assertIn("update pulls the source checkout", pull.stderr)  # the original command answered, in its sandbox refusal
        flagged = self.mackit("update", "--json")
        self.assertEqual(flagged.returncode, 2)
        self.assertEqual(json.loads(flagged.stdout), {"ok": False, "error": "usage: unrecognized arguments: --json"})
        described = self.mackit("update", "--help")
        self.assertEqual(described.returncode, 0)
        self.assertIn("usage: mackit update [-h]", described.stdout)
        self.assertIn("update check", described.stdout)
        self.assertIn("update install --yes", " ".join(described.stdout.split()))  # argparse wraps the paragraph

    def test_the_command_reads_and_writes_the_windows_own_settings(self):
        status = self.call("config", "status")
        self.assertEqual((status["command"], status["has_settings"], status["sync_enabled"], status["problem"]), ("config status", True, False, None))
        self.assertEqual(status["keys"], ["file.0.components", "file.0.profile"])
        self.assertFalse(self.support.exists() or self.cloud.exists())  # reading writes nothing
        self.assertEqual(json.loads(self.selection.read_text()), SEED)
        exported = self.root / "out.json"
        exported.unlink(missing_ok=True)
        first = self.call("config", "export", "-o", str(exported))
        envelope = json.loads(exported.read_text())
        self.assertEqual((envelope["product"], first["bytes"]), (PRODUCT, exported.stat().st_size))
        self.assertEqual(envelope["values"], {"file.0.profile": "developer", "file.0.components": ["nvim", "zsh"]})
        self.assertEqual(self.call("config", "export", "-o", str(exported), expect=2)["error"]["code"], "file_exists")
        self.assertEqual(self.exported(), envelope["values"])
        self.assertFalse(self.support.exists() or self.cloud.exists())  # exporting writes only the named file

        # What the 安装配置 page stores (mackit select is that same save) is what the command exports.
        chosen = self.call("select", "--profile", "tianli", "--components", "nvim,zsh,yabai")
        self.assertEqual(chosen["components"], ["nvim", "yabai", "zsh"])
        self.assertEqual(self.exported(), {"file.0.profile": "tianli", "file.0.components": ["nvim", "yabai", "zsh"]})

        incoming = self.root / "in.json"
        incoming.write_text(json.dumps(self.envelope("developer", ["ghostty", "tmux"])))
        before = json.loads(self.selection.read_text())
        self.assertEqual(self.call("config", "import", str(incoming), expect=2)["error"]["code"], "confirmation_required")
        foreign = self.root / "foreign.json"
        foreign.write_text(json.dumps(dict(self.envelope("developer", ["ghostty"]), product="someone.else")))
        self.assertEqual(self.call("config", "import", str(foreign), "--yes", expect=1)["error"]["code"], "import_rejected")
        other = self.root / "other-key.json"
        other.write_text(json.dumps({"version": 1, "product": PRODUCT, "values": {"file.0.source_root": "/elsewhere"}}))
        self.assertEqual(self.call("config", "import", str(other), "--yes", expect=1)["error"]["code"], "import_rejected")
        self.assertEqual(json.loads(self.selection.read_text()), before)  # refused imports leave the selection alone
        self.assertFalse((self.support / PRODUCT / "Backups").exists())

        imported = self.call("config", "import", str(incoming), "--yes")
        self.assertTrue(imported["imported"] and "sync" not in imported)
        self.assertEqual(json.loads(self.selection.read_text()), {"profile": "developer", "components": ["ghostty", "tmux"]})
        self.assertEqual(stat.S_IMODE(self.selection.stat().st_mode), 0o600)  # owner-only, as the engine keeps it
        self.assertEqual(len(list((self.support / PRODUCT / "Backups").iterdir())), 1)
        self.assertFalse(self.cloud.exists())  # sync is off: nothing leaves the machine
        # The engine (what the App's pages read) sees the imported selection.
        shown = json.loads(self.mackit("status", "--json").stdout)["app"]
        self.assertEqual((shown["profile"], shown["selected"]), ("developer", ["ghostty", "tmux"]))

        dry = self.call("config", "sync", "on", "--dry-run")
        self.assertTrue(dry["dry_run"] and dry["would_change"] and not self.call("config", "status")["sync_enabled"])
        self.assertFalse(self.stored_switch() or self.cloud.exists())
        on = self.call("config", "sync", "on", "--yes")
        mirrored = json.loads((self.cloud / (PRODUCT + ".json")).read_text())
        self.assertEqual((on["changed"], on["sync_enabled"], on["check_with"], mirrored["values"]["file.0.components"]),
                         (True, True, "mackit config status", ["ghostty", "tmux"]))
        self.assertTrue(self.call("config", "status")["sync_enabled"] and self.stored_switch())
        self.assertIs(self.call("config", "sync", "on", "--yes")["changed"], False)
        self.assertIs(self.call("config", "sync", "off", "--yes")["sync_enabled"], False)
        self.assertFalse(self.stored_switch())

    def test_update_check_reads_only_the_isolated_release_record(self):
        missing = self.call("update", "check", expect=1)
        self.assertEqual((missing["error"]["code"], missing["current"], missing["source"]),
                         ("check_incomplete", {"version": "1.2", "build": "7"}, {"kind": "private_cloud", "channel": "isolated"}))
        feed = self.cloud / "TianliApps/Updates" / BUNDLE / "isolated"
        feed.mkdir(parents=True)

        def publish(version, build):
            (feed / "release.json").write_text(json.dumps({"version": version, "build": build, "bundle_id": BUNDLE, "channel": "isolated",
                                                           "filename": f"MacKit-{version}.zip", "sha256": "a" * 64, "size_bytes": 10}))
            return self.call("update", "check")

        newer = publish("2.0", "9")
        self.assertEqual((newer["state"], newer["update_available"], newer["latest"]["version"]), ("update_available", True, "2.0"))
        self.assertIn("配置与更新…", newer["upgrade"]["how"])
        self.assertIn("MacKit · 配置助手", newer["upgrade"]["how"])
        # The window's button here is 升级到新版…, and the answer names the command that does the same.
        self.assertEqual((newer["upgrade"]["in_app"], newer["upgrade"]["button"], newer["upgrade"]["command"]), (True, "升级到新版…", "mackit update install --yes"))
        self.assertIn("mackit update install --yes", newer["upgrade"]["how"])
        self.assertIn("有新版 2.0 (9)", self.mackit("update", "check").stdout)
        same = publish("1.2", "7")
        self.assertEqual((same["state"], same["update_available"], same["upgrade"]["button"], same["upgrade"]["command"]), ("up_to_date", False, None, None))
        self.assertEqual(publish("1.0", "1")["state"], "ahead_of_channel")
        self.assertEqual(sorted(path.name for path in feed.iterdir()), ["release.json"])  # nothing downloaded, nothing installed
        self.assertEqual(json.loads(self.selection.read_text()), SEED)
        # Outside an isolated run the channel is the public one the window's 检查更新 reads; this test never goes there.
        self.assertIn('.github(repository: "zengtianli/mackit")', (ROOT / "macos/Sources/Lifecycle.swift").read_text())

    def test_config_status_reports_the_sentence_under_the_switch(self):
        """`sync_status` is the line under 使用 iCloud 记住配置. With no App running it is what the last pass left, or the
        value a window opens with; reading it writes nothing and the fields that were there before are unchanged."""
        fresh = self.call("config", "status")
        self.assertEqual(set(fresh), {"ok", "command", "has_settings", "sync_enabled", "sync_status", "keys", "app_running", "problem"})
        self.assertEqual((fresh["has_settings"], fresh["sync_enabled"], fresh["keys"], fresh["app_running"], fresh["problem"]),
                         (True, False, ["file.0.components", "file.0.profile"], False, None))
        self.assertEqual(fresh["sync_status"], {"text": OFF, "at": None, "from": "derived", "live": False})
        self.assertFalse(self.support.exists() or self.cloud.exists())  # reading the sentence writes nothing
        text = self.mackit("config", "status")
        self.assertEqual(text.returncode, 0)
        self.assertIn("\n同步状态：" + OFF, text.stdout)

        on = self.call("config", "sync", "on", "--yes")
        left = self.call("config", "status")["sync_status"]
        # No App is running: the sentence is the one that pass left behind, with its time, and it is not live.
        self.assertEqual((left["text"], left["from"], left["live"]), (on["status"], "record", False), left)
        self.assertNotEqual(left["text"], OFF)
        self.assertRegex(left["at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")

        def files():
            return sorted((path.relative_to(self.root).as_posix(), path.stat().st_mtime_ns)
                          for folder in (self.support, self.cloud) for path in folder.rglob("*"))

        before = files()
        self.assertEqual(self.call("config", "status")["sync_status"], left)
        self.assertEqual(files(), before)  # reading again changed no file under the support or the cloud folder
        self.assertIn("\n同步状态：" + left["text"], self.mackit("config", "status").stdout)

        self.call("config", "sync", "off", "--yes")
        closed = self.call("config", "status")["sync_status"]
        self.assertEqual((closed["text"], closed["live"]), (OFF, False), closed)
        self.assertIn(closed["from"], ("record", "derived"))
        # A record that no longer fits the switch is not reported: the switch is flipped under it by hand here.
        subprocess.run(["/usr/bin/defaults", "write", self.suite, SWITCH, "-bool", "true"], check=True, capture_output=True, timeout=30)
        stale = self.call("config", "status")
        self.assertIs(stale["sync_enabled"], True)
        self.assertEqual((stale["sync_status"]["from"], stale["sync_status"]["live"]), ("derived", False), stale)
        self.assertNotEqual(stale["sync_status"]["text"], OFF)

    def throwaway(self, app, version, build):
        """A signed stand-in for an installed MacKit.app: the compiled binary, the test bundle identifier, and the engine
        from source where the bundle keeps its own."""
        (app / "Contents/MacOS").mkdir(parents=True)
        shutil.copy2(NATIVE, app / "Contents/MacOS/MacKit")
        (app / "Contents/Info.plist").write_bytes(plistlib.dumps({
            "CFBundleIdentifier": BUNDLE, "CFBundleExecutable": "MacKit", "CFBundlePackageType": "APPL",
            "CFBundleShortVersionString": version, "CFBundleVersion": build, "LSUIElement": True}))
        engine = app / "Contents/Resources/core/bin/mackit"
        engine.parent.mkdir(parents=True)
        engine.write_text("#!/bin/sh\nexec " + shlex.quote(sys.executable) + " " + shlex.quote(str(ROOT / "bin/mackit")) + ' "$@"\n')
        engine.chmod(0o755)
        sign(app)
        return app

    def test_update_install_previews_asks_and_then_replaces_a_throwaway_bundle(self):
        """The window's 升级到新版… as a command, for real, on a bundle that is nobody's: it lives under the isolated
        support folder, so the installer keeps its rollback copy and its "Trash" there too and reopens nothing.
        The command runs from inside the bundle it replaces, as the installed one does."""
        installed = self.throwaway(self.support / "installed/MacKit.app", "1.2", "7")
        binary = installed / "Contents/MacOS/MacKit"
        env = dict(self.env, MACKIT_NATIVE=str(binary), APP_LIFECYCLE_NO_RELAUNCH="1")
        feed = self.cloud / "TianliApps/Updates" / BUNDLE / "isolated"
        publish(feed, self.throwaway(self.root / ("next-" + uuid.uuid4().hex) / "MacKit.app", "1.3", "8"), BUNDLE)
        old, new = {"version": "1.2", "build": "7"}, {"version": "1.3", "build": "8"}
        backups, trash = self.support / "backups", self.support / "trash"

        def untouched():
            return facts(installed) == old and not backups.exists() and not trash.exists() and not list(installed.parent.glob("*.upgrade-*"))

        asked = self.call("update", "install", expect=2, env=env)
        self.assertEqual((asked["error"]["code"], asked["command"]), ("confirmation_required", "update install"))
        self.assertTrue(untouched())
        dry = self.call("update", "install", "--dry-run", env=env)
        self.assertEqual((dry["dry_run"], dry["installed"], dry["would_install"], dry["installation"], dry["will_quit_app"], dry["will_relaunch"]),
                         (True, False, {"from": old, "to": new}, "bundle", False, False))
        self.assertEqual((dry["current"], dry["latest"]["version"], dry["latest"]["build"], dry["source"], dry["app_running"]),
                         (old, "1.3", "8", {"kind": "private_cloud", "channel": "isolated"}, False))
        self.assertEqual(self.call("update", "install", "--dry-run", "--yes", env=env)["installed"], False)  # --dry-run wins over --yes
        self.assertTrue(untouched())
        self.assertIn("未执行", self.mackit("update", "install", "--dry-run", env=env).stdout)

        # Where the window's button would be 下载新版…: a folder the App cannot be replaced in.
        installed.parent.chmod(0o555)
        try:
            manual = self.call("update", "install", "--yes", expect=1, env=env)
        finally:
            installed.parent.chmod(0o755)
        self.assertEqual(manual["error"]["code"], "manual_install")
        self.assertTrue(untouched())

        done = self.call("update", "install", "--yes", env=env)
        self.assertEqual((done["installed"], done["state"], done["previous"], done["current"], done["backup"], done["old_app_cleanup"], done["relaunched"]),
                         (True, "installed", old, new, None, "trashed", False), done)
        self.assertEqual(facts(installed), new)                      # the new version is where the old one was
        retired = list(trash.glob("*/MacKit.app"))
        self.assertEqual([facts(app) for app in retired], [old])     # and the old one is in the (isolated) Trash, whole
        self.assertTrue((retired[0] / "Contents/MacOS/MacKit").is_file())
        self.assertFalse((backups / "MacKit.app").exists())          # no second copy is left where the rollback copy was kept
        self.assertFalse(list(installed.parent.glob("*.upgrade-*")))
        subprocess.run(["/usr/bin/codesign", "--verify", "--deep", "--strict", str(installed)], check=True, capture_output=True, timeout=120)
        # Read back, and asking again finds nothing to do.
        self.assertEqual((self.call("update", "check", env=env)["state"], self.call("update", "check", env=env)["current"]), ("up_to_date", new))
        again = self.call("update", "install", "--yes", env=env)
        self.assertEqual((again["installed"], again["state"], again["current"]), (False, "up_to_date", new))
        self.assertEqual(len(list(trash.glob("*/MacKit.app"))), 1)
        self.assertEqual(json.loads(self.selection.read_text()), SEED)  # the configuration is kept

    def test_a_running_app_follows_the_command_and_never_writes_the_old_value_back(self):
        self.follow_scenario()

    def test_refusals(self):
        # An isolated run that does not say where the switch is kept is refused before anything is read.
        partial = {key: value for key, value in self.env.items() if key != "MACKIT_LIFECYCLE_SUITE"}
        self.assertEqual(self.call("config", "status", expect=1, env=partial)["error"]["code"], "isolation_incomplete")
        for suite in (PRODUCT, "com.example.other", SUITE_PREFIX):
            self.assertEqual(self.call("config", "status", expect=1, env=dict(self.env, MACKIT_LIFECYCLE_SUITE=suite))["error"]["code"], "isolation_incomplete")
        # ... or one that names the owner's own home.
        self.assertEqual(self.call("config", "status", expect=1, home=Path.home())["error"]["code"], "isolation_incomplete")
        # A sandbox --home without the isolation variables has no such settings: refused, nothing read or written.
        bare = {key: value for key, value in self.env.items() if not key.startswith(("APP_LIFECYCLE_", "MACKIT_LIFECYCLE_"))}
        for words in (("config", "status"), ("config", "sync", "on", "--yes"), ("config", "import", str(self.root / "absent.json"), "--yes")):
            refused = self.call(*words, expect=1, env=bare)
            self.assertEqual((refused["error"]["code"], refused["command"]), ("isolated_home", " ".join(words[:2])))
        text = self.mackit("config", "sync", "on", "--yes", env=bare)
        self.assertEqual((text.returncode, text.stdout), (1, ""))
        self.assertIn("--home", text.stderr)
        # update install replaces the installed App and quits a running one: a sandbox --home never does either, not even
        # as a preview. Refused before the release channel is read (outside an isolated run that would be the network).
        for words in (("update", "install", "--yes"), ("update", "install", "--dry-run"), ("update", "install"), ("update", "--yes", "install")):
            refused = self.call(*words, expect=1, env=bare)
            self.assertEqual((refused["error"]["code"], refused["command"]), ("isolated_home", "update install"))
            self.assertIn("MacKit.app", refused["error"]["message"])
        self.assertEqual(self.call("update", "install", "--yes", expect=1, env=partial)["error"]["code"], "isolation_incomplete")
        self.assertEqual(self.mackit("update", "install", "--help", env=bare).returncode, 0)
        self.assertEqual(self.mackit("config", "--help", env=bare).returncode, 0)  # the help needs no settings
        self.assertEqual(json.loads(self.selection.read_text()), SEED)
        self.assertFalse(self.support.exists() or self.cloud.exists() or self.stored_switch())
        # The probe mode exists for this test only: outside an isolated run the binary exits at once, before any NSApplication.
        probe = subprocess.run([str(self.binary), "--lifecycle-follow-probe", str(self.root / "never.json"), "--home", str(self.home)], env=bare,
                               capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=30)
        self.assertEqual((probe.returncode, (self.root / "never.json").exists()), (64, False))
        # From source with no App binary to forward to, the command says so in the same shape.
        alone = {key: value for key, value in self.env.items() if key != "MACKIT_NATIVE"}
        self.assertEqual(self.call("config", "status", expect=1, env=alone)["error"]["code"], "app_missing")
        text = self.mackit("update", "check", env=alone)
        self.assertEqual((text.returncode, text.stdout), (1, ""))
        self.assertIn("MacKit App", text.stderr)

    @unittest.skipUnless(HEADQUARTERS.is_file(), "shared source not on this machine")
    def test_the_command_layer_is_the_shared_source_byte_for_byte(self):
        self.assertTrue((ROOT / "macos/Sources/AppLifecycleCLI.swift").read_bytes() == HEADQUARTERS.read_bytes(),
                        f"macos/Sources/AppLifecycleCLI.swift differs from the shared source; copy {HEADQUARTERS} over it and build again")


ASSEMBLED = os.environ.get("MACKIT_APP")


@unittest.skipUnless(ASSEMBLED, "set MACKIT_APP to an assembled or installed MacKit.app")
class AssembledBundleTests(Isolated, unittest.TestCase):
    """The shipped chain: the App's own command inside the bundle forwards to the bundle's own App executable, and that
    executable, started in place as the App (activation policy prohibited, nothing on screen), follows it. A signed
    binary cannot be moved into another bundle (the system ends it with signal 9), so this is how the signed bytes run
    the follow scenario. Everything is on a throwaway preference domain, home, support and cloud folder and a private
    notification channel; the bundle's real settings are not opened and no other running App is signalled."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix="mackit-lifecycle-app-")
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name).resolve()
        self.app = Path(ASSEMBLED)
        self.info = plistlib.loads((self.app / "Contents/Info.plist").read_bytes())
        self.probe_binary = self.app / "Contents/MacOS" / self.info["CFBundleExecutable"]
        self.suite = SUITE_PREFIX + uuid.uuid4().hex
        self.home, self.cloud = self.root / "home", self.root / "cloud"
        self.selection = write_selection(self.home, SEED)
        self.env = dict(os.environ, APP_LIFECYCLE_SUPPORT_DIR=str(self.root / "support"), APP_LIFECYCLE_CLOUD_DIR=str(self.cloud),
                        MACKIT_LIFECYCLE_SUITE=self.suite, MACKIT_NATIVE=str(self.root / "ignored-by-the-apps-own-command"))
        self.env.pop("APP_LIFECYCLE_FOLLOW_CHANNEL", None)  # isolated and no channel: no running App is signalled
        self.addCleanup(forget, self.suite)
        self.followers = []
        self.addCleanup(self.stop_followers)
        real = Path.home() / ".config/mackit/portable-preferences.json"
        before = real.read_bytes() if real.exists() else None
        self.addCleanup(lambda: self.assertEqual(real.read_bytes() if real.exists() else None, before, "the owner's remembered selection changed"))

    def stop_followers(self):
        for process in self.followers:
            process.kill()
            process.wait(timeout=10)

    # The command as installed: the App's own engine, which forwards to its own bundle's executable.
    def mackit(self, *words, env=None, home=None, cwd=None):
        return subprocess.run([str(self.app / "Contents/Resources/core/bin/mackit"), "--home", str(home or self.home), *words], env=env or self.env,
                              cwd=cwd, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=90)

    engine = mackit

    def test_the_bundles_own_executable_follows_its_own_command(self):
        self.follow_scenario()

    def test_the_apps_own_command_forwards_to_its_own_bundle(self):
        info = self.info
        status = self.engine("config", "status", "--json")
        body = json.loads(status.stdout)
        self.assertEqual((status.returncode, body["ok"], body["command"], body["sync_enabled"]), (0, True, "config status", False))
        self.assertEqual(body["keys"], ["file.0.components", "file.0.profile"])
        direct = subprocess.run([str(self.app / "Contents/MacOS" / info["CFBundleExecutable"]), "--home", str(self.home), "config", "status", "--json"],
                                env=self.env, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=90)
        self.assertEqual((status.returncode, status.stdout, status.stderr), (direct.returncode, direct.stdout, direct.stderr))
        wrong = self.engine("config", "status", "--no-such", "--json")
        self.assertEqual((wrong.returncode, json.loads(wrong.stdout)["error"]["code"]), (2, "usage"))
        exported = json.loads(self.engine("config", "export", "-o", "-").stdout)
        self.assertEqual(exported["values"], {"file.0.profile": "developer", "file.0.components": ["nvim", "zsh"]})
        dry = json.loads(self.engine("config", "sync", "on", "--dry-run", "--json").stdout)
        self.assertEqual((dry["would_change"], dry["sync_enabled"]), (True, False))
        self.assertFalse((self.root / "support").exists() or (self.root / "cloud").exists())  # read commands wrote nothing
        # The version, build and bundle identifier the window shows come from the bundle the command lives in.
        feed = self.root / "cloud/TianliApps/Updates" / info["CFBundleIdentifier"] / "isolated"
        feed.mkdir(parents=True)
        (feed / "release.json").write_text(json.dumps({"version": info["CFBundleShortVersionString"], "build": info["CFBundleVersion"],
                                                       "bundle_id": info["CFBundleIdentifier"], "channel": "isolated",
                                                       "filename": "MacKit.zip", "sha256": "a" * 64, "size_bytes": 10}))
        check = self.engine("update", "check", "--json")
        body = json.loads(check.stdout)
        self.assertEqual((check.returncode, body["state"], body["current"]),
                         (0, "up_to_date", {"version": info["CFBundleShortVersionString"], "build": info["CFBundleVersion"]}))
        top = self.engine("--help").stdout
        for line in cli.LIFECYCLE_READS + cli.LIFECYCLE_WRITES:
            self.assertIn("\n" + line + "\n", top)
        self.assertNotIn("暂无命令", top)
        self.assertEqual(json.loads((self.home / ".config/mackit/portable-preferences.json").read_text()), SEED)
        # The sentence under the switch, and the upgrade's own argument check: both answered by the bundle's executable.
        self.assertEqual(body_of(self.engine("config", "status", "--json"))["sync_status"], {"text": OFF, "at": None, "from": "derived", "live": False})
        wrong = self.engine("update", "install", "--no-such", "--json")
        self.assertEqual((wrong.returncode, json.loads(wrong.stdout)["error"]["code"]), (2, "usage"))
        # The record above is this very version: there is nothing to install, with or without --yes, and nothing is touched.
        for words in (("update", "install", "--dry-run", "--json"), ("update", "install", "--json")):
            nothing = self.engine(*words)
            self.assertEqual((nothing.returncode, body_of(nothing)["installed"], body_of(nothing)["state"]), (0, False, "up_to_date"), words)

    def test_update_install_replaces_a_copy_of_this_bundle_and_its_own_command_brings_the_answer_back(self):
        """`mackit update install --yes` replaces the whole .app, and `mackit` is the frozen engine inside that .app: by
        the time the App executable answers, the files the engine was started from are in the Trash and the same paths
        hold the next version. The engine still has to hand back stdout, stderr and the exit code.

        Run on a copy of the bundle under test, never on the bundle itself: the copy gets the test bundle identifier (so
        no running MacKit is found, let alone asked to quit) and an ad-hoc signature, and lives under the isolated
        support folder, where the installer also keeps its rollback copy and its "Trash" and reopens nothing."""
        source_before = hashlib.sha256((self.app / "Contents/MacOS" / self.info["CFBundleExecutable"]).read_bytes()).hexdigest(), \
            (self.app / "Contents/Info.plist").read_bytes()
        support = self.root / "support"

        def copy(to, build):
            to.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["/usr/bin/ditto", str(self.app), str(to)], check=True, capture_output=True, timeout=300)
            info = dict(self.info, CFBundleIdentifier=BUNDLE, CFBundleVersion=build)
            (to / "Contents/Info.plist").write_bytes(plistlib.dumps(info))
            sign(to)
            return to

        version = self.info["CFBundleShortVersionString"]
        old, new = {"version": version, "build": "1"}, {"version": version, "build": "2"}
        installed = copy(support / "installed/MacKit.app", "1")
        publish(self.root / "cloud/TianliApps/Updates" / BUNDLE / "isolated", copy(self.root / "next/MacKit.app", "2"), BUNDLE)
        env = dict(self.env, APP_LIFECYCLE_NO_RELAUNCH="1")
        command = installed / "Contents/Resources/core/bin/mackit"

        def run(*words, seconds=120):
            return subprocess.run([str(command), "--home", str(self.home), *words], env=env, capture_output=True, text=True,
                                  stdin=subprocess.DEVNULL, timeout=seconds)

        dry = run("update", "install", "--dry-run", "--json")
        self.assertEqual((dry.returncode, body_of(dry)["would_install"], body_of(dry)["will_quit_app"]), (0, {"from": old, "to": new}, False), dry.stdout + dry.stderr)
        asked = run("update", "install", "--json")
        self.assertEqual((asked.returncode, body_of(asked)["error"]["code"], facts(installed)), (2, "confirmation_required", old))
        engine_before = hashlib.sha256(command.read_bytes()).hexdigest()

        done = run("update", "install", "--yes", "--json", seconds=cli.LIFECYCLE_INSTALL_SECONDS + 60)
        self.assertEqual((done.returncode, done.stderr), (0, ""), done.stdout + done.stderr)
        body = body_of(done)  # one whole JSON object came back through the engine that was replaced under its own feet
        self.assertEqual((body["ok"], body["command"], body["installed"], body["state"], body["previous"], body["current"],
                          body["backup"], body["old_app_cleanup"], body["relaunched"]),
                         (True, "update install", True, "installed", old, new, None, "trashed", False), body)
        self.assertEqual(facts(installed), new)
        retired = list((support / "trash").glob("*/MacKit.app"))
        self.assertEqual([facts(app) for app in retired], [old])
        # The engine that answered is the one now in the Trash; the path it was started from holds the next version's.
        self.assertEqual(hashlib.sha256((retired[0] / "Contents/Resources/core/bin/mackit").read_bytes()).hexdigest(), engine_before)
        self.assertFalse((support / "backups/MacKit.app").exists())
        self.assertFalse(list(installed.parent.glob("*.upgrade-*")))
        subprocess.run(["/usr/bin/codesign", "--verify", "--deep", "--strict", str(installed)], check=True, capture_output=True, timeout=120)
        # The next version's own command reads the result back and finds nothing more to do; the text form works too.
        check = run("update", "check", "--json")
        self.assertEqual((check.returncode, body_of(check)["state"], body_of(check)["current"]), (0, "up_to_date", new))
        again = run("update", "install", "--yes")
        self.assertEqual((again.returncode, again.stderr), (0, ""))
        self.assertIn("不需要升级", again.stdout)
        self.assertEqual(len(list((support / "trash").glob("*/MacKit.app"))), 1)
        self.assertEqual(json.loads((self.home / ".config/mackit/portable-preferences.json").read_text()), SEED)
        # The bundle that was named for this test is as it was.
        self.assertEqual((hashlib.sha256((self.app / "Contents/MacOS" / self.info["CFBundleExecutable"]).read_bytes()).hexdigest(),
                          (self.app / "Contents/Info.plist").read_bytes()), source_before)


if __name__ == "__main__":
    unittest.main()
