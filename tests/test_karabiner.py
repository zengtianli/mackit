"""Karabiner rule commands and the reload after apply.

CLI calls run against a disposable HOME (its source prepared in <HOME>/.local/share/mackit); the reload
is exercised with a temporary state folder, a temporary link, a temporary log and injected "is it running"
answers, so no test renames a real generation, re-points the real ~/.config/karabiner or depends on Karabiner
being installed here. Whether a re-read is due is decided from the log line's own time against the time the
fixture's link and file changed, so the lines are stamped in the past or the future on purpose.
"""
import hashlib, json, os, subprocess, sys, tempfile, time, unittest
from unittest import mock
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


def line(offset, tag="x"):
    """A log line as Karabiner writes it, stamped `offset` seconds from now."""
    return time.strftime("[%Y-%m-%d %H:%M:%S.000]", time.localtime(time.time() + offset)) + f" [info] [core_service (daemon)] {tag} core_configuration is updated.\n"


class ReloadTests(unittest.TestCase):
    """karabiner.reload on fabricated generations, a fabricated ~/.config/karabiner link and a fabricated log."""
    NAMES = ("20260101-000000-aaaaaa", "20260102-000000-bbbbbb", "20260103-000000-cccccc")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mackit-karabiner-")
        self.state = Path(self.temp.name) / "state"
        self.log = Path(self.temp.name) / "core_service.log"
        self.link = Path(self.temp.name) / "config/karabiner"
        self.link.parent.mkdir()
        for i, name in enumerate(self.NAMES):
            (self.state / "generations" / name / "karabiner").mkdir(parents=True)
            (self.state / "generations" / name / "karabiner/karabiner.json").write_text(json.dumps({"n": i}))
        self.point(self.NAMES[1])
        self.log.write_text(line(-3600, "old"))  # Karabiner's last logged load is an hour older than the link
        self.now = 0.0

    def tearDown(self):
        self.temp.cleanup()

    def point(self, name):
        if self.link.is_symlink():
            self.link.unlink()
        self.link.symlink_to(self.state / "generations" / name / "karabiner")

    def reload(self, on_sleep=None, **kwargs):
        def sleep(seconds):
            self.now += seconds
            if on_sleep:
                on_sleep()
        options = {"log": self.log, "wait": 2.0, "link": self.link, "is_installed": lambda: True, "is_running": lambda: True,
                   "sleep": sleep, "clock": lambda: self.now, **kwargs}
        return karabiner.reload(self.state, **options)

    def intact(self):
        return sorted(str(p.relative_to(self.state)) for p in self.state.rglob("*"))

    def answer(self, tag="new", offset=60):
        def karabiner_answers():
            with self.log.open("a") as f:
                f.write(line(offset, tag))
        return karabiner_answers

    def test_a_changed_file_is_nudged_and_confirmed_from_a_new_log_line(self):
        self.point("20260103-000000-cccccc")  # apply just made this one and re-pointed the link at it
        before = self.intact()
        self.assertEqual(karabiner.loaded(self.link, self.log)["current"], False)  # the link is newer than the last load
        watched, away = self.state / "generations/20260102-000000-bbbbbb/karabiner", []

        def karabiner_answers():
            away.append(not watched.exists())
            self.answer()()
        result = self.reload(karabiner_answers, skip="20260103-000000-cccccc")
        self.assertEqual((result["attempted"], result["reloaded"], result["current"], result["expected"], result["reason"]), (True, True, True, True, ""))
        # A rename undone at once goes unnoticed by Karabiner (measured 2026-10-07), so the directory stays away for a moment.
        self.assertTrue(away[0])
        # Newest first, not the one apply just made, and the older ones are left alone once one answered.
        self.assertEqual(result["nudged"], ["20260102-000000-bbbbbb"])
        self.assertIn("new core_configuration is updated.", result["line"])  # the old line does not count
        self.assertEqual(self.intact(), before)  # every directory is back under its own name

    def test_it_should_have_re_read_and_did_not(self):
        result = self.reload()  # the link changed after the last logged load, the nudge is sent, no line comes
        self.assertEqual((result["attempted"], result["reloaded"], result["current"], result["expected"], result["reason"]),
                         (True, False, False, True, "not_confirmed"))
        # The directory the link points at is never renamed: for that moment the active configuration would be missing.
        self.assertEqual(result["nudged"], ["20260103-000000-cccccc", "20260101-000000-aaaaaa"])
        self.assertLessEqual(result["waited_ms"], 2200)
        self.assertGreaterEqual(result["waited_ms"], 2000)

    def test_an_unchanged_file_expects_no_new_line_and_nothing_is_renamed(self):
        self.log.write_text(line(-3600, "old") + line(60, "loaded"))  # a load newer than the link and the file
        seen = []
        result = self.reload(lambda: seen.append("slept"))
        self.assertEqual((result["attempted"], result["reloaded"], result["current"], result["expected"], result["reason"], result["nudged"], result["waited_ms"]),
                         (False, False, True, False, "already_current", [], 0))
        self.assertIn("loaded core_configuration", result["line"])
        self.assertEqual(seen, [])  # no wait either: there is nothing to wait for
        state = karabiner.loaded(self.link, self.log)
        self.assertEqual((state["current"], bool(state["changedAt"]), bool(state["loadedAt"])), (True, True, True))

    def test_a_rewritten_file_or_a_re_pointed_link_makes_a_re_read_due_again(self):
        self.log.write_text(line(5, "loaded"))
        self.assertTrue(karabiner.loaded(self.link, self.log)["current"])
        active = self.link / "karabiner.json"
        os.utime(active, (time.time() + 120, time.time() + 120))  # content written after that load
        self.assertEqual(karabiner.loaded(self.link, self.log)["current"], False)
        os.utime(active, (time.time() - 120, time.time() - 120))
        self.assertTrue(karabiner.loaded(self.link, self.log)["current"])
        self.log.write_text(line(-5, "loaded"))
        self.point(self.NAMES[2])  # apply or restore moved the link after that load
        self.assertEqual(karabiner.loaded(self.link, self.log)["current"], False)

    def test_apply_re_pointing_to_the_same_bytes_is_not_a_missed_re_read(self):
        # What apply saw before it moved the link: Karabiner had loaded the then-active file.
        before = {"current": True, "digest": sha(self.link / "karabiner.json"), "line": line(-3600, "old").strip()}
        same = self.state / "generations" / self.NAMES[2] / "karabiner/karabiner.json"
        same.write_bytes((self.link / "karabiner.json").read_bytes())
        self.point(self.NAMES[2])  # the link is newer than the last load, the bytes Karabiner holds are not
        self.assertEqual(karabiner.loaded(self.link, self.log)["current"], False)
        result = self.reload(before=before, skip=self.NAMES[2])
        self.assertEqual((result["attempted"], result["reloaded"], result["current"], result["expected"], result["reason"], result["nudged"]),
                         (False, False, True, False, "content_unchanged", []))
        same.write_text("{\"different\": true}")  # other bytes: now a re-read is due, and its absence is reported
        result = self.reload(before=before, skip=self.NAMES[2])
        self.assertEqual((result["attempted"], result["current"], result["expected"], result["reason"]), (True, False, True, "not_confirmed"))
        stale = dict(before, current=False)  # Karabiner was already behind before apply: equal bytes prove nothing
        same.write_bytes((self.state / "generations" / self.NAMES[1] / "karabiner/karabiner.json").read_bytes())
        self.assertEqual(self.reload(before=stale, skip=self.NAMES[2])["reason"], "not_confirmed")

    def test_a_line_karabiner_wrote_by_itself_after_apply_counts_as_the_re_read(self):
        before = karabiner.loaded(self.link, self.log)
        self.point(self.NAMES[2])
        self.answer("by itself")()  # Karabiner noticed the new link before the nudge was needed
        result = self.reload(before=before, skip=self.NAMES[2])
        self.assertEqual((result["attempted"], result["reloaded"], result["current"], result["reason"], result["nudged"]), (False, True, True, "", []))
        self.assertIn("by itself", result["line"])

    def test_without_an_earlier_load_line_the_answer_is_unknown_not_failed_or_fine(self):
        self.log.write_text("[2026-01-01 00:00:00.000] [info] something else\n")
        self.assertIsNone(karabiner.loaded(self.link, self.log)["current"])
        result = self.reload()
        self.assertEqual((result["attempted"], result["reloaded"], result["current"], result["expected"], result["reason"]),
                         (True, False, None, None, "not_confirmed"))
        self.assertTrue(self.reload(self.answer())["reloaded"])

    def test_the_rotated_log_still_answers_and_stamps_parse(self):
        self.log.with_name("core_service.1.log").write_text(line(60, "rotated"))
        self.log.write_text("[2026-01-01 00:00:00.000] [info] fresh file, no load yet\n")
        self.assertEqual(self.reload()["reason"], "already_current")
        at = karabiner.stamp("[2026-10-06 19:22:41.310] [info] [core_service (daemon)] core_configuration is updated.")
        self.assertEqual(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(at)), "2026-10-06 19:22:41")
        self.assertAlmostEqual(at % 1, 0.31, places=2)
        self.assertIsNone(karabiner.stamp("core_configuration is updated."))

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
        self.assertEqual(len(result["nudged"]), 2)  # every generation but the active one

    def test_a_rotated_log_is_read_from_its_start(self):
        self.log.write_text("x" * 500 + "\n")
        def rotated():
            self.log.write_text(line(60, "rotated"))
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
        self.assertEqual(self.rule("add", stdin=json.dumps(RULE), code=1)["error"]["code"], "not_prepared")  # no prepared source to write
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

        stale = self.rule("remove", "--index", "1", "--digest", first["digest"], code=1)["error"]  # stale digest
        self.assertEqual((stale["code"], "changed since" in stale["message"]), ("stale_digest", True))
        exists = self.rule("add", stdin=json.dumps(RULE), code=1)["error"]
        self.assertEqual((exists["code"], "--replace" in exists["message"]), ("exists", True))
        refused = self.rule("add", stdin=json.dumps(COMMAND_RULE), code=1)["error"]
        self.assertEqual((refused["code"], "shell_command" in refused["message"]), ("shell_command", True))
        # Opening an application is starting a program too, whichever way the rule spells it.
        opener = {"description": "open an app", "manipulators": [{"type": "basic", "from": {"key_code": "f16"},
                  "to": [{"software_function": {"open_application": {"bundle_identifier": "com.apple.Safari"}}}]}]}
        self.assertEqual(self.rule("add", stdin=json.dumps(opener), code=1)["error"]["code"], "shell_command")
        self.assertEqual(self.rule("add", stdin="not json", code=1)["error"]["code"], "invalid_json")
        self.assertEqual(self.rule("add", stdin=json.dumps({"description": "x"}), code=1)["error"]["code"], "invalid_rule")
        self.assertEqual(self.rule("show", "--index", "99", code=1)["error"]["code"], "not_found")
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
        self.assertEqual(set(again["karabiner"]), {"attempted", "reloaded", "current", "expected", "reason", "nudged", "waited_ms", "log", "line"})
        live = self.home / ".config/karabiner/karabiner.json"
        self.assertNotIn(RULE["description"], live.read_text())
        added = self.rule("add", "--apply", stdin=json.dumps(RULE))
        self.assertTrue(added["applied"])
        self.assertEqual(added["installation"]["karabiner"]["reason"], "isolated_home")
        self.assertIn("was not asked to re-read (isolated_home)", added["applyNote"])  # not "unconfirmed": nothing was asked
        self.assertIn(RULE["description"], live.read_text())  # one command: source edited and the generated file re-made
        status = self.json("karabiner", "status")["karabiner"]
        self.assertEqual((status["editable"], status["config"]["managed"], status["shellCommands"]), (True, True, 0))
        self.assertEqual(status["rules"], added["count"])
        self.assertEqual(status["loaded"], {"current": None, "changedAt": "", "loadedAt": ""})  # a sandbox link is not what Karabiner reads
        self.assertEqual(self.json("karabiner", "reload", code=1)["error"]["code"], "isolated_home")

    def test_apply_flag_without_the_component_saves_and_says_so(self):
        self.json("prepare")
        added = self.rule("add", "--apply", stdin=json.dumps(RULE))
        self.assertFalse(added["applied"])
        self.assertIn("not installed", added["applyNote"])
        self.assertFalse((self.home / ".config/karabiner").exists())

    def test_select_remembers_the_choice_the_app_shows(self):
        self.assertEqual(self.json("select", code=1)["error"]["code"], "nothing_to_change")
        self.assertEqual(set(self.json("select", "--components", "zsh,nope", code=1)["error"]), {"code", "message"})
        chosen = self.json("select", "--profile", "developer", "--components", "nvim,zsh")
        self.assertEqual(chosen["components"], ["nvim", "zsh"])
        status = self.json("status")["app"]
        self.assertEqual((status["selected"], status["appBuild"]), (["nvim", "zsh"], ""))  # a source checkout has no bundle build
        self.assertFalse((self.home / ".config/nvim").exists())  # remembered, not installed
        self.cli("apply", "--components", "fd")
        self.assertEqual(self.json("select", "--profile", "tianli", code=1)["error"]["code"], "preset_locked")

    def test_help_states_the_contract_and_usage_errors_answer_in_json(self):
        top = self.cli("--help").stdout
        for text in ("读命令", "写命令", "--json", '{"ok": false, "error"', '"error": {"code"', "退出码", "仅在窗口中", "karabiner rule add|remove|enable|disable",
                     "karabiner reload", "select", "already_current", "not_confirmed", "app.appBuild",
                     # every human entry of project.yaml's sop.agent_cli is named under 仅在窗口中
                     "switch pages", "使用帮助", "打开在线手册", "Karabiner installer", "install Homebrew", "Input Monitoring", "shortcut's source",
                     "config file in Finder", "backup folder", "record a key", "unsaved draft", "操作进行中", "progress bar", "配置与更新…"):
            self.assertIn(text, top)
        self.assertNotIn("暂无命令", top)  # every item of the App has a command or is listed under 仅在窗口中: project.yaml has no missing entry
        for args in (["karabiner"], ["karabiner", "rule"], ["karabiner", "rule", "add"], ["karabiner", "rule", "enable"], ["select"]):
            self.cli(*args, "--help")
        wrong = self.cli("karabiner", "rule", "bogus", "--json", code=2)
        self.assertEqual(json.loads(wrong.stdout)["ok"], False)
        self.assertEqual(json.loads(wrong.stdout)["error"]["code"], "usage")
        older = self.cli("status", "--json", "--no-such-flag", code=2)  # commands that predate the convention keep their string
        self.assertTrue(json.loads(older.stdout)["error"].startswith("usage:"))
        self.assertEqual(self.cli("karabiner", "rule", "bogus", code=2).stdout, "")  # without --json: stderr only, as before


class BridgeTests(unittest.TestCase):
    def test_the_install_banner_says_what_happened_to_karabiner(self):
        from mackit import cli, gui
        self.assertEqual(gui.karabiner_note(None), "")
        self.assertIn("已读入", gui.karabiner_note({"reloaded": True, "reason": ""}))
        for quiet in ("already_current", "content_unchanged", "unchanged", "isolated_home", "not_running", "not_installed"):
            self.assertEqual(gui.karabiner_note({"reloaded": False, "reason": quiet}), "")
        for loud in ("not_confirmed", "log_unreadable"):
            self.assertIn("mackit karabiner reload", gui.karabiner_note({"reloaded": False, "reason": loud}))
        self.assertEqual(cli.first_command(["--home", "/x", "--json", "karabiner", "rule"]), "karabiner")
        self.assertEqual(cli.first_command(["--home=/x", "status"]), "status")

    def test_status_reports_the_build_number_of_the_app_it_ships_in(self):
        import plistlib
        from mackit import cli
        with tempfile.TemporaryDirectory(prefix="mackit-bundle-") as temp:
            exe = Path(temp) / "MacKit.app/Contents/Resources/core/bin/mackit"
            exe.parent.mkdir(parents=True)
            exe.write_text("")
            (Path(temp) / "MacKit.app/Contents/Info.plist").write_bytes(plistlib.dumps({"CFBundleVersion": "2026100701"}))
            with mock.patch.object(cli, "bundled_cli", lambda: exe):
                self.assertEqual(cli.bundle_build(), "2026100701")
            (Path(temp) / "MacKit.app/Contents/Info.plist").write_text("not a plist")
            with mock.patch.object(cli, "bundled_cli", lambda: exe):
                self.assertEqual(cli.bundle_build(), "")
        self.assertEqual(cli.bundle_build(), "")  # a source checkout


if __name__ == "__main__":
    unittest.main()
