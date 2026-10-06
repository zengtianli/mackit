"""Native current-App menu search. GUI and CLI use the same signed MacKit implementation."""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import sys


def binary(payload: Path) -> Path:
    candidates = []
    if getattr(sys, "frozen", False):
        for parent in Path(sys.executable).resolve().parents:
            if parent.suffix == ".app":
                candidates.append(parent / "Contents/MacOS/MacKit")
                break
    else:
        candidates.append(payload / "build/native/MacKit")
    candidates.append(Path("/Applications/MacKit.app/Contents/MacOS/MacKit"))
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    raise ValueError("菜单搜索需要原生 MacKit：先运行 scripts/build-app.sh --local 或安装 MacKit.app。")


def command(args, home: Path, payload: Path) -> dict:
    from . import cli
    verb = args.menu_command
    # Even a read-only scan of another application would escape an isolated --home.
    if cli.isolated(home):
        raise ValueError("菜单搜索读取或操作本机 App；不能在隔离 --home 中执行。")
    native = binary(payload)
    if verb == "show":
        process = subprocess.Popen([str(native), "--menu-search"], stdin=subprocess.DEVNULL,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        return {"ok": True, "pid": process.pid, "launched": True, "native": str(native)}
    parameters = [str(native), {"status": "--menu-status", "scan": "--menu-scan", "execute": "--menu-execute"}[verb]]
    if getattr(args, "pid", None) is not None:
        parameters += ["--pid", str(args.pid)]
    if verb == "execute":
        try:
            path = json.loads(args.path_json)
        except (ValueError, TypeError):
            raise ValueError("--path-json 需要 JSON 菜单路径数组。") from None
        if not isinstance(path, list) or not path or not all(isinstance(s, str) and s for s in path):
            raise ValueError("--path-json 需要非空的菜单名称数组。")
        parameters += ["--path-json", json.dumps(path, ensure_ascii=False)]
    result = subprocess.run(parameters, capture_output=True, text=True, timeout=12)
    try:
        data = json.loads(result.stdout)
    except ValueError:
        raise ValueError("原生菜单工具未返回 JSON：" + result.stderr.strip()[:300]) from None
    if result.returncode or not data.get("ok"):
        raise ValueError(data.get("error") or "菜单读取不完整：" + " ".join(data.get("warnings", [])))
    return data
