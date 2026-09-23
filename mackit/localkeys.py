"""Shortcuts declared outside MacKit's own components, read at query time.

- Apps register their keys in ~/.config/mackit/keys.d/<app>.json: a JSON list of
  {"component","mode","key","description"} rows. mode "global" means system-wide,
  "app:<Name>" means only inside that app.
- Keyboard Maestro: active hot-key macros, read-only from its macros file.

Nothing here is written back to data/keys.json, so personal apps never reach the
published handbook.
"""
from __future__ import annotations
import json, os, plistlib
from pathlib import Path

MODS = {"cmd": "cmd", "command": "cmd", "⌘": "cmd", "ctrl": "ctrl", "control": "ctrl", "⌃": "ctrl",
        "alt": "alt", "opt": "alt", "option": "alt", "⌥": "alt", "shift": "shift", "⇧": "shift",
        "right-cmd": "right-cmd", "left-cmd": "cmd", "hyper": "hyper"}
# Carbon key codes (US layout) for the keys hot keys usually use.
KEYCODES = {0:"a",11:"b",8:"c",2:"d",14:"e",3:"f",5:"g",4:"h",34:"i",38:"j",40:"k",37:"l",46:"m",45:"n",31:"o",
            35:"p",12:"q",15:"r",1:"s",17:"t",32:"u",9:"v",13:"w",7:"x",16:"y",6:"z",18:"1",19:"2",20:"3",21:"4",
            23:"5",22:"6",26:"7",28:"8",25:"9",29:"0",41:";",39:"'",43:",",47:".",44:"/",42:"\\",33:"[",30:"]",
            27:"-",24:"=",50:"`",48:"tab",49:"space",36:"return",51:"delete",53:"escape",123:"left",124:"right",
            125:"down",126:"up",122:"f1",120:"f2",99:"f3",118:"f4",96:"f5",97:"f6",98:"f7",100:"f8",101:"f9",109:"f10"}


def config_dir(home: Path) -> Path:
    base = os.environ.get("XDG_CONFIG_HOME")
    return (Path(base) if base else home / ".config") / "mackit"


def app_rows(home: Path) -> tuple[list[dict], list[str]]:
    rows, issues = [], []
    for path in sorted((config_dir(home) / "keys.d").glob("*.json")):
        try:
            data = json.loads(path.read_text())
            if not isinstance(data, list):
                raise ValueError("expected a JSON list")
        except (OSError, ValueError) as error:
            issues.append(f"unreadable key manifest {path}: {error}")
            continue
        for row in data:
            if not isinstance(row, dict) or not all(isinstance(row.get(k), str) for k in ("component", "key", "description")):
                issues.append(f"invalid row in {path}: {row!r}")
                continue
            rows.append({"mode": "global", "source": str(path), **row, "origin": "keys.d"})
    return rows, issues


def keyboard_maestro_rows(home: Path) -> list[dict]:
    path = home / "Library/Application Support/Keyboard Maestro/Keyboard Maestro Macros.plist"
    try:
        data = plistlib.loads(path.read_bytes())
    except (OSError, plistlib.InvalidFileException, ValueError):
        return []
    rows = []
    for group in data.get("MacroGroups", []):
        if group.get("IsActive", True) is False:
            continue
        targeting = group.get("Targeting") or {}
        apps = [a.get("Name") for a in targeting.get("TargetingApps", []) if isinstance(a, dict) and a.get("Name")]
        scope = "global" if targeting.get("Targeting", "All") == "All" or not apps else "app:" + ",".join(apps)
        for macro in group.get("Macros", []):
            if macro.get("IsActive", True) is False:
                continue
            for trigger in macro.get("Triggers", []):
                if trigger.get("MacroTriggerType") != "HotKey" or trigger.get("KeyCode") not in KEYCODES:
                    continue
                m = int(trigger.get("Modifiers", 0))
                mods = [name for bit, name in ((256, "cmd"), (4096, "ctrl"), (2048, "alt"), (512, "shift")) if m & bit]
                rows.append({"component": "keyboard-maestro", "mode": scope, "key": "+".join(mods + [KEYCODES[trigger["KeyCode"]]]),
                             "description": macro.get("Name") or "(unnamed macro)",
                             "source": f"Keyboard Maestro › {group.get('Name', '?')}", "origin": "keyboard-maestro"})
    return rows


def local_rows(home: Path) -> tuple[list[dict], list[str]]:
    rows, issues = app_rows(home)
    return rows + keyboard_maestro_rows(home), issues


def normalize(key: str) -> str | None:
    """'cmd+ctrl+shift+h' and '⇧⌘⌃H' style strings → a canonical form; None if not a combo."""
    parts = [p for p in key.lower().replace(" ", "+").split("+") if p]
    if not parts:
        return None
    *mods, last = parts
    try:
        canon = sorted({MODS[m] for m in mods})
    except KeyError:
        return None
    if "right-cmd" in canon:
        canon.remove("right-cmd")
        canon = ["right-cmd"] + [m for m in canon if m != "cmd"]
    return "+".join(canon + [last])


def rcmd_disabled(home: Path) -> bool:
    try:
        overrides = json.loads((config_dir(home) / "hotkey_overrides.json").read_text())
    except (OSError, ValueError):
        return False
    return (overrides.get("features") or {}).get("rcmd") is False


def conflicts(rows: list[dict], home: Path) -> list[str]:
    """Two tools on one system-wide key, or an app key that a global key intercepts first."""
    skip_rcmd = rcmd_disabled(home)
    glob, local = {}, []
    for row in rows:
        mode = row.get("mode", "")
        if row["component"] == "hammerspoon" and skip_rcmd and row["key"].startswith("right-cmd+"):
            continue
        key = normalize(row["key"])
        if key is None:
            continue
        if mode == "global":
            glob.setdefault(key, []).append(row)
        elif mode.startswith("app:"):
            local.append((key, row))
    issues = []
    for key, owners in glob.items():
        components = sorted({r["component"] for r in owners})
        if len(components) > 1:
            issues.append("global key claimed twice: " + key + " — " +
                          " / ".join(f'{r["component"]} ({r["description"]})' for r in owners))
    for key, row in local:
        for owner in glob.get(key, []):
            issues.append(f'{row["mode"][4:]} key {key} ({row["description"]}) is intercepted first by '
                          f'{owner["component"]} ({owner["description"]})')
    return issues
