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
        "right-cmd": "right-cmd", "left-cmd": "cmd"}
# Carbon key codes (US layout) for the keys hot keys usually use.
KEYCODES = {0:"a",11:"b",8:"c",2:"d",14:"e",3:"f",5:"g",4:"h",34:"i",38:"j",40:"k",37:"l",46:"m",45:"n",31:"o",
            35:"p",12:"q",15:"r",1:"s",17:"t",32:"u",9:"v",13:"w",7:"x",16:"y",6:"z",18:"1",19:"2",20:"3",21:"4",
            23:"5",22:"6",26:"7",28:"8",25:"9",29:"0",41:";",39:"'",43:",",47:".",44:"/",42:"\\",33:"[",30:"]",
            27:"-",24:"=",50:"`",48:"tab",49:"space",36:"return",51:"delete",53:"escape",123:"left",124:"right",
            125:"down",126:"up",122:"f1",120:"f2",99:"f3",118:"f4",96:"f5",97:"f6",98:"f7",100:"f8",101:"f9",109:"f10"}


def config_dir(home: Path) -> Path:
    """XDG_CONFIG_HOME applies to the real HOME only; an explicit other --home stays isolated."""
    base = os.environ.get("XDG_CONFIG_HOME")
    real = home.expanduser().resolve() == Path.home().resolve()
    return (Path(base) if base and real else home / ".config") / "mackit"


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
            if not isinstance(row, dict) or not all(isinstance(row.get(k), str) for k in ("component", "key", "description")) \
                    or not isinstance(row.get("mode", "global"), str):
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


# Right Option acts as Hyper (⇧⌘⌃) through Hammerspoon (components/hammerspoon/modules/keymap.lua).
HYPER = {"cmd", "ctrl", "shift"}
ORDER = ["right-cmd", "cmd", "ctrl", "alt", "shift"]
# Hammerspoon skips its Ctrl+HJKL keys in these apps (modules/keymap.lua terminal_apps).
TERMINALS = {"terminal", "iterm", "iterm2", "ghostty", "alacritty", "kitty", "warp"}


def normalize(key: str) -> str | None:
    """The one canonical form every check uses (doctor, keys --conflicts-with, the 窗口 page's hint).

    'shift+ctrl+cmd+H', '⇧⌘⌃H', skhd 'ctrl + shift - h' and 'hyper+h' → 'cmd+ctrl+shift+h'.
    Modifiers sort as right-cmd, cmd, ctrl, alt, shift (the order the App's key recorder emits);
    right-cmd stays distinct from cmd; a bare key stays itself; None when a modifier is unknown.
    """
    text = key.lower()
    for symbol in "⌘⌃⌥⇧":
        text = text.replace(symbol, symbol + "+")
    head, sep, tail = text.rpartition(" - ")  # skhd: modifiers before the last " - "
    if sep:
        text = head + "+" + tail
    parts = [p for p in text.replace(" ", "+").split("+") if p]
    if not parts:
        return None
    *mods, last = parts
    canon = set()
    for mod in mods:
        if mod == "hyper":
            canon |= HYPER
        elif mod in MODS:
            canon.add(MODS[mod])
        else:
            return None
    if "right-cmd" in canon:
        canon.discard("cmd")
    return "+".join([m for m in ORDER if m in canon] + [last])


def combo(key: str) -> str | None:
    """normalize() for a key with at least one modifier; None otherwise (not a usable hot key)."""
    canon = normalize(key)
    return canon if canon and "+" in canon else None


def scope(row: dict) -> str | None:
    """'global' for keys held system-wide ('outside-terminals' too: every app except terminals),
    'app' for keys inside one app, None for keys that never compete (editor modes, import-only tables)."""
    # Right-⌘ app switching moved to Initials (2026-09-27); Hammerspoon's keymaps.lua
    # right_command table is only an import source for Initials, never a live claim.
    if row.get("component") == "hammerspoon" and str(row.get("key", "")).startswith("right-cmd+"):
        return None
    mode = row.get("mode", "")
    if mode in ("global", "outside-terminals"):
        return "global"
    return "app" if mode.startswith("app:") else None


def clash_key(row: dict) -> str | None:
    """The canonical key a new skhd hotkey must not reuse, or None when the row cannot clash.
    The App's 窗口 page compares recorded keys with this value from the engine's snapshot."""
    if row.get("component") == "yabai" or scope(row) != "global":
        return None
    return combo(str(row.get("key", "")))


def conflicts(rows: list[dict], home: Path) -> list[str]:
    """Two tools on one system-wide key, or an app key that a global key intercepts first."""
    glob, local = {}, []
    for row in rows:
        kind, key = scope(row), normalize(row["key"])
        if kind is None or key is None:
            continue
        if kind == "global":
            glob.setdefault(key, []).append(row)
        else:
            local.append((key, row))
    issues = []
    for key, owners in glob.items():
        components = sorted({r["component"] for r in owners})
        if len(components) > 1:
            issues.append("global key claimed twice: " + key + " — " +
                          " / ".join(f'{r["component"]} ({r["description"]})' for r in owners))
    for key, row in local:
        apps = row["mode"][4:]
        for owner in glob.get(key, []):
            if owner["mode"] == "outside-terminals" and all(a.strip().lower() in TERMINALS for a in apps.split(",")):
                continue
            issues.append(f'{apps} key {key} ({row["description"]}) is intercepted first by '
                          f'{owner["component"]} ({owner["description"]})')
    return issues


def clashes(key: str, rows: list[dict], profile: str) -> list[dict]:
    """Global keys another tool already holds for a candidate hotkey (the 窗口 page's warning)."""
    target = combo(key)
    if not target:
        return []
    return [row for row in rows if row.get("profile") in (None, profile) and clash_key(row) == target]
