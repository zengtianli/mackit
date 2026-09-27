#!/usr/bin/env python3
"""Exercise the real transaction/recovery entrypoints in disposable homes."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

from _common import ROOT, cli, finish, isolated_home

sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT))
from mackit import cli as product_cli


def receipt(home, transaction):
    return home / ".local/state/mackit/transactions" / (transaction + ".json")


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def round_trip():
    with isolated_home() as scratch:
        home = Path(scratch)
        zsh = home / ".zshrc"
        zsh.write_text("original shell\n")
        nvim = home / ".config/nvim"
        nvim.mkdir(parents=True)
        (nvim / "user.lua").write_text("original editor configuration\n")
        result = json.loads(cli(home, "apply", "--components", "zsh,nvim").stdout)
        require(zsh.is_symlink() and nvim.is_symlink(), "apply did not link both components")
        require(nvim.resolve() == ROOT / "components/nvim", "nvim points to an unexpected source")
        saved = json.loads(receipt(home, result["transaction"]).read_text())
        backups = {Path(op["target"]).name: Path(op["backup"]) for op in saved["operations"]}
        require(backups[".zshrc"].read_text() == "original shell\n", "shell backup differs")
        require((backups["nvim"] / "user.lua").read_text() == "original editor configuration\n",
                "editor directory backup differs")
        again = json.loads(cli(home, "apply", "--components", "zsh,nvim").stdout)
        require(again["changed"] == 0, "repeated apply is not idempotent")
        cli(home, "restore", result["transaction"])
        require(not zsh.is_symlink() and zsh.read_text() == "original shell\n", "shell restore differs")
        require(not nvim.is_symlink() and (nvim / "user.lua").read_text() == "original editor configuration\n",
                "editor directory restore differs")
        require(json.loads(receipt(home, result["transaction"]).read_text())["status"] == "restored",
                "restore did not persist transaction status")
        repeated = cli(home, "restore", ok=False)
        require(repeated.returncode != 0 and "No active installation" in repeated.stderr,
                "restoring an already-restored transaction should refuse cleanly")
        require(zsh.read_text() == "original shell\n", "repeated restore changed the original")
    return "Original file and directory backed up/restored; repeated apply changes zero entries; repeated restore refuses safely."


def protect_user_edits(interrupted=False):
    with isolated_home() as scratch:
        home = Path(scratch)
        zsh = home / ".zshrc"
        zsh.write_text("original before apply\n")
        result = json.loads(cli(home, "apply", "--components", "zsh").stdout)
        path = receipt(home, result["transaction"])
        record = json.loads(path.read_text())
        if interrupted:
            # Reproduce the on-disk journal state left by an interrupted process.
            record["status"] = "installing"
            path.write_text(json.dumps(record))
            blocked = cli(home, "apply", "--components", "zsh", ok=False)
            require(blocked.returncode != 0 and "Interrupted installation found" in blocked.stderr,
                    "pending transaction did not block a second apply")
            require(json.loads(path.read_text())["status"] == "installing", "blocked apply changed pending journal")
        installed_link = os.readlink(zsh)
        zsh.unlink()
        zsh.write_text("new user work\n")
        denied = cli(home, "restore", result["transaction"], ok=False)
        require(denied.returncode != 0, "restore accepted a changed target")
        require(zsh.read_text() == "new user work\n", "restore overwrote user work")
        backup = next(Path(op["backup"]) for op in record["operations"] if op["target"] == str(zsh))
        require(backup.read_text() == "original before apply\n", "failed restore changed the original backup")
        # Follow the documented preserve-before-restore path, keeping both versions.
        preserved = home / "saved-user.zshrc"
        zsh.replace(preserved)
        zsh.symlink_to(installed_link)
        cli(home, "restore", result["transaction"])
        require(zsh.read_text() == "original before apply\n", "restore after preserving edits failed")
        require(preserved.read_text() == "new user work\n", "preserved user work was lost")
        require(json.loads(path.read_text())["status"] == "restored", "recovered journal was not finalized")
    return ("Interrupted journal blocks apply; " if interrupted else "") + "restore protects new edits and original backup; preserving edits allows recovery."


def injected_failure():
    with isolated_home() as scratch:
        home = Path(scratch)
        zsh = home / ".zshrc"
        zsh.write_text("original before fault\n")
        nvim = home / ".config/nvim"
        nvim.mkdir(parents=True)
        (nvim / "user.lua").write_text("editor before fault\n")
        original = Path.symlink_to
        injected = []

        def fail_editor_link(path, *args, **kwargs):
            if path == nvim:
                injected.append(True)
                raise OSError("acceptance injected link failure")
            return original(path, *args, **kwargs)

        isolated_env = {"HOME": str(home), "XDG_CONFIG_HOME": str(home / ".config"),
                        "XDG_STATE_HOME": str(home / ".local/state"),
                        "XDG_CACHE_HOME": str(home / ".cache")}
        output, errors = io.StringIO(), io.StringIO()
        with patch.dict(os.environ, isolated_env), patch.object(Path, "symlink_to", fail_editor_link), \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            code = product_cli.main(["--home", str(home), "apply", "--components", "zsh,nvim"])
        require(code != 0 and len(injected) == 1 and "acceptance injected link failure" in errors.getvalue(),
                "real CLI did not encounter the injected filesystem failure")
        require(not zsh.is_symlink() and zsh.read_text() == "original before fault\n", "fault rollback lost shell")
        require(not nvim.is_symlink() and (nvim / "user.lua").read_text() == "editor before fault\n",
                "fault rollback lost editor directory")
        records = json.loads(cli(home, "status").stdout)["transactions"]
        require(len(records) == 1 and records[0]["status"] == "rolled_back", "fault rollback journal differs")
        retry = json.loads(cli(home, "apply", "--components", "zsh,nvim").stdout)
        require(retry["changed"] > 0, "apply cannot resume after rollback")
        cli(home, "restore", retry["transaction"])
        require(zsh.read_text() == "original before fault\n", "retry round trip lost original")
    return "Real CLI filesystem fault after the first link rolls back both original configurations; a fresh apply/restore then succeeds."


def main():
    scenarios = {
        "backup_restore_and_idempotence": round_trip(),
        "changed_target_protection": protect_user_edits(),
        "interrupted_transaction": protect_user_edits(interrupted=True),
        "injected_filesystem_failure": injected_failure(),
    }
    finish("recovery", "Recovery passed: four isolated real-CLI transaction scenarios.",
           scenarios=scenarios, isolation="Disposable HOME; no installed applications or live configuration changed.",
           limitations=["Interrupted process represented by its persisted installing journal state; no physical power-loss test."])


if __name__ == "__main__":
    main()
