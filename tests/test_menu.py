import argparse
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mackit import cli, menu, window


class MenuTests(unittest.TestCase):
    def test_sandbox_cannot_read_or_open_user_apps(self):
        with tempfile.TemporaryDirectory() as home, patch.object(menu, "binary") as native:
            for verb in ("status", "scan", "show", "execute"):
                with self.assertRaisesRegex(ValueError, "隔离"):
                    menu.command(argparse.Namespace(menu_command=verb), Path(home), cli.ROOT)
            native.assert_not_called()

    def test_scan_uses_native_exact_pid_without_shell(self):
        args = argparse.Namespace(menu_command="scan", pid=123)
        with patch.object(menu, "binary", return_value=Path("/native/MacKit")), patch.object(menu.subprocess, "run") as run:
            run.return_value = argparse.Namespace(returncode=0, stdout='{"ok":true,"items":[]}', stderr="")
            self.assertEqual(menu.command(args, Path.home(), cli.ROOT)["items"], [])
            self.assertEqual(run.call_args.args[0], ["/native/MacKit", "--menu-scan", "--pid", "123"])
            self.assertNotIn("shell", run.call_args.kwargs)

    def test_incomplete_scan_is_not_success(self):
        with patch.object(menu, "binary", return_value=Path("/native/MacKit")), patch.object(menu.subprocess, "run") as run:
            run.return_value = argparse.Namespace(returncode=1, stdout='{"ok":true,"complete":false,"warnings":["超时"]}', stderr="")
            with self.assertRaisesRegex(ValueError, "超时"):
                menu.command(argparse.Namespace(menu_command="scan", pid=None), Path.home(), cli.ROOT)

    def test_execute_requires_nonempty_exact_path(self):
        with patch.object(menu, "binary", return_value=Path("/native/MacKit")), patch.object(menu.subprocess, "run") as run:
            for value in ('{}', '[]', '[1]', '[""]', 'not JSON'):
                with self.assertRaises(ValueError):
                    menu.command(argparse.Namespace(menu_command="execute", pid=123, path_json=value), Path.home(), cli.ROOT)
            run.assert_not_called()

    def test_execute_preserves_unicode_and_path(self):
        path = ["文件", "写笔记"]
        with patch.object(menu, "binary", return_value=Path("/native/MacKit")), patch.object(menu.subprocess, "run") as run:
            run.return_value = argparse.Namespace(returncode=0, stdout='{"ok":true}', stderr="")
            menu.command(argparse.Namespace(menu_command="execute", pid=123, path_json=json.dumps(path)), Path.home(), cli.ROOT)
            self.assertEqual(json.loads(run.call_args.args[0][-1]), path)

    def test_public_cli_menu_parser_and_json_error(self):
        with tempfile.TemporaryDirectory() as home, contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["--home", home, "menu", "scan", "--json"]), 1)
            self.assertFalse(json.loads(out.getvalue())["ok"])

    def test_action_is_available_without_default_global_binding(self):
        self.assertIn("--menu-search", window.ACTIONS["menu-search"][1])
        bindings = window.load(cli.ROOT)["hotkeys"]
        self.assertFalse(any(row.get("action") == "menu-search" for row in bindings))


if __name__ == "__main__":
    unittest.main()
