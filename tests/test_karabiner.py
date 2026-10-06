"""Karabiner rule commands and the reload after apply.

CLI calls run against a disposable HOME (its source prepared in <HOME>/.local/share/mackit); the reload
is exercised with a temporary state folder, a temporary log and injected "is it running" answers, so no
test renames a real generation, reads the real log or depends on Karabiner being installed here.
"""
import hashlib, json, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mackit import karabiner  # noqa: E402

REPO_SOURCE = ROOT / "components/karabiner/karabiner.json"
RULE = {"description": "F13 → F14 (test)", "manipulators": [{"type": "basic", "from": {"key_code": "f13"}, "to": [{"key_code": "f14"}]}]}
COMMAND_RULE = {"description": "runs a program", "manipulators": [
    {"type": "basic", "from": {"key_code": "f15"}, "to_delayed_action": {"to_if_invoked": [{"shell_command": "open -a Safari"}]}}]}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReloadTests(unittest.TestCase):
    """karabiner.reload on fabricated generations and a fabricated log."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mackit-karabiner-")
        self.state = Path(self.temp.name) / "state"
        self.log = Path(self.temp.name) / "core_service.log"
        self.log.write_text("[old] core_configuration is updated.\n")
        for name in ("20260101-000000-aaaaaa", "20260102-000000-bbbbbb", "20260103-000000-cccccc"):
            (self.state / "generations" / name / "karabiner").mkdir(parents=True)
            (self.state / "generations" / name / "karabiner/karabiner.json").write_text("{}")
        self.now = 0.0

    def tearDown(self):
        self.temp.cleanup()

    def reload(self, on_sleep=None, **kwargs):
        def sleep(seconds):
            self.now += seconds
            if on_sleep:
                on_sleep()
        options = {"log": self.log, "wait": 2.0, "is_installed": lambda: True, "is_running": lambda: True,
                   "sleep": sleep, "clock": lambda: self.now, **kwargs}
        return karabiner.reload(self.state, **options)

    def intact(self):
        return sorted(str(p.relative_to(self.state)) for p in self.state.rglob("*"))

    def test_nudges_previous_generations_and_confirms_from_a_new_log_line(self):
        before = self.intact()
        def karabiner_answers():
            with self.log.open("a") as f:
                f.write("[new] core_configuration is updated.\n")
        result = self.reload(karabiner_answers, skip="20260103-000000-cccccc")
        self.assertEqual((result["attempted"], result["reloaded"], result["reason"]), (True, True, ""))
        self.assertEqual(result["nudged"], ["20260102-000000-bbbbbb", "20260101-000000-aaaaaa"])  # not the one apply just made
        self.assertEqual(result["line"], "[new] core_configuration is updated.")  # the old line does not count
        self.assertEqual(self.intact(), before)  # every directory is back under its own name

    def test_one_bounded_wait_then_an_honest_not_confirmed(self):
        result = self.reload()
        self.assertEqual((result["attempted"], result["reloaded"], result["reason"]), (True, False, "not_confirmed"))
        self.assertEqual(len(result["nudged"]), 3)
        self.assertLessEqual(result["waited_ms"], 2200)
        self.assertGreaterEqual(result["waited_ms"], 2000)

    def test_skips_without_touching_anything_when_absent_or_stopped(self):
        before = self.intact()
        for options, reason in (({"is_installed": lambda: False}, "not_installed"), ({"is_running": lambda: False}, "not_running")):
            result = self.reload(**options)
            self.assertEqual((result["attempted"], result["reloaded"], result["reason"], result["nudged"]), (False, False, reason, []))
        self.assertEqual(self.reload(skip="x", log=self.log)["attempted"], True)
        empty = Path(self.temp.name) / "empty"
        self.assertEqual(karabiner.reload(empty, log=self.log, is_installed=lambda: True, is_running=lambda: True)["reason"], "no_generation")
        self.assertEqual(self.intact(), before)

    def test_unreadable_log_and_an_interrupted_nudge(self):
        stray = self.state / "generations/20260101-000000-aaaaaa/karabiner"
        stray.rename(stray.with_name("karabiner" + karabiner.NUDGE))  # a nudge that was killed half way
        result = self.reload(log=Path(self.temp.name) / "missing.log")
        self.assertEqual((result["attempted"], result["reloaded"], result["reason"]), (True, False, "log_unreadable"))
        self.assertTrue(stray.is_dir())
        self.assertEqual(len(result["nudged"]), 3)

    def test_a_rotated_log_is_read_from_its_start(self):
        self.log.write_text("x" * 500 + "\n")
        def rotated():
            self.log.write_text("[rotated] core_configuration is updated.\n")
        self.assertTrue(self.reload(rotated)["reloaded"])


class RuleTests(unittest.TestCase):
    def test_validation_and_the_no_program_invariant(self):
        self.assertEqual(karabiner.clean_rule(RULE)["description"], RULE["description"])
        for bad in ([], {"description": "x"}, {"description": "", "manipulators": RULE["manipulators"]},
                    {"description": "x", "manipulators": [{"type": "basic"}]}, {**RULE, "enabled": "no"}, COMMAND_RULE):
            with self.assertRaises(ValueError, msg=bad):
                karabiner.clean_rule(bad)
        rules = [dict(COMMAND_RULE, enabled=False)]
        with self.assertRaises(ValueError):
            karabiner.set_enabled(rules, 0, True)  # a hand-written command rule cannot be switched on from here
        # The shipped source holds no shell_command at all, enabled or not.
        shipped = karabiner.rules_of(karabiner.profile_of(karabiner.parse(REPO_SOURCE.read_text())))
        self.assertFalse(any(karabiner.has_command(r) for r in shipped))

    def test_enable_and_disable_use_karabiners_own_spelling(self):
        rules = [dict(RULE)]
        self.assertTrue(karabiner.set_enabled(rules, 0, False))
        self.assertEqual(list(rules[0]), ["description", "enabled", "manipulators"])
        self.assertFalse(karabiner.set_enabled(rules, 0, False))
        self.assertTrue(karabiner.set_enabled(rules, 0, True))
        self.assertEqual(rules, [RULE])

    def test_source_layout_round_trips(self):
        text = REPO_SOURCE.read_text()
        self.assertEqual(karabiner.render(karabiner.parse(text)), text)


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mackit-karabiner-cli-")
        self.home = Path(self.temp.name)
        self.repo_before = sha(REPO_SOURCE)

    def tearDown(self):
        self.temp.cleanup()
        self.assertEqual(sha(REPO_SOURCE), self.repo_before, "a test wrote into the repository")

    def cli(self, *args, code=0, stdin=None):
        r = subprocess.run([sys.executable, str(ROOT / "bin/mackit"), "--home", str(self.home), *args],
                           input=stdin, capture_output=True, text=True, timeout=60)
        if code is not None:
            self.assertEqual(r.returncode, code, r.stdout + r.stderr)
        return r

    def json(self, *args, code=0, stdin=None):
        out = json.loads(self.cli(*args, "--json", code=code, stdin=stdin).stdout)
        self.assertEqual(out["ok"], code == 0, out)
        return out

    def rule(self, *args, **kwargs):
        return self.json("karabiner", "rule", *args, **kwargs)

    def test_rules_list_show_add_replace_disable_enable_remove(self):
        listed = self.rule("list")  # readable from the built-in copy before any source exists
        self.assertEqual(listed["count"], len(listed["rules"]))
        self.assertEqual([r["index"] for r in listed["rules"]], list(range(1, listed["count"] + 1)))
        self.assertEqual(Path(listed["source"]), REPO_SOURCE)
        self.assertIn("error", self.rule("add", stdin=json.dumps(RULE), code=1))  # no prepared source to write
        source = Path(self.json("prepare")["root"]) / "components/karabiner/karabiner.json"
        original = source.read_bytes()
        first = self.rule("list")
        self.assertEqual(Path(first["source"]), source)
        self.assertEqual(first["digest"], self.json("file", "read", "karabiner")["digest"])  # the 配置文件 page's lock

        added = self.rule("add", "--digest", first["digest"], stdin=json.dumps(RULE))
        self.assertEqual((added["action"], added["changed"], added["index"], added["count"], added["applied"]), ("add", True, first["count"] + 1, first["count"] + 1, False))
        self.assertEqual(Path(added["backup"]).read_bytes(), original)  # the copy of what was replaced
        self.assertEqual(added["digest"], sha(source))
        shown = self.rule("show", "--description", RULE["description"])
        self.assertEqual((shown["rule"], shown["enabled"], shown["from"]), (RULE, True, ["f13"]))
        self.assertEqual(json.loads(self.cli("karabiner", "rule", "show", "--index", str(added["index"])).stdout), RULE)

        self.assertIn("changed since", self.rule("remove", "--index", "1", "--digest", first["digest"], code=1)["error"])  # stale digest
        self.assertIn("--replace", self.rule("add", stdin=json.dumps(RULE), code=1)["error"])
        self.assertIn("shell_command", self.rule("add", stdin=json.dumps(COMMAND_RULE), code=1)["error"])
        self.rule("add", stdin="not json", code=1)
        self.rule("show", "--index", "99", code=1)
        self.assertEqual(sha(source), added["digest"])  # none of the refusals wrote

        changed = dict(RULE, manipulators=[{"type": "basic", "from": {"key_code": "f13"}, "to": [{"key_code": "f16"}]}])
        replaced = self.rule("add", "--replace", stdin=json.dumps(changed))
        self.assertEqual((replaced["replaced"], replaced["index"], replaced["count"]), (True, added["index"], added["count"]))
        self.rule("add", "--replace", stdin=json.dumps(RULE))

        off = self.rule("disable", "--description", RULE["description"])
        self.assertTrue(off["changed"])
        self.assertFalse(self.rule("show", "--index", str(off["index"]))["enabled"])
        self.assertFalse(self.rule("disable", "--index", str(off["index"]))["changed"])  # already off: nothing written
        self.assertTrue(self.rule("enable", "--index", str(off["index"]))["changed"])
        self.assertEqual(sha(source), added["digest"])  # enabled again = the same bytes as before disabling

        top = self.rule("add", "--at", "1", stdin=json.dumps(dict(RULE, description="first (test)")))
        self.assertEqual(top["index"], 1)
        self.rule("remove", "--index", "1")
        gone = self.rule("remove", "--description", RULE["description"])
        self.assertEqual(gone["count"], first["count"])
        self.assertEqual(source.read_bytes(), original)  # add then remove leaves the file byte-identical
        self.rule("remove", "--description", RULE["description"], code=1)

    def test_apply_reports_the_reload_and_never_reaches_karabiner_from_a_sandbox(self):
        self.assertNotIn("karabiner", json.loads(self.cli("apply", "--components", "fd").stdout))
        applied = json.loads(self.cli("apply", "--components", "karabiner").stdout)
        self.assertEqual((applied["karabiner"]["attempted"], applied["karabiner"]["reason"]), (False, "isolated_home"))
        again = json.loads(self.cli("apply", "--components", "karabiner").stdout)
        self.assertEqual(again["karabiner"]["reason"], "unchanged")  # same content: nothing re-pointed, nothing to re-read
        live = self.home / ".config/karabiner/karabiner.json"
        self.assertNotIn(RULE["description"], live.read_text())
        added = self.rule("add", "--apply", stdin=json.dumps(RULE))
        self.assertTrue(added["applied"])
        self.assertEqual(added["installation"]["karabiner"]["reason"], "isolated_home")
        self.assertIn(RULE["description"], live.read_text())  # one command: source edited and the generated file re-made
        status = self.json("karabiner", "status")["karabiner"]
        self.assertEqual((status["editable"], status["config"]["managed"], status["shellCommands"]), (True, True, 0))
        self.assertEqual(status["rules"], added["count"])
        self.assertIn("isolated", self.json("karabiner", "reload", code=1)["error"])

    def test_apply_flag_without_the_component_saves_and_says_so(self):
        self.json("prepare")
        added = self.rule("add", "--apply", stdin=json.dumps(RULE))
        self.assertFalse(added["applied"])
        self.assertIn("not installed", added["applyNote"])
        self.assertFalse((self.home / ".config/karabiner").exists())

    def test_select_remembers_the_choice_the_app_shows(self):
        self.json("select", code=1)
        self.json("select", "--components", "zsh,nope", code=1)
        chosen = self.json("select", "--profile", "developer", "--components", "nvim,zsh")
        self.assertEqual(chosen["components"], ["nvim", "zsh"])
        self.assertEqual(self.json("status")["app"]["selected"], ["nvim", "zsh"])
        self.assertFalse((self.home / ".config/nvim").exists())  # remembered, not installed
        self.cli("apply", "--components", "fd")
        self.assertIn("locked", self.json("select", "--profile", "tianli", code=1)["error"])

    def test_help_states_the_contract_and_usage_errors_answer_in_json(self):
        top = self.cli("--help").stdout
        for text in ("读命令", "写命令", "--json", '{"ok": false, "error"', "退出码", "仅在窗口中", "暂无命令", "karabiner rule add|remove|enable|disable", "karabiner reload", "select"):
            self.assertIn(text, top)
        for args in (["karabiner"], ["karabiner", "rule"], ["karabiner", "rule", "add"], ["karabiner", "rule", "enable"], ["select"]):
            self.cli(*args, "--help")
        wrong = self.cli("karabiner", "rule", "bogus", "--json", code=2)
        self.assertEqual(json.loads(wrong.stdout)["ok"], False)
        self.assertTrue(json.loads(wrong.stdout)["error"].startswith("usage:"))
        self.assertEqual(self.cli("karabiner", "rule", "bogus", code=2).stdout, "")  # without --json: stderr only, as before


if __name__ == "__main__":
    unittest.main()
