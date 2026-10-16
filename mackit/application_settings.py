"""Application-language settings shared by the native page and public CLI.

Only AppleLanguages is changed. Real accounts use macOS defaults (including its
sandbox-domain routing); disposable homes use plist files wholly inside that home.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import plistlib
import pwd
import re
import subprocess
import time
import uuid

from . import cli


def isolated(home):
    # HOME may itself have been replaced by a test runner.
    return home.resolve() != Path(pwd.getpwuid(os.getuid()).pw_dir).resolve()


def canonical(value):
    code = value.replace("_", "-")
    aliases = {"english":"en", "french":"fr", "german":"de", "italian":"it",
               "spanish":"es", "japanese":"ja", "dutch":"nl", "zh-cn":"zh-Hans",
               "zh-sg":"zh-Hans", "zh-tw":"zh-Hant", "zh-hans-cn":"zh-Hans",
               "zh-hant-tw":"zh-Hant", "china":"zh-Hans"}
    return aliases.get(code.lower(), code)


def metadata(home):
    bundled = cli.read(cli.data_root()/"data/application-settings.json")
    # Optional package-external copy overrides are read at runtime; corrupt data falls back.
    try:
        override = cli.read(contained(home/".config/mackit/application-settings.json", home), {})
        if not isinstance(override, dict):
            return bundled
        result = dict(bundled)
        for key in ("copy", "languages"):
            values = override.get(key, {})
            if isinstance(values, dict) and all(isinstance(k,str) and isinstance(v,str) and len(v)<2000 for k,v in values.items()):
                result[key] = {**bundled[key], **values}
        return result
    except (OSError, ValueError):
        return bundled


def contained(path, home):
    if isolated(home) and not path.resolve().is_relative_to(home.resolve()):
        raise cli.Failure("隔离目录中的链接指向目录之外，未读写。", "outside_home")
    return path


def load_plist(path):
    if not path.exists():
        return {}
    if path.stat().st_size > 16*1024*1024:
        raise ValueError("偏好文件过大，未读取。")
    data = plistlib.loads(path.read_bytes())
    if not isinstance(data, dict):
        raise ValueError("偏好文件格式无效。")
    return data


def installed(home):
    roots = [home/"Applications"]
    if not isolated(home):
        roots += [Path("/Applications"), Path("/System/Applications")]
    apps = {}
    problems = []
    def visit(root, depth=0):
        if not root.is_dir():
            return
        for path in sorted(root.iterdir()):
            if path.name.startswith("."):
                continue
            if path.suffix.lower() != ".app":
                if depth < 2 and path.is_dir() and not path.is_symlink():
                    visit(path, depth+1)
                continue
            try:
                contained(path, home)
                info = load_plist(contained(path/"Contents/Info.plist", home))
                bundle = info.get("CFBundleIdentifier", "")
                if not isinstance(bundle, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]+", bundle):
                    continue
                resources = contained(path/"Contents/Resources", home)
                values = list(info.get("CFBundleLocalizations", []))
                values += [p.stem for p in resources.glob("*.lproj") if p.is_dir()]
                values += [info.get("CFBundleDevelopmentRegion", "")]
                languages = sorted({canonical(v) for v in values if isinstance(v, str)
                                    and v.lower() != "base" and re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{1,32}", v)})
                languages.sort(key=lambda v:({"zh-Hans":0,"zh-Hant":1,"en":2}.get(v,3),v))
                apps.setdefault(bundle, {"id":bundle, "name":str(info.get("CFBundleDisplayName") or info.get("CFBundleName") or path.stem),
                                        "path":str(path), "languageIDs":languages})
            except (OSError, ValueError, TypeError, plistlib.InvalidFileException) as exc:
                problems.append(f"{path.name}：{exc}")
    for root in roots:
        visit(root)
    return apps, problems


def preference_path(bundle, home):
    sandbox = home/"Library/Containers"/bundle/"Data/Library/Preferences"/(bundle+".plist")
    normal = home/"Library/Preferences"/(bundle+".plist")
    return contained(sandbox if sandbox.exists() else normal, home)


def preference(bundle, home, live=False):
    if live and not isolated(home):
        result = subprocess.run(["/usr/bin/defaults", "export", bundle, "-"], capture_output=True, timeout=10)
        if result.returncode:
            if "does not exist" not in result.stderr.decode(errors="replace"):
                raise cli.Failure("无法读取应用偏好，未修改："+bundle, "read_failed")
            data = {}
        else:
            data = plistlib.loads(result.stdout)
    else:
        data = load_plist(preference_path(bundle, home))
    value = data.get("AppleLanguages")
    if value is not None and (not isinstance(value, list) or any(not isinstance(v, str) for v in value)):
        raise cli.Failure("应用的语言偏好格式无效，未覆盖："+bundle, "invalid_preference")
    return value


def write_preference(bundle, value, home):
    if not isolated(home):
        args = ["/usr/bin/defaults", "delete", bundle, "AppleLanguages"] if value is None else [
            "/usr/bin/defaults", "write", bundle, "AppleLanguages", "-array", *value]
        subprocess.run(args, capture_output=True, check=True, timeout=10)
    else:
        path = preference_path(bundle, home)
        data = load_plist(path)
        if value is None:
            data.pop("AppleLanguages", None)
        else:
            data["AppleLanguages"] = value
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(path.name+".mackit-"+uuid.uuid4().hex)
        try:
            temp.write_bytes(plistlib.dumps(data))
            temp.chmod(path.stat().st_mode & 0o777 if path.exists() else 0o600)
            temp.replace(path)
        finally:
            temp.unlink(missing_ok=True)
    if preference(bundle, home, live=True) != value:
        raise cli.Failure("语言设置回读不一致："+bundle, "readback_failed")


def digest(app, value):
    return hashlib.sha256(json.dumps([app["id"], app["path"], app["languageIDs"], value], sort_keys=True).encode()).hexdigest()


def records_dir(home):
    return contained(cli.paths(home)[1]/"application-languages", home)


def latest(home):
    records = [cli.read(path) for path in records_dir(home).glob("*.json")]
    return max((r for r in records if r.get("status") in ("applied", "preparing", "rollback_failed")), key=lambda r:r["createdAt"], default=None)


def snapshot(home, query=""):
    if not isinstance(query, str) or len(query) > 256:
        raise cli.Failure("搜索文字无效或过长。", "invalid_query")
    meta = metadata(home)
    apps, problems = installed(home)
    running = ""
    if not isolated(home):
        running = subprocess.check_output(["/bin/ps", "-axo", "comm="], text=True, timeout=10)
    rows = []
    for app in apps.values():
        try:
            value = preference(app["id"], home)
            selected = canonical(value[0]) if value else "system"
            choices = [{"id":"system", "label":meta["copy"]["system"]}]
            choices += [{"id":v, "label":meta["languages"].get(v, v)} for v in app["languageIDs"]]
            if selected != "system" and selected not in app["languageIDs"]:
                choices.append({"id":selected, "label":meta["languages"].get(selected, selected)+"（当前设置）"})
            active = app["path"]+"/Contents/MacOS/" in running
            status = meta["copy"]["running"] if active else meta["copy"]["saved"] if value else meta["copy"]["system"]
            row = {**app, "languages":choices, "selected":selected, "current":value,
                   "digest":digest(app, value), "running":active, "status":status,
                   "office":app["id"] in meta["office"]}
            haystack = " ".join([app["name"], app["id"], "Office 办公 中文" if row["office"] else "", *app["languageIDs"]])
            if not query or query.casefold() in haystack.casefold():
                rows.append(row)
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            problems.append(app["name"]+"："+str(exc))
    record = latest(home)
    return {"apps":sorted(rows, key=lambda r:(not r["office"], r["name"].casefold())),
            "copy":meta["copy"], "problems":problems, "isolated":isolated(home),
            "latestTransaction":record["id"] if record else ""}


def change(home, changes):
    if not isinstance(changes, list) or not changes:
        raise cli.Failure("请选择要修改的应用。", "empty_selection")
    state = cli.paths(home)[1]
    with cli.locked(state):
        pending = latest(home)
        if pending and pending["status"] != "applied":
            raise cli.Failure("有未完成的语言修改，请先恢复上次语言修改。", "recovery_required")
        apps, _ = installed(home)
        operations, seen = [], set()
        # Validate the entire batch before creating a record or writing any preference.
        for item in changes:
            if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                raise cli.Failure("应用设置参数无效。", "invalid_request")
            bundle = item["id"]
            if bundle in seen or bundle not in apps:
                raise cli.Failure("应用不存在或重复："+bundle, "not_found")
            seen.add(bundle)
            app = apps[bundle]
            language = item.get("language")
            if not isinstance(language, str):
                raise cli.Failure("请选择界面语言。", "invalid_language")
            language = canonical(language)
            if language != "system" and language not in app["languageIDs"]:
                raise cli.Failure(app["name"]+" 未提供所选语言。", "unsupported_language")
            before = preference(bundle, home, live=True)
            if item.get("digest") and item["digest"] != digest(app, before):
                raise cli.Failure("应用设置已被其他程序修改，请刷新后重试。", "stale_digest")
            after = None if language == "system" else [language]
            if before == after or before and language != "system" and canonical(before[0]) == language:
                continue
            operations.append({"id":bundle, "path":app["path"], "before":before, "after":after})
        if not operations:
            return {"message":"所选应用已经使用这些语言设置。", "changed":0, "transaction":""}
        record = {"id":cli.new_tx(), "createdAt":time.time_ns(), "status":"preparing", "operations":operations}
        path = records_dir(home)/(record["id"]+".json")
        cli.dump(path, record)
        applied = []
        try:
            for op in operations:
                # Include the in-flight operation: a write may succeed before its readback fails.
                applied.append(op)
                write_preference(op["id"], op["after"], home)
            record["status"] = "applied"
            cli.dump(path, record)
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            errors = []
            for op in reversed(applied):
                try:
                    if preference(op["id"], home, live=True) != op["before"]:
                        write_preference(op["id"], op["before"], home)
                except (OSError, ValueError, subprocess.SubprocessError) as rollback:
                    errors.append(str(rollback))
            record.update(status="rollback_failed" if errors else "rolled_back", error=str(exc), rollback_errors=errors)
            cli.dump(path, record)
            raise cli.Failure("语言修改未完成，"+("恢复未全部完成，请保留恢复记录。" if errors else "已恢复修改前设置。"), "write_failed", transaction=record["id"]) from exc
    return {"message":f"已为 {len(operations)} 个应用保存语言设置；重新打开对应应用后生效。",
            "changed":len(operations), "transaction":record["id"]}


def restore(home, transaction=None):
    with cli.locked(cli.paths(home)[1]):
        record = latest(home)
        if not record or transaction and transaction != record["id"]:
            raise cli.Failure("请选择最近一次仍可恢复的语言修改记录。", "not_found")
        apps, _ = installed(home)
        for op in record["operations"]:
            if op["id"] not in apps or apps[op["id"]]["path"] != op["path"]:
                raise cli.Failure("应用已移动或移除，未恢复。", "app_changed")
            current = preference(op["id"], home, live=True)
            if current != op["after"] and not (record["status"] != "applied" and current == op["before"]):
                raise cli.Failure("语言后来被其他程序修改，未覆盖；请刷新查看。", "stale_digest")
        done = []
        try:
            for op in reversed(record["operations"]):
                if preference(op["id"], home, live=True) == op["before"]:
                    continue
                done.append(op)
                write_preference(op["id"], op["before"], home)
        except (OSError, ValueError, subprocess.SubprocessError):
            for op in reversed(done):
                if preference(op["id"], home, live=True) != op["after"]:
                    write_preference(op["id"], op["after"], home)
            raise
        record["status"] = "restored"
        cli.dump(records_dir(home)/(record["id"]+".json"), record)
    return {"message":"已恢复上次修改前的语言设置；重新打开对应应用后生效。", "transaction":record["id"]}


def dispatch(request, home):
    action = request["action"]
    if action == "applicationSnapshot":
        return {"applications":snapshot(home, request.get("query", ""))}
    if action == "applicationLanguage":
        return change(home, request.get("changes"))
    if action == "applicationRestore":
        return restore(home, request.get("transaction"))
    raise cli.Failure("未知应用设置操作。", "invalid_request")
