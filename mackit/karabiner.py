"""Karabiner rules in components/karabiner/karabiner.json, and the nudge that makes a running Karabiner re-read.

Rule edits are saved through the 配置文件 page's own read/save (cli.karabiner_command), so the path guard,
digest check, lock and editor-backups are the same; this module holds only what is specific to Karabiner:
finding and validating rules, and the reload. Karabiner maps keys to keys here: a rule that carries a
shell_command is refused (programs are skhd bindings; tests/test_native.py guards the source file). Stdlib only.
"""
from __future__ import annotations
import json, subprocess, time
from pathlib import Path

LOG = Path("/var/log/karabiner/core_service.log")
MARK = "core_configuration is updated"
INSTALLED = (Path("/Applications/Karabiner-Elements.app"), Path("/Library/Application Support/org.pqrs/Karabiner-Elements"))
PROCESSES = ("Karabiner-Core-Service", "karabiner_console_user_server", "karabiner_grabber")
NUDGE = ".mackit-nudge"
NO_COMMAND = ("Karabiner only maps keys to keys here: this rule carries a shell_command. "
              "Bind a program with mackit window hotkey add --command instead.")


# ── rules ─────────────────────────────────────────────────────────────────
def parse(text: str) -> dict:
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise ValueError("karabiner.json is not valid JSON: " + str(exc)) from None
    if not isinstance(data, dict):
        raise ValueError("karabiner.json must be a JSON object.")
    return data


def render(data: dict) -> str:
    """The layout the source file is kept in (2-space indent, key order as given)."""
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def profile_of(data: dict) -> dict:
    """The profile Karabiner uses: the selected one, else the first."""
    profiles = data.get("profiles")
    if not isinstance(profiles, list) or not profiles or not all(isinstance(p, dict) for p in profiles):
        raise ValueError("karabiner.json has no profiles.")
    return next((p for p in profiles if p.get("selected")), profiles[0])


def rules_of(profile: dict) -> list:
    group = profile.setdefault("complex_modifications", {})
    rules = group.setdefault("rules", []) if isinstance(group, dict) else None
    if not isinstance(rules, list) or not all(isinstance(r, dict) for r in rules):
        raise ValueError("complex_modifications.rules must be a list of objects.")
    return rules


def has_command(value) -> bool:
    """True when a shell_command sits anywhere inside (to, to_if_alone, to_delayed_action, …)."""
    if isinstance(value, dict):
        return "shell_command" in value or any(has_command(v) for v in value.values())
    if isinstance(value, list):
        return any(has_command(v) for v in value)
    return False


def enabled(rule: dict) -> bool:
    return rule.get("enabled", True) is not False


def trigger(manipulator) -> str:
    """The key a manipulator starts from, e.g. command+h or right_option."""
    source = manipulator.get("from") if isinstance(manipulator, dict) else None
    if not isinstance(source, dict):
        return ""
    if isinstance(source.get("simultaneous"), list):
        key = "&".join(str(next(iter(k.values()), "")) for k in source["simultaneous"] if isinstance(k, dict))
    else:
        key = next((str(source[k]) for k in ("key_code", "consumer_key_code", "pointing_button", "any") if k in source), "")
    modifiers = source.get("modifiers")
    held = modifiers.get("mandatory") if isinstance(modifiers, dict) else None
    return "+".join([*(str(m) for m in (held if isinstance(held, list) else [])), key]) if key else ""


def summary(rule: dict, index: int) -> dict:
    manipulators = rule.get("manipulators") if isinstance(rule.get("manipulators"), list) else []
    return {"index": index, "description": str(rule.get("description", "")), "enabled": enabled(rule),
            "manipulators": len(manipulators), "from": [t for t in (trigger(m) for m in manipulators) if t]}


def clean_rule(rule) -> dict:
    """A rule as Karabiner reads it: description plus basic manipulators, and nothing that runs a program."""
    if not isinstance(rule, dict):
        raise ValueError("A rule is one JSON object with description and manipulators.")
    description = rule.get("description")
    if not isinstance(description, str) or not description.strip() or "\n" in description:
        raise ValueError("The rule needs a one-line description; it is how the rule is found again.")
    manipulators = rule.get("manipulators")
    if not isinstance(manipulators, list) or not manipulators or not all(isinstance(m, dict) for m in manipulators):
        raise ValueError("manipulators must be a non-empty list of objects.")
    for m in manipulators:
        if m.get("type") not in ("basic", "mouse_motion_to_scroll"):
            raise ValueError('Each manipulator needs "type": "basic" (or mouse_motion_to_scroll).')
        if m["type"] == "basic" and not isinstance(m.get("from"), dict):
            raise ValueError('A basic manipulator needs a "from" object.')
    if "enabled" in rule and not isinstance(rule["enabled"], bool):
        raise ValueError("enabled must be true or false.")
    if has_command(rule):
        raise ValueError(NO_COMMAND)
    return {**rule, "description": description.strip()}


def find(rules: list, index=None, description=None) -> int:
    """Position of one rule, by its 1-based number in the list or by its exact description."""
    if index is not None:
        if not 1 <= index <= len(rules):
            raise ValueError(f"No rule {index}; the file has {len(rules)}.")
        return index - 1
    hits = [i for i, r in enumerate(rules) if r.get("description") == description]
    if not hits:
        raise ValueError("No rule described as: " + str(description))
    if len(hits) > 1:
        raise ValueError(f"{len(hits)} rules share that description; use --index ({', '.join(str(i + 1) for i in hits)}).")
    return hits[0]


def add(rules: list, rule, at=None, replace=False) -> tuple[int, bool]:
    """Insert a validated rule (append, or before 1-based position `at`); returns (position, replaced)."""
    item = clean_rule(rule)
    same = [i for i, r in enumerate(rules) if r.get("description") == item["description"]]
    if same and not replace:
        raise ValueError(f"A rule with this description exists (rule {same[0] + 1}); pass --replace to change it.")
    if len(same) > 1:
        raise ValueError(f"{len(same)} rules share that description; remove them by --index first.")
    if same:
        rules[same[0]] = item
        return same[0], True
    if at is None:
        rules.append(item)
        return len(rules) - 1, False
    if not 1 <= at <= len(rules) + 1:
        raise ValueError(f"--at must be 1–{len(rules) + 1}.")
    rules.insert(at - 1, item)
    return at - 1, False


def set_enabled(rules: list, position: int, on: bool) -> bool:
    """Karabiner's own spelling: a disabled rule carries "enabled": false, an enabled one has no such key."""
    rule = rules[position]
    if enabled(rule) == on:
        return False
    if on:
        if has_command(rule):
            raise ValueError(NO_COMMAND)
        rules[position] = {k: v for k, v in rule.items() if k != "enabled"}
    else:
        changed = {**rule, "enabled": False}
        rules[position] = dict(sorted(changed.items())) if list(rule) == sorted(rule) else changed
    return True


# ── running Karabiner ─────────────────────────────────────────────────────
def installed() -> bool:
    return any(p.exists() for p in INSTALLED)


def running() -> bool:
    try:
        out = subprocess.run(["/bin/ps", "-axo", "comm="], capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    return any(Path(line.strip()).name in PROCESSES for line in out.splitlines())


def marks(log: Path, offset: int = 0):
    """Log lines saying the configuration was re-read, written after byte `offset`; None when unreadable.
    A log shorter than the offset was rotated and is read from its start."""
    try:
        with log.open("rb") as handle:
            handle.seek(offset if log.stat().st_size >= offset else 0)
            text = handle.read().decode("utf-8", "replace")
    except OSError:
        return None
    return [line.strip() for line in text.splitlines() if MARK in line]


def last_reload(log: Path = LOG) -> str:
    """The newest such line in the current log file ("" when none or unreadable). Read-only."""
    try:
        start = max(0, log.stat().st_size - 256 * 1024)
    except OSError:
        return ""
    found = marks(log, start)
    return found[-1] if found else ""


def reload(state: Path, skip: str = "", log: Path = LOG, wait: float = 5.0, recent: int = 4,
           is_installed=installed, is_running=running, sleep=time.sleep, clock=time.monotonic) -> dict:
    """Make a running Karabiner read the configuration again, then look for its own confirmation.

    Karabiner keeps watching the directory it last loaded from while apply only re-points
    ~/.config/karabiner. Renaming a watched directory and renaming it back makes it load again, through
    the link, so the newest file. Which generation it watches is not always the previous one, so the
    `recent` newest generations are nudged (not `skip`, the one apply just created). One bounded wait
    of `wait` seconds for a new log line; no retry. The caller keeps this away from an isolated --home."""
    result = {"attempted": False, "reloaded": False, "reason": "", "nudged": [], "waited_ms": 0, "log": str(log), "line": ""}
    if not is_installed():
        return {**result, "reason": "not_installed"}
    if not is_running():
        return {**result, "reason": "not_running"}
    generations = state / "generations"
    for stray in generations.glob("*/karabiner" + NUDGE):  # an interrupted nudge: put the directory back
        if not (stray.parent / "karabiner").exists():
            stray.rename(stray.parent / "karabiner")
    found = sorted((d for d in generations.glob("*/karabiner") if d.is_dir() and not d.is_symlink() and d.parent.name != skip), reverse=True)
    if not found:
        return {**result, "reason": "no_generation"}
    try:
        offset = log.stat().st_size
    except OSError:
        offset = None
    for directory in found[:recent]:
        moved = directory.with_name(directory.name + NUDGE)
        directory.rename(moved)
        moved.rename(directory)
        result["nudged"].append(directory.parent.name)
    result["attempted"] = True
    if offset is None:
        return {**result, "reason": "log_unreadable"}
    start = clock()
    while True:
        lines = marks(log, offset)
        if lines:
            result.update(reloaded=True, line=lines[-1])
            break
        if clock() - start >= wait:
            result["reason"] = "not_confirmed"
            break
        sleep(0.1)
    result["waited_ms"] = int((clock() - start) * 1000)
    return result
