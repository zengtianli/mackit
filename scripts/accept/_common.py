"""Shared helpers for isolated, noninteractive MacKit product acceptance."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path(os.environ.get("SOP_OUT_DIR", ROOT / "perf/acceptance"))


def isolated_home():
    # macOS aliases /var to /private/var. Keep containment checks on one spelling.
    return tempfile.TemporaryDirectory(prefix="mackit-accept-", dir=Path(tempfile.gettempdir()).resolve())


def cli(home, *args, ok=True):
    home = Path(home)
    env = os.environ.copy()
    env.update(HOME=str(home), XDG_CONFIG_HOME=str(home / ".config"),
               XDG_STATE_HOME=str(home / ".local/state"),
               XDG_CACHE_HOME=str(home / ".cache"),
               PYTHONDONTWRITEBYTECODE="1")
    result = subprocess.run([sys.executable, str(ROOT / "bin/mackit"),
                             "--home", str(home), *args], cwd=ROOT,
                            env=env, text=True, capture_output=True, timeout=60)
    if ok and result.returncode:
        raise AssertionError(f"CLI {args} exited {result.returncode}: "
                             + result.stderr.replace(str(home), "<isolated-home>")
                             .replace(str(ROOT), "<repo>"))
    return result


def finish(name, summary, **details):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    value = {"summary": summary, **details}
    (OUT_DIR / f"{name}.detail.json").write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    print(summary)
