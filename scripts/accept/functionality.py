#!/usr/bin/env python3
"""Exercise shipped CLI and GUI bridge with disposable configuration homes."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from _common import ROOT, cli, finish, isolated_home


def gui(home, action, **values):
    env = os.environ.copy()
    env.update(HOME=str(home), XDG_CONFIG_HOME=str(home / ".config"),
               XDG_STATE_HOME=str(home / ".local/state"),
               XDG_CACHE_HOME=str(home / ".cache"),
               PYTHONDONTWRITEBYTECODE="1")
    result = subprocess.run(
        [sys.executable, str(ROOT / "bin/mackit"), "--home", str(home), "gui"],
        input=json.dumps({"action": action, **values}), cwd=ROOT, env=env,
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, f"GUI bridge {action} failed"
    value = json.loads(result.stdout)
    assert value.get("ok"), f"GUI bridge {action} returned an error"
    return value


def main():
    version = (ROOT / "VERSION").read_text().strip()
    with isolated_home() as temporary:
        home = Path(temporary)
        assert cli(home, "--version").stdout.strip() == version
        initial = json.loads(cli(home, "status").stdout)
        assert initial["installed"] == {} and initial["transactions"] == []
        for profile in ("developer", "tianli"):
            planned = json.loads(cli(home, "plan", "--profile", profile, "--json").stdout)
            expected = json.loads((ROOT / "profiles" / f"{profile}.json").read_text())
            assert planned["profile"] == profile
            assert planned["components"] == expected["components"]
            assert planned["entries"]
            assert all(Path(row["target"]).is_relative_to(home) for row in planned["entries"])
        assert not (home / ".config").exists(), "Preview unexpectedly installed configuration"
        original = "# isolated user's existing shell configuration\n"
        (home / ".zshrc").write_text(original)
        components = "zsh,nvim,ghostty,karabiner"
        plan = json.loads(cli(home, "plan", "--components", components, "--json").stdout)
        assert next(row for row in plan["entries"] if row["component"] == "zsh")["action"] == "backup + install"
        assert (home / ".zshrc").read_text() == original
        applied = json.loads(cli(home, "apply", "--components", components).stdout)
        assert applied["changed"] == 7
        assert (home / ".zshrc").is_symlink()
        assert (home / ".config/nvim").resolve() == ROOT / "components/nvim"
        assert "config-file = " in (home / ".config/ghostty/config").read_text()
        assert json.loads((home / ".config/karabiner/karabiner.json").read_text())["profiles"]
        current = json.loads(cli(home, "status").stdout)
        assert current["installed"]["components"] == components.split(",")
        transaction = next(row for row in current["transactions"] if row["id"] == applied["transaction"])
        assert transaction["status"] == "applied"
        shell_operation = next(row for row in transaction["operations"] if row["target"] == str(home / ".zshrc"))
        assert Path(shell_operation["backup"]).read_text() == original
        after = json.loads(cli(home, "plan", "--json").stdout)
        assert all(row["action"] == "unchanged" for row in after["entries"])
        assert json.loads(cli(home, "apply").stdout)["changed"] == 0
        diagnosed = cli(home, "doctor", ok=False)
        diagnosis = json.loads(diagnosed.stdout)
        assert diagnosis["profile"] == "developer"
        # Dependency availability belongs to the machine, while this checks all
        # installed configuration and declaration checks actually succeed.
        assert all(issue.startswith(("missing command:", "missing app:")) for issue in diagnosis["issues"]), diagnosis["issues"]
        assert diagnosed.returncode == int(bool(diagnosis["issues"]))
        keys = json.loads(cli(home, "keys", "编号", "--component", "nvim", "--json").stdout)
        assert keys and all(row["component"] == "nvim" for row in keys)
        assert any("keymaps.lua" in row["source"] for row in keys)
        assert Path(cli(home, "edit", "nvim-keys", "--print").stdout.strip()) == ROOT / "components/nvim/lua/config/keymaps.lua"
        external_dependencies_missing = len(diagnosis["issues"])

    source_file = ROOT / "components/nvim/lua/config/keymaps.lua"
    source_digest = hashlib.sha256(source_file.read_bytes()).hexdigest()
    with isolated_home() as temporary:
        home = Path(temporary)
        (home / ".zshrc").write_text("# original GUI fixture\n")
        snapshot = gui(home, "snapshot")
        assert not snapshot["installed"] and len(snapshot["keys"]) > 500
        selection = {"profile": "developer", "components": ["zsh", "nvim"]}
        preview = gui(home, "preview", **selection)
        assert not (home / ".zshrc").is_symlink()
        assert len(preview["token"]) == 64 and len(preview["plan"]["entries"]) == 2
        installed = gui(home, "apply", token=preview["token"], **selection)
        snapshot = gui(home, "snapshot")
        source = home / ".local/share/mackit"
        assert snapshot["installed"] and Path(snapshot["sourceRoot"]) == source
        assert (home / ".config/nvim").resolve().is_relative_to(source)
        document = gui(home, "readFile", file="nvim-keys")
        assert Path(document["path"]).resolve().is_relative_to(source)
        edited = document["content"] + "\n-- isolated acceptance edit\n"
        saved = gui(home, "saveFile", file="nvim-keys", content=edited, digest=document["digest"])
        assert Path(saved["backup"]).read_text() == document["content"]
        assert gui(home, "readFile", file="nvim-keys")["content"] == edited
        gui(home, "restore", transaction=installed["installation"]["transaction"])
        assert (home / ".zshrc").read_text() == "# original GUI fixture\n"
        assert not gui(home, "snapshot")["installed"]
    assert hashlib.sha256(source_file.read_bytes()).hexdigest() == source_digest
    finish(
        "functionality",
        "PASS: real CLI planning/apply/status/doctor/key lookup and GUI preview/apply/edit/read/restore in isolated homes",
        version=version,
        scenarios=["both profile plans without installation", "CLI apply with original backup",
                   "installed state and generated configuration", "idempotent reapply",
                   "doctor checks installed sources and declarations", "key search and edit-source lookup",
                   "GUI prepared-source preview and token-bound apply", "GUI save/read with editor backup",
                   "GUI explicit transaction restore"],
        external_dependencies_missing=external_dependencies_missing,
        limitations=["Does not install dependencies, launch configured applications, or exercise physical hotkeys.",
                     "Temporary homes only; no real user configuration or services are changed."],
    )


if __name__ == "__main__":
    main()
