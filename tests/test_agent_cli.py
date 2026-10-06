"""Agent-facing CLI: the App's pages as commands, run against disposable homes only.

Every write here goes to a temporary HOME whose source was prepared the way the App prepares it
(~/.local/share/mackit), never to the repository or this Mac's running services.
"""
import hashlib, json, os, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mackit import localkeys, window  # noqa: E402

REPO_WINDOW = [ROOT / "components/yabai/config" / name for name in ("settings.json", "yabairc", "skhd/hotkeys.json", "skhd/skhdrc")] \
    + [ROOT / "components/nvim/lua/config/keymaps.lua", ROOT / "data/keys.json"]


def digest(paths):
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


class AgentCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mackit-agent-")
        self.home = Path(self.temp.name)
        self.repo_before = digest(REPO_WINDOW)

    def tearDown(self):
        self.temp.cleanup()
        self.assertEqual(digest(REPO_WINDOW), self.repo_before, "a test wrote into the repository")

    def cli(self, *args, code=0, stdin=None, env=None):
        r = subprocess.run([sys.executable, str(ROOT / "bin/mackit"), "--home", str(self.home), *args],
                           input=stdin, capture_output=True, text=True, env=env, timeout=60)
        if code is not None:
            self.assertEqual(r.returncode, code, r.stdout + r.stderr)
        return r

    def json(self, *args, code=0, stdin=None):
        out = json.loads(self.cli(*args, "--json", code=code, stdin=stdin).stdout)
        self.assertEqual(out["ok"], code == 0, out)
        return out

    def prepare(self):
        """mackit prepare: what the App's “预览配置变化” does first (copy the built-in source into ~/.local/share/mackit)."""
        root = Path(self.json("prepare")["root"])
        self.assertEqual(root, self.home / ".local/share/mackit")
        return root

    def test_help_lists_commands_and_hides_the_app_bridge(self):
        top = self.cli("--help").stdout
        self.assertNotIn("SUPPRESS", top)
        self.assertNotIn("gui", top.split("COMMAND", 1)[1].split("options", 1)[0].split())
        for name in ("plan", "apply", "doctor", "deps", "status", "restore", "link", "keys", "file", "window", "edit"):
            self.assertIn(name, top)
        for args in (["file", "write"], ["window", "hotkey", "add"], ["window", "rule", "add"], ["window", "service"], ["deps"], ["keys"]):
            self.cli(*args, "--help")

    def test_window_status_set_hotkey_rule_and_stale_digest(self):
        self.assertFalse(self.json("window", "status")["window"]["editable"])
        self.json("window", "set", "window_gap=12", code=1)  # yabai source not prepared yet
        source = self.prepare()
        status = self.json("window", "status")["window"]
        self.assertTrue(status["editable"])
        self.assertEqual({s["key"] for s in status["settingSpecs"]}, set(window.SPEC))
        first = status["digest"]
        saved = self.json("window", "set", "window_gap=12", "--digest", first, "--apply")
        self.assertEqual(saved["applied"], [])  # isolated HOME never touches running services
        rc = source / "components/yabai/config/yabairc"
        self.assertIn("window_gap 12", rc.read_text())
        self.assertTrue(Path(saved["backup"]).is_dir())
        stale = self.json("window", "set", "window_gap=14", "--digest", first, code=1)
        self.assertIn("error", stale)
        self.assertIn("window_gap 12", rc.read_text())
        self.json("window", "set", "layout=grid", code=1)  # same validation as the page
        self.json("window", "set", "--unset", "window_gap")
        self.assertNotIn("window_gap", rc.read_text())

        added = self.json("window", "hotkey", "add", "--key", "shift+alt+ctrl+k", "--action", "full", "--note", "test")
        self.assertIsInstance(added["conflicts"], list)
        skhd = source / "components/yabai/config/skhd/skhdrc"
        self.assertIn("ctrl + alt + shift - k : $HOME/.config/yabai/scripts/window/position.sh full", skhd.read_text())
        self.json("window", "hotkey", "add", "--key", "ctrl+alt+shift+k", "--action", "left", code=1)
        self.json("window", "hotkey", "add", "--key", "ctrl+alt+shift+k", "--command", "yabai -m window --focus west", "--replace")
        self.assertIn("ctrl + alt + shift - k : yabai -m window --focus west", skhd.read_text())
        self.json("window", "hotkey", "add", "--key", "k", "--action", "full", code=1)  # no modifier
        self.json("window", "hotkey", "remove", "--key", "ctrl+alt+shift+k")
        self.assertNotIn("ctrl + alt + shift - k", skhd.read_text())

        self.json("window", "rule", "add", "--app", "System Settings", "--manage", "off")
        self.assertIn('app="^System\\ Settings$" manage=off', rc.read_text())
        self.json("window", "rule", "add", "--app", "Evil\"; rm", "--manage", "off", code=1)
        self.json("window", "rule", "remove", "--app", "System Settings")
        self.assertNotIn("System", rc.read_text())

        whole = self.json("window", "status")
        whole["window"]["settings"] = {"layout": "bsp"}
        done = self.json("window", "save", "--from", "-", stdin=json.dumps(whole))
        self.assertIn("layout bsp", rc.read_text())
        self.assertEqual(done["digest"], self.json("window", "status")["window"]["digest"])
        self.json("window", "save", "--from", "-", stdin=json.dumps(whole), code=1)  # its digest is now stale

    def gui(self, request):
        r = subprocess.run([sys.executable, str(ROOT / "bin/mackit"), "--home", str(self.home), "gui"],
                           input=json.dumps(request), capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)  # the App's bridge always answers with one JSON object
        return json.loads(r.stdout)

    def test_isolated_home_installs_from_its_own_source(self):
        applied = json.loads(self.cli("apply", "--components", "yabai").stdout)
        source = self.home / ".local/share/mackit"
        self.assertEqual((self.home / ".config/yabai").resolve(), (source / "components/yabai/config").resolve())
        self.assertEqual(self.json("status")["root"], str(source))
        status = self.json("window", "status")["window"]
        self.json("window", "set", "window_gap=33", "--digest", status["digest"])
        self.assertIn("window_gap 33", (source / "components/yabai/config/yabairc").read_text())
        self.assertEqual(self.json("restore", applied["transaction"])["restored"], applied["transaction"])
        self.assertIn("without --home", self.cli("update", code=1).stderr)  # pulls a checkout; never from a sandbox
        # tearDown proves this checkout's files did not change.

    def test_isolated_home_with_a_source_outside_it_is_read_only(self):
        # A sandbox that recorded this checkout (source CLIs before 0.3.5 did) can read it but never write it.
        cfg = self.home / ".config/mackit"
        cfg.mkdir(parents=True)
        (cfg / "profile.json").write_text(json.dumps({"profile": "developer", "components": ["yabai"], "source_root": str(ROOT)}))
        status = self.json("window", "status")["window"]
        self.assertFalse(status["editable"])
        self.assertIn("演示目录的配置来源在它之外", self.json("window", "set", "window_gap=33", "--digest", status["digest"], code=1)["error"])
        keys = self.json("file", "read", "nvim-keys")
        self.assertEqual(Path(keys["path"]), ROOT / "components/nvim/lua/config/keymaps.lua")
        self.json("file", "write", "nvim-keys", "--digest", keys["digest"], "--from", "-", stdin="-- x\n", code=1)
        self.assertFalse(self.gui({"action": "saveFile", "file": "nvim-keys", "content": "-- x\n", "digest": keys["digest"]})["ok"])
        self.json("file", "write", "local", "--digest", "absent", "--from", "-", stdin="export X=1\n")  # inside the sandbox

    def test_refused_apply_leaves_nothing_and_prepare_is_the_cli_step(self):
        self.assertIn("plan changed", self.json("apply", "--components", "nvim", "--token", "deadbeef", code=1)["error"])
        self.assertFalse((self.home / ".local/share").exists(), "a refused apply created the source")
        self.assertIn("mackit prepare", self.json("file", "read", "local", code=1)["error"])
        self.assertIn("mackit prepare", self.json("window", "set", "window_gap=4", code=1)["error"])
        self.assertFalse(self.json("plan", "--components", "nvim")["source_ready"])
        first = self.json("prepare")
        self.assertEqual((first["created"], Path(first["root"])), (True, self.home / ".local/share/mackit"))
        self.assertFalse(self.json("prepare")["created"])
        self.assertTrue(self.json("plan", "--components", "nvim")["source_ready"])
        self.assertTrue(self.json("window", "status")["window"]["editable"])

    def test_window_save_rejects_wrong_json_types(self):
        self.json("prepare")
        digest = self.json("window", "status")["window"]["digest"]
        for bad in ({"hotkeys": [{"key": "ctrl+alt+h", "action": ["x"]}]},
                    {"hotkeys": [{"key": "ctrl+alt+h", "command": {"a": 1}}]},
                    {"hotkeys": ["ctrl+alt+h"]},
                    {"rules": [{"app": "Finder", "space": [1]}]},
                    {"rules": [{"app": ["Finder"], "manage": "off"}]}):
            body = {"settings": {}, "rules": [], "hotkeys": [], **bad}
            self.assertIn("error", self.json("window", "save", "--digest", digest, "--from", "-", stdin=json.dumps(body), code=1))
            self.assertFalse(self.gui({"action": "windowSave", "digest": digest, **body})["ok"])
        for request in ({"action": ["snapshot"]}, {"action": "readFile", "file": ["local"]},
                        {"action": "windowSave", "digest": digest, "settings": [], "rules": [], "hotkeys": []}):
            self.assertFalse(self.gui(request)["ok"])
        self.assertEqual(self.json("window", "status")["window"]["digest"], digest)

    def test_hotkey_warning_and_app_hint_use_the_source_catalog(self):
        source = self.prepare()
        catalog = source / "data/keys.json"
        rows = json.loads(catalog.read_text())
        rows.append({"component": "ghostty", "mode": "global", "key": "shift+alt+ctrl+f9", "description": "only in this source", "source": "test"})
        catalog.write_text(json.dumps(rows))
        added = self.json("window", "hotkey", "add", "--key", "ctrl+alt+shift+f9", "--action", "full")
        self.assertEqual([r["description"] for r in added["conflicts"]], ["only in this source"])
        self.assertEqual([r["description"] for r in self.json("keys", "--conflicts-with", "⌃⌥⇧F9")["conflicts"]], ["only in this source"])
        snapshot = self.gui({"action": "snapshot"})["keys"]
        self.assertEqual([r["description"] for r in snapshot if r.get("clash") == "ctrl+alt+shift+f9"], ["only in this source"])
        self.assertFalse([r for r in snapshot if r["component"] == "yabai" and "clash" in r])

    def test_window_status_shows_keys_in_recorder_order(self):
        source = self.prepare()
        (source / "components/yabai/config/skhd/hotkeys.json").write_text(json.dumps([{"key": "shift+ctrl+k", "action": "full"}]))
        status = self.json("window", "status")["window"]
        self.assertEqual(status["hotkeys"][0]["key"], "ctrl+shift+k")
        self.json("window", "save", "--from", "-", stdin=json.dumps(status))
        self.assertIn("ctrl + shift - k", (source / "components/yabai/config/skhd/skhdrc").read_text())

    def test_window_service_refused_on_isolated_home(self):
        self.prepare()
        out = self.json("window", "service", "stop", "skhd", code=1)
        self.assertIn("演示目录", out["error"])

    def test_file_list_read_write_with_digest_and_backup(self):
        self.json("file", "read", "local", code=1)  # like the App: prepare the source first
        self.prepare()
        listed = self.json("file", "list")
        ids = [f["id"] for f in listed["files"]]
        self.assertIn("local", ids)
        self.assertIn("hs-local", ids)
        self.assertNotIn("yabai", ids)  # generated; the window commands own it
        self.assertEqual(ids, [f["id"] for f in self.json("edit")["files"] if f["id"] != "vim"])
        self.cli("edit", "yabai", "--print", code=1)
        new = self.json("file", "read", "local")
        self.assertEqual(new["digest"], "absent")
        write = ["file", "write", "local", "--from", "-"]
        self.json(*write, "--digest", "absent", stdin="export X=1\n")
        current = self.json("file", "read", "local")
        self.assertEqual(current["content"], "export X=1\n")
        self.assertEqual(self.cli("file", "read", "local").stdout, "export X=1\n")
        self.json(*write, "--digest", "absent", stdin="export Y=2\n", code=1)  # stale digest
        saved = self.json(*write, "--digest", current["digest"], stdin="export Y=2\n")
        self.assertEqual(Path(saved["backup"]).read_text(), "export X=1\n")
        keys = self.json("file", "read", "nvim-keys")
        self.assertTrue(keys["path"].startswith(str(self.home / ".local/share/mackit")))
        self.json("file", "read", "../../.ssh/id_ed25519", code=1)

    def test_deps_state_and_install_refused_on_isolated_home(self):
        deps = self.json("deps", "--components", "tmux,ghostty")
        self.assertEqual({d["id"] for d in deps["dependencies"]}, {"tmux", "ghostty"})
        self.assertEqual(deps["missing"], [d["id"] for d in deps["dependencies"] if not d["installed"]])
        check = self.cli("deps", "--components", "tmux,ghostty", "--check", "--json", code=None)
        self.assertEqual(check.returncode, 1 if deps["missing"] else 0)
        self.assertEqual(json.loads(check.stdout)["ok"], not deps["missing"])
        out = self.json("deps", "--components", "tmux", "--install", code=1)
        self.assertIn("演示目录", out["error"])

    def test_status_plan_token_and_restore_json(self):
        status = self.json("status")
        self.assertIn("appVersion", status["app"])
        self.assertIn("commandLink", status)
        self.assertEqual(status["app"]["keyCount"] >= 900, True)
        plan = self.json("plan", "--components", "zsh")
        (self.home / ".zshrc").write_text("changed after review\n")
        self.cli("apply", "--components", "zsh", "--token", plan["token"], code=1)
        self.assertEqual((self.home / ".zshrc").read_text(), "changed after review\n")
        plan = self.json("plan", "--components", "zsh")
        tx = json.loads(self.cli("apply", "--components", "zsh", "--token", plan["token"]).stdout)["transaction"]
        self.assertEqual(self.json("restore", tx)["restored"], tx)
        self.assertEqual((self.home / ".zshrc").read_text(), "changed after review\n")

    def test_keys_honour_home_over_xdg_and_conflict_check(self):
        env = dict(os.environ, XDG_CONFIG_HOME=str(self.home / "elsewhere"))
        keysd = self.home / "elsewhere/mackit/keys.d"
        keysd.mkdir(parents=True)
        (keysd / "leak.json").write_text(json.dumps([{"component": "leak", "key": "cmd+ctrl+alt+shift+l", "description": "x"}]))
        found = json.loads(self.cli("keys", "--json", env=env).stdout)
        rows = found["rows"]
        self.assertEqual((found["ok"], found["count"]), (True, len(rows)))
        self.assertFalse([r for r in rows if r["component"] == "leak"], "an isolated --home read another config dir")
        mine = self.home / ".config/mackit/keys.d"
        mine.mkdir(parents=True)
        (mine / "demo.json").write_text(json.dumps([{"component": "demo", "key": "ctrl+alt+j", "description": "demo key"}]))
        hit = self.json("keys", "--conflicts-with", "⌃⌥J")
        self.assertEqual([r["component"] for r in hit["conflicts"]], ["demo"])
        self.assertFalse(hit["clear"])
        self.assertTrue(self.json("keys", "--conflicts-with", "ctrl+alt+shift+f12")["clear"])
        self.json("keys", "--conflicts-with", "q", code=1)

    def test_link_on_empty_home_reports_and_json_failures(self):
        out = self.json("restore", code=1)
        self.assertIn("No active installation", out["error"])
        doctor = json.loads(self.cli("doctor", "--components", "nvim", code=1).stdout)
        self.assertFalse(doctor["ok"])


class CanonicalKeyTests(unittest.TestCase):
    """One canonicaliser (localkeys.normalize) for doctor, keys --conflicts-with, window hotkey add and the
    App: the engine sends each row's "clash" key, and the 窗口 page only compares its recorded key with it."""
    def test_combo_forms(self):
        self.assertEqual(localkeys.combo("ctrl + shift - g"), "ctrl+shift+g")
        self.assertEqual(localkeys.combo("⇧⌘H"), "cmd+shift+h")
        self.assertEqual(localkeys.combo("hyper+y"), "cmd+ctrl+shift+y")  # Right Option → ⇧⌘⌃ (Karabiner)
        self.assertEqual(localkeys.combo("left-cmd+c"), "cmd+c")
        self.assertEqual(localkeys.combo("right-cmd+c"), "right-cmd+c")
        self.assertIsNone(localkeys.combo("space"))
        for key in ("ctrl + shift - g", "⇧⌘H", "hyper+y", "shift+alt+ctrl+k"):
            self.assertEqual(localkeys.combo(key), localkeys.normalize(key))

    def test_recorder_order_is_canonical(self):
        # KeyCombo.from (WindowPage.swift) emits cmd, ctrl, alt, shift + key; the engine must agree.
        self.assertEqual(localkeys.normalize("cmd+ctrl+alt+shift+k"), "cmd+ctrl+alt+shift+k")
        self.assertEqual(window.canonical_key("shift+alt+ctrl+cmd+k"), "cmd+ctrl+alt+shift+k")

    def test_doctor_sees_hyper_and_outside_terminals(self):
        rows = [{"component": "hammerspoon", "mode": "outside-terminals", "key": "ctrl+h", "description": "left"},
                {"component": "demo", "mode": "app:Demo", "key": "⌃H", "description": "back"},
                {"component": "term", "mode": "app:Ghostty", "key": "ctrl+h", "description": "erase"},
                {"component": "hammerspoon", "mode": "global", "key": "hyper+y", "description": "a"},
                {"component": "initials", "mode": "global", "key": "cmd+ctrl+shift+y", "description": "b"}]
        issues = localkeys.conflicts(rows, Path("/nonexistent"))
        self.assertEqual(len(issues), 2, issues)
        self.assertTrue(any("Demo key ctrl+h" in i for i in issues))
        self.assertFalse(any("Ghostty" in i for i in issues))  # Hammerspoon leaves terminals alone
        self.assertTrue(any("claimed twice: cmd+ctrl+shift+y" in i for i in issues))

    def test_clash_rules(self):
        rows = [{"component": "yabai", "mode": "global", "key": "ctrl + alt - h", "description": "own"},
                {"component": "hammerspoon", "mode": "outside-terminals", "key": "ctrl+alt+h", "description": "hs"},
                {"component": "tmux", "mode": "prefix", "key": "ctrl+alt+h", "description": "not global"},
                {"component": "ghostty", "mode": "global", "key": "ctrl+alt+h", "description": "other", "profile": "tianli"}]
        self.assertEqual([r["description"] for r in localkeys.clashes("⌃⌥H", rows, "developer")], ["hs"])
        self.assertEqual(len(localkeys.clashes("ctrl+alt+h", rows, "tianli")), 2)

    def test_doctor_normalize_reads_skhd_rows(self):
        self.assertEqual(localkeys.normalize("ctrl + shift - g"), localkeys.normalize("shift+ctrl+g"))

    def test_clash_key_is_the_single_rule(self):
        self.assertIsNone(localkeys.clash_key({"component": "yabai", "mode": "global", "key": "ctrl+alt+h"}))
        self.assertIsNone(localkeys.clash_key({"component": "hammerspoon", "mode": "global", "key": "right-cmd+c"}))
        self.assertIsNone(localkeys.clash_key({"component": "nvim", "mode": "n", "key": "ctrl+h"}))
        self.assertEqual(localkeys.clash_key({"component": "hammerspoon", "mode": "outside-terminals", "key": "ctrl+h"}), "ctrl+h")


if __name__ == "__main__":
    unittest.main()
