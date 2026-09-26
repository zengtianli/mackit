"""Window manager settings (yabai + skhd) behind the native app's 窗口 page.

One JSON source per tool lives next to the generated file it replaces:
  components/yabai/config/settings.json  -> yabairc   (config values + app rules)
  components/yabai/config/skhd/hotkeys.json -> skhdrc (bindings)
The app edits the JSON only; rendering, validation, live apply and service control
stay here so a hand edit and a GUI edit produce the same files. Stdlib only.
"""
from __future__ import annotations
import json, re, shutil, subprocess, time, uuid
from pathlib import Path

try:
    from mackit.localkeys import KEYCODES, normalize
except ImportError:  # run from the repo
    from localkeys import KEYCODES, normalize

# (key, kind, choices-or-range, label, help). Only keys yabai documents; values validated here.
SETTINGS = [
    ("layout", "choice", ["float", "bsp", "stack"], "布局", "float 不接管窗口，只在按快捷键时摆放；bsp 自动平铺；stack 叠放。"),
    ("auto_balance", "choice", ["off", "on"], "自动均分", "平铺时新开窗口后把同层窗口均分。仅 bsp 有效。"),
    ("split_ratio", "float", [0.1, 0.9], "分割比例", "平铺时新窗口占的比例，0.5 为一半。"),
    ("window_placement", "choice", ["second_child", "first_child"], "新窗口位置", "平铺时新窗口放在右/下（second_child）或左/上（first_child）。"),
    ("window_gap", "int", [0, 60], "窗口间隙", "平铺窗口之间的像素间隔。"),
    ("top_padding", "int", [0, 200], "上边距", "平铺区域离屏幕上边的像素。"),
    ("bottom_padding", "int", [0, 200], "下边距", "平铺区域离屏幕下边的像素。"),
    ("left_padding", "int", [0, 200], "左边距", "平铺区域离屏幕左边的像素。"),
    ("right_padding", "int", [0, 200], "右边距", "平铺区域离屏幕右边的像素。"),
    ("mouse_modifier", "choice", ["alt", "cmd", "ctrl", "shift", "fn"], "鼠标修饰键", "按住它再拖动窗口任意位置即可移动或缩放。"),
    ("mouse_action1", "choice", ["move", "resize"], "修饰键 + 左键", "按住修饰键用左键拖动时的动作。"),
    ("mouse_action2", "choice", ["resize", "move"], "修饰键 + 右键", "按住修饰键用右键拖动时的动作。"),
    ("mouse_drop_action", "choice", ["swap", "stack"], "拖到另一窗口上", "平铺时把窗口拖到另一窗口上：交换位置或叠放。"),
    ("focus_follows_mouse", "choice", ["off", "autofocus", "autoraise"], "焦点跟随鼠标", "鼠标移到哪个窗口就聚焦它；autoraise 还会置前。"),
    ("mouse_follows_focus", "choice", ["off", "on"], "鼠标跟随焦点", "切换窗口焦点时把鼠标移到该窗口中央。"),
    ("window_shadow", "choice", ["on", "off", "float"], "窗口阴影", "off 去掉全部阴影，float 只保留浮动窗口的阴影。需要脚本附加组件。"),
    ("window_opacity", "choice", ["off", "on"], "透明度区分", "打开后非活动窗口按下方透明度显示。需要脚本附加组件。"),
    ("active_window_opacity", "float", [0.1, 1.0], "活动窗口透明度", "1.0 为不透明。"),
    ("normal_window_opacity", "float", [0.1, 1.0], "其他窗口透明度", "1.0 为不透明。"),
]
SPEC = {k: (kind, rng) for k, kind, rng, _, _ in SETTINGS}
# yabai prints these spellings for values it was given differently.
READBACK = {"disabled": "off"}
RULE_KEYS = {"manage": ["off", "on"], "sticky": ["on", "off"]}

SCRIPTS = "$HOME/.config/yabai/scripts"
ACTIONS = {  # id -> (label, command). Commands are fixed; the app only picks an id.
    **{f"grid-top-{i}": (f"上半屏第 {i} 格", f"{SCRIPTS}/window/position.sh grid top {i}") for i in range(1, 5)},
    **{f"grid-bottom-{i}": (f"下半屏第 {i} 格", f"{SCRIPTS}/window/position.sh grid bottom {i}") for i in range(1, 5)},
    "left": ("左半屏", f"{SCRIPTS}/window/position.sh left"),
    "right": ("右半屏", f"{SCRIPTS}/window/position.sh right"),
    "full": ("全屏", f"{SCRIPTS}/window/position.sh full"),
    "float-toggle": ("当前窗口浮动/平铺切换", "yabai -m window --toggle float"),
    "layout-toggle": ("当前桌面 bsp ↔ float", f"{SCRIPTS}/space/layout_toggle.sh"),
    "mouse-follow": ("鼠标跟随开关", f"{SCRIPTS}/service/mouse_follow.sh"),
    "focus-west": ("聚焦左侧窗口", "yabai -m window --focus west"),
    "focus-east": ("聚焦右侧窗口", "yabai -m window --focus east"),
    "focus-north": ("聚焦上方窗口", "yabai -m window --focus north"),
    "focus-south": ("聚焦下方窗口", "yabai -m window --focus south"),
    "balance": ("均分当前桌面窗口", "yabai -m space --balance"),
}
SKHD_NAMES = {"space": "space", "return": "return", "tab": "tab", "escape": "escape", "delete": "backspace",
              "left": "left", "right": "right", "up": "up", "down": "down",
              **{f"f{i}": f"f{i}" for i in range(1, 11)}}
MOD_ORDER = ["cmd", "ctrl", "alt", "shift"]


def paths(root: Path) -> dict:
    base = root / "components/yabai/config"
    return {"settings": base / "settings.json", "yabairc": base / "yabairc",
            "hotkeys": base / "skhd/hotkeys.json", "skhdrc": base / "skhd/skhdrc"}


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return default


# ── validation ────────────────────────────────────────────────────────────
def clean_settings(values: dict) -> dict:
    out = {}
    for key, value in values.items():
        if key not in SPEC:
            raise ValueError(f"未知设置：{key}")
        kind, rng = SPEC[key]
        if kind == "choice":
            if value not in rng:
                raise ValueError(f"{key} 只能是 {' / '.join(rng)}")
            out[key] = value
        else:
            try:
                num = float(value) if kind == "float" else int(value)
            except (TypeError, ValueError):
                raise ValueError(f"{key} 需要数字") from None
            if not rng[0] <= num <= rng[1]:
                raise ValueError(f"{key} 需在 {rng[0]}–{rng[1]} 之间")
            out[key] = round(num, 2) if kind == "float" else num
    return out


APP_RE = re.compile(r"^[\w .\-+&'()一-鿿]{1,60}$")


def clean_rules(rules: list) -> list:
    out = []
    for rule in rules:
        app = str(rule.get("app", "")).strip()
        if not APP_RE.match(app):
            raise ValueError(f"应用名无效：{app!r}（只用应用显示名，如 System Settings）")
        item = {"app": app}
        for key, allowed in RULE_KEYS.items():
            if rule.get(key) not in (None, ""):
                if rule[key] not in allowed:
                    raise ValueError(f"{app} 的 {key} 只能是 {' / '.join(allowed)}")
                item[key] = rule[key]
        if rule.get("space") not in (None, "", 0):
            space = int(rule["space"])
            if not 1 <= space <= 16:
                raise ValueError(f"{app} 的桌面编号需在 1–16")
            item["space"] = space
        if len(item) == 1:
            raise ValueError(f"{app} 的规则没有任何设置")
        out.append(item)
    return out


def canonical_key(key: str) -> str:
    canon = normalize(key)
    if not canon or canon.count("+") == 0:
        raise ValueError(f"快捷键需要至少一个修饰键：{key}")
    *mods, last = canon.split("+")
    if any(m not in MOD_ORDER for m in mods):
        raise ValueError(f"skhd 不支持该修饰键：{key}")
    if last not in KEYCODES.values():
        raise ValueError(f"不认识的按键：{last}")
    return "+".join([m for m in MOD_ORDER if m in mods] + [last])


def clean_hotkeys(rows: list) -> list:
    out, seen = [], {}
    for row in rows:
        key = canonical_key(str(row.get("key", "")))
        if key in seen:
            raise ValueError(f"{key} 重复绑定（{seen[key]}）")
        action, command = row.get("action", ""), row.get("command", "")
        if action:
            if action not in ACTIONS:
                raise ValueError(f"未知动作：{action}")
            command = ""
        elif not isinstance(command, str) or not command.strip() or "\n" in command:
            raise ValueError(f"{key} 需要选择动作或填写单行命令")
        item = {"key": key, "action": action} if action else {"key": key, "command": command.strip()}
        if row.get("note"):
            item["note"] = str(row["note"])[:80]
        seen[key] = item.get("note") or action or command
        out.append(item)
    return out


# ── rendering ─────────────────────────────────────────────────────────────
def skhd_key(canon: str) -> str:
    *mods, last = canon.split("+")
    code = next(c for c, name in KEYCODES.items() if name == last)
    token = last if re.fullmatch(r"[a-z0-9]", last) else SKHD_NAMES.get(last, f"0x{code:02X}")
    return " + ".join(mods) + " - " + token


def render_skhdrc(rows: list) -> str:
    lines = ["# 由 MacKit 生成：请在 MacKit App「窗口」页或 hotkeys.json 修改，改这里会被覆盖。", ""]
    for row in rows:
        command = ACTIONS[row["action"]][1] if row.get("action") else row["command"]
        label = row.get("note") or (ACTIONS[row["action"]][0] if row.get("action") else "")
        if label:
            lines.append("# " + label)
        lines.append(f"{skhd_key(row['key'])} : {command}")
    return "\n".join(lines) + "\n"


def render_yabairc(data: dict) -> str:
    lines = ["#!/usr/bin/env bash",
             "# 由 MacKit 生成：请在 MacKit App「窗口」页或 settings.json 修改，改这里会被覆盖。",
             "# 脚本附加组件（SA）在 macOS 27 beta 上会打坏菜单栏渲染，默认不加载；阴影/透明度等依赖它的设置届时不生效。",
             ""]
    for key, _, _, label, _ in SETTINGS:
        if key in data.get("settings", {}):
            lines.append(f"yabai -m config {key} {data['settings'][key]}  # {label}")
    rules = data.get("rules", [])
    if rules:
        lines += ["", "# 应用规则"]
        for rule in rules:
            attrs = " ".join(f"{k}={rule[k]}" for k in ("manage", "sticky", "space") if k in rule)
            lines.append(f'yabai -m rule --add label="mackit-{rule["app"]}" app="^{re.escape(rule["app"])}$" {attrs}')
        lines.append("yabai -m rule --apply")
    return "\n".join(lines) + "\n"


# ── IO ────────────────────────────────────────────────────────────────────
def load(root: Path) -> dict:
    p = paths(root)
    data = read_json(p["settings"], {"settings": {}, "rules": []})
    hotkeys = read_json(p["hotkeys"], [])
    return {"settings": data.get("settings", {}), "rules": data.get("rules", []), "hotkeys": hotkeys}


def write_atomic(path: Path, text: str, backups: Path, mode: int = 0o644) -> None:
    if path.exists():
        backups.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backups / path.name)
    tmp = path.with_name("." + path.name + ".mackit-" + uuid.uuid4().hex)
    tmp.write_text(text)
    tmp.chmod(mode)
    tmp.replace(path)


def save(root: Path, state: Path, request: dict) -> dict:
    """Validate everything first, then write JSON sources and generated files together."""
    settings = clean_settings(request.get("settings", {}))
    rules = clean_rules(request.get("rules", []))
    hotkeys = clean_hotkeys(request.get("hotkeys", []))
    p = paths(root)
    backups = state / "window-backups" / (time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6])
    data = {"settings": settings, "rules": rules}
    write_atomic(p["settings"], json.dumps(data, ensure_ascii=False, indent=2) + "\n", backups)
    write_atomic(p["hotkeys"], json.dumps(hotkeys, ensure_ascii=False, indent=2) + "\n", backups)
    write_atomic(p["yabairc"], render_yabairc(data), backups, 0o755)
    write_atomic(p["skhdrc"], render_skhdrc(hotkeys), backups)
    return {"backup": str(backups) if backups.exists() else ""}


# ── live system ───────────────────────────────────────────────────────────
def run(args: list, timeout: int = 8) -> tuple[int, str]:
    exe = shutil.which(args[0])
    if not exe:
        return 127, ""
    try:
        r = subprocess.run([exe, *args[1:]], capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout or r.stderr).strip()
    except subprocess.TimeoutExpired:
        return 124, "超时"


def running(name: str) -> bool:
    """skhd 把 pid（4 字节整数）写在 /tmp/skhd_<用户>.pid；yabai 能应答查询即在运行。都比 pgrep（约 17 ms）快。"""
    import getpass, os, struct
    if name == "skhd":
        try:
            raw = Path(f"/tmp/skhd_{getpass.getuser()}.pid").read_bytes()
            os.kill(struct.unpack("<i", raw[:4])[0], 0)
            return True
        except (OSError, struct.error, ValueError):
            return False
    return run(["yabai", "-m", "config", "layout"], timeout=3)[0] == 0


def status() -> dict:
    from concurrent.futures import ThreadPoolExecutor
    queries = [["yabai", "-m", "config", key] for key, *_ in SETTINGS]
    # 每项一个短命令，并发查询；yabai 没在运行时这些查询直接失败，即视为未运行。
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(run, queries + [["yabai", "--version"], ["skhd", "--version"]]))
    live = {}
    for (key, *_), (rc, out) in zip(SETTINGS, results):
        if rc == 0 and out:
            live[key] = READBACK.get(out, out)
    yabai_on = bool(live)
    return {"yabai": {"installed": bool(shutil.which("yabai")), "running": yabai_on, "version": results[-2][1]},
            "skhd": {"installed": bool(shutil.which("skhd")), "running": running("skhd"), "version": results[-1][1]},
            "live": live}


def apply_live(root: Path) -> list:
    """Push saved settings and rules into the running yabai; ask skhd to reload."""
    data, done = load(root), []
    if running("yabai"):
        for key, value in data["settings"].items():
            rc, out = run(["yabai", "-m", "config", key, str(value)])
            if rc:
                raise ValueError(f"yabai 拒绝 {key}={value}：{out}")
        rc, out = run(["yabai", "-m", "rule", "--list"])
        for old in (json.loads(out) if rc == 0 and out.startswith("[") else []):
            if str(old.get("label", "")).startswith("mackit-"):
                run(["yabai", "-m", "rule", "--remove", old["label"]])
        for rule in data["rules"]:
            attrs = [f"{k}={rule[k]}" for k in ("manage", "sticky", "space") if k in rule]
            rc, out = run(["yabai", "-m", "rule", "--add", f"label=mackit-{rule['app']}", f"app=^{re.escape(rule['app'])}$", *attrs])
            if rc and "already" not in out:
                raise ValueError(f"应用规则 {rule['app']} 未生效：{out}")
        if data["rules"]:
            run(["yabai", "-m", "rule", "--apply"])
        done.append("yabai")
    if running("skhd"):
        run(["skhd", "--reload"])
        done.append("skhd")
    return done


def service(name: str, start: bool) -> None:
    if name not in ("yabai", "skhd"):
        raise ValueError("未知服务")
    if not shutil.which(name):
        raise ValueError(f"未安装 {name}，请按官方说明安装后再启用。")
    rc, out = run([name, "--start-service" if start else "--stop-service"], timeout=20)
    if rc:
        raise ValueError(f"{name} {'启动' if start else '停止'}失败：{out}")
