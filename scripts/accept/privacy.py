#!/usr/bin/env python3
"""Check local privacy and write boundaries without accessing real user data."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

from _common import ROOT, cli, finish, isolated_home


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def gui(home, account_home, command_dir, command_log, action, ok=True, **values):
    env = os.environ.copy()
    env.update(HOME=str(account_home), XDG_CONFIG_HOME=str(home / ".config"),
               XDG_STATE_HOME=str(home / ".local/state"),
               XDG_CACHE_HOME=str(home / ".cache"), PATH=str(command_dir),
               MACKIT_ACCEPT_COMMAND_LOG=str(command_log), PYTHONDONTWRITEBYTECODE="1")
    result = subprocess.run(
        [sys.executable, str(ROOT / "bin/mackit"), "--home", str(home), "gui"],
        input=json.dumps({"action": action, **values}), cwd=ROOT, env=env,
        text=True, capture_output=True, timeout=60,
    )
    assert result.returncode == 0, f"GUI bridge process failed: {action}"
    response = json.loads(result.stdout)
    assert response.get("ok") is ok, f"Unexpected GUI acceptance result: {action}"
    return response


def main():
    # Only the existing public catalog and configuration files are read here.
    protected = [ROOT / "data/keys.json", ROOT / "components/nvim/lua/config/keymaps.lua",
                 ROOT / "components/yabai/config/settings.json",
                 ROOT / "components/yabai/config/skhd/hotkeys.json",
                 ROOT / "components/yabai/config/yabairc",
                 ROOT / "components/yabai/config/skhd/skhdrc"]
    before = {path: digest(path) for path in protected}
    with isolated_home() as temporary:
        sandbox = Path(temporary)
        home, account = sandbox / "demo-home", sandbox / "account-home"
        home.mkdir()
        account.mkdir()
        secret = "synthetic-private-" + uuid.uuid4().hex
        for relative in (".personal_env", ".ssh/id_ed25519", "Documents/private-note.txt"):
            path = home / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(secret)
        command_dir = sandbox / "commands"
        command_dir.mkdir()
        command_log = sandbox / "unexpected-command"
        # Inert tripwires keep this acceptor harmless even if the product guard
        # regresses. No real package manager or window service is on this PATH.
        for name in ("brew", "yabai", "skhd"):
            path = command_dir / name
            path.write_text('#!/bin/sh\nprintf "%s\\n" "$0" >> "$MACKIT_ACCEPT_COMMAND_LOG"\nexit 99\n')
            path.chmod(0o700)

        def call(action, ok=True, **values):
            response = gui(home, account, command_dir, command_log, action, ok=ok, **values)
            assert secret not in json.dumps(response), "Unrelated private content appeared in GUI response"
            return response

        for args in (("keys", "--json"), ("status",),
                     ("plan", "--components", "nvim", "--json")):
            result = cli(home, *args)
            assert secret not in result.stdout + result.stderr, "Unrelated private content appeared in CLI response"
            json.loads(result.stdout)
        snapshot = call("snapshot")
        assert snapshot["keys"] and not snapshot["installed"]
        call("preview", components=["nvim"])
        source = home / ".local/share/mackit"
        assert source.is_dir() and source.resolve().is_relative_to(home)
        assert not (source / ".personal_env").exists()
        assert not (source / ".ssh").exists()
        assert secret not in (source / "data/keys.json").read_text()

        for forbidden in ("../../.personal_env", str(home / ".ssh/id_ed25519"), "../nvim-keys"):
            call("readFile", ok=False, file=forbidden)
            call("saveFile", ok=False, file=forbidden, content="replacement", digest="absent")
        external = sandbox / "outside-config.txt"
        external.write_text(secret)
        linked = source / "components/nvim/lua/config/keymaps.lua"
        assert linked.resolve().is_relative_to(source)
        linked.unlink()
        linked.symlink_to(external)
        call("readFile", ok=False, file="nvim-keys")
        call("saveFile", ok=False, file="nvim-keys", content="replacement", digest=digest(external))
        assert external.read_text() == secret and linked.is_symlink()
        local_link = home / ".config/mackit/local.zsh"
        local_link.parent.mkdir(parents=True, exist_ok=True)
        local_link.symlink_to(external)
        call("readFile", ok=False, file="local")
        call("saveFile", ok=False, file="local", content="replacement", digest=digest(external))
        assert external.read_text() == secret

        dependency_result = call("installDependencies", ok=False, components=["nvim"])
        assert "演示目录" in dependency_result["error"]
        for service in ("yabai", "skhd"):
            for start in (True, False):
                response = call("windowService", ok=False, service=service, start=start)
                assert "演示目录" in response["error"]
        settings = json.loads((source / "components/yabai/config/settings.json").read_text())
        window_data = {"settings": settings.get("settings", {}), "rules": settings.get("rules", []),
                       "hotkeys": json.loads((source / "components/yabai/config/skhd/hotkeys.json").read_text())}
        window_digest = hashlib.sha256(json.dumps(window_data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        call("windowSave", **window_data, digest=window_digest, applyNow=True)
        assert not command_log.exists(), "Demo mode invoked a package manager or window service"
        assert all((home / relative).read_text() == secret for relative in
                   (".personal_env", ".ssh/id_ed25519", "Documents/private-note.txt"))
    assert {path: digest(path) for path in protected} == before, "Public source was modified"
    finish(
        "privacy",
        "PASS: synthetic private data stays out of local responses; file allowlists, symlink guards and demo service boundaries hold",
        scenarios=["unrelated synthetic secrets excluded from keys/status/plan/snapshot",
                   "prepared GUI source excludes home secrets", "read/write path traversal rejected",
                   "component and local-override external symlinks rejected",
                   "demo dependency installation and window service start/stop rejected",
                   "demo window save does not apply live", "shared public configuration remains unchanged"],
        limitations=["Checks local product flows with synthetic fixtures, not network traffic capture.",
                     "Package manager and window commands are inert tripwires; no real service is invoked.",
                     "Intentionally registered local shortcut metadata remains visible locally by product design."],
    )


if __name__ == "__main__":
    main()
