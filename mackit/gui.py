"""Native-app JSON bridge. Installation and restoration remain owned by cli.py.

Requests arrive on stdin, progress on stderr, one JSON response on stdout.
No shell evaluates requests. An isolated --home uses the same production path.
"""
from __future__ import annotations
import argparse, contextlib, hashlib, io, json, os, shlex, shutil, subprocess, sys, time, uuid
from pathlib import Path
from . import cli

LABELS = {"zsh":"Shell 与命令行", "nvim":"Neovim 编辑器", "ghostty":"Ghostty 终端", "tmux":"终端分屏", "yazi":"Yazi 文件管理", "starship":"命令提示符", "lazygit":"Git 界面", "atuin":"命令历史", "hammerspoon":"桌面快捷键", "karabiner":"键盘映射", "yabai":"窗口管理（可选）", "btop":"系统资源", "fd":"文件查找", "glow":"Markdown 阅读"}
APPS = {"ghostty":"Ghostty", "hammerspoon":"Hammerspoon", "karabiner":"Karabiner-Elements"}

def valid_root(path):
    return (path/"components/nvim/init.lua").is_file() and (path/"profiles/developer.json").is_file() and (path/"VERSION").is_file() and (path/"bin/mackit").is_file()

def source_root(home, payload):
    config, _ = cli.paths(home)
    saved=cli.read(config/"profile.json",{})
    if saved.get("source_root"):
        root=Path(saved["source_root"])
        if valid_root(root): return root
        raise ValueError("已安装配置的来源目录已移动。请恢复该目录后重试："+str(root))
    # v0.1 migration: inspect the generated launcher, never execute its contents.
    shim=home/".local/bin/mackit"
    if shim.is_file() and shim.stat().st_size < 8192:
        for line in shim.read_text().splitlines():
            parts=shlex.split(line)
            if len(parts)>=2 and parts[0]=="exec":
                root=Path(parts[1]).parent.parent
                if valid_root(root):return root
    if saved:
        raise ValueError("检测到旧安装记录，但找不到配置来源；请先恢复原 MacKit 目录。")
    root=home/".local/share/mackit"
    if not root.parent.resolve().is_relative_to(home.resolve()):
        raise ValueError("配置目录的父级指向用户目录之外，请先检查 ~/.local/share。")
    if cli.exists(root) and not valid_root(root):
        raise ValueError("~/.local/share/mackit 已有其他内容，未覆盖。请先移走或改名。")
    return root

def ensure_source(root,payload):
    if valid_root(root):return
    root.parent.mkdir(parents=True,exist_ok=True)
    temp=root.with_name(".mackit-install-"+uuid.uuid4().hex)
    try:
        # The app carries an allowlisted core, not the developer working tree.
        temp.mkdir()
        for name in ("bin","mackit","components","profiles","data","VERSION","LICENSE","THIRD_PARTY.md","install.sh"):
            src=payload/name
            if not src.exists():continue
            if src.is_dir():shutil.copytree(src,temp/name,symlinks=True,ignore=shutil.ignore_patterns("__pycache__","*.pyc",".DS_Store"))
            else:shutil.copy2(src,temp/name)
        if not valid_root(temp):raise ValueError("App 内置配置不完整，请重新下载安装包。")
        if cli.exists(root):raise ValueError("配置目录在预览期间发生变化，请重新打开 App。")
        temp.rename(root)
    finally:
        if temp.exists():shutil.rmtree(temp)

def arguments(request, home):
    name=request.get("profile") or cli.read(cli.paths(home)[0]/"profile.json",{}).get("profile","developer")
    if name not in ("developer","tianli"):raise ValueError("未知预设")
    chosen=request.get("components")
    if chosen is not None and (not isinstance(chosen,list) or not chosen or not all(isinstance(c,str) and c in cli.COMPONENTS for c in chosen)):
        raise ValueError("请至少选择一个有效组件。")
    return argparse.Namespace(profile=name, components=",".join(chosen) if chosen is not None else None)

def dependencies(selected, home):
    result=[]
    for name in sorted({d for c in selected for d in cli.DEPS.get(c,[])}):
        command={"neovim":"nvim","ripgrep":"rg"}.get(name,name)
        result.append({"id":name,"kind":"formula","installed":bool(shutil.which(command)),"label":name})
    for comp in selected:
        if comp in cli.CASKS:
            app=APPS[comp]
            installed=any((p/(app+".app")).is_dir() for p in [Path("/Applications"),home/"Applications"])
            result.append({"id":cli.CASKS[comp],"kind":"cask","installed":installed,"label":app})
    return result

def capture(fn,*args):
    out=io.StringIO()
    with contextlib.redirect_stdout(out):rc=fn(*args)
    return out.getvalue(),rc

def plan_result(args,home):
    p=cli.plan(args,home)
    fingerprints=[cli.fingerprint(Path(e["target"])) for e in p["entries"]]
    token=hashlib.sha256(json.dumps([p,fingerprints],sort_keys=True).encode()).hexdigest()
    return {"plan":p,"token":token,"dependencies":dependencies(p["components"],home)}

def inventory(home,payload,root):
    config,state=cli.paths(home)
    installed=cli.read(config/"profile.json",{})
    records=[cli.read(p) for p in sorted((state/"transactions").glob("*.json"),reverse=True)]
    transactions=[{"id":r["id"],"status":r["status"],"changed":len(r["operations"]),"profile":r["profile"]} for r in records if r.get("operations")]
    defs=[]
    for name in cli.COMPONENTS:
        defs.append({"id":name,"label":LABELS[name],"desktop":name in ("hammerspoon","karabiner","yabai")})
    edit=[{"id":k,"path":str(root/"components"/v)} for k,v in cli.EDIT.items() if k!="vim"]
    edit += [{"id":k,"path":str(config/v)} for k,v in {"local":"local.zsh","local-keys":"keymaps.zsh","hs-local":"hammerspoon.lua"}.items()]
    data_root=root if valid_root(root) else payload
    return {"installed":bool(installed),"profile":installed.get("profile","developer"),"selected":installed.get("components",cli.profile("developer")["components"]),
        "sourceRoot":str(root),"sourceVersion":(data_root/"VERSION").read_text().strip(),"appVersion":(payload/"VERSION").read_text().strip(),
        "components":defs,"profiles":{n:cli.read(data_root/"profiles"/(n+".json"))["components"] for n in ("developer","tianli")},
        "transactions":transactions,"files":edit,"keys":cli.read(data_root/"data/keys.json",[]),"brew":shutil.which("brew") or ""}

def edit_path(request,home,root):
    ident=request.get("file","")
    local={"local":"local.zsh","local-keys":"keymaps.zsh","hs-local":"hammerspoon.lua"}
    base=cli.paths(home)[0] if ident in local else root/"components"
    if ident not in local and ident not in cli.EDIT:raise ValueError("未知配置文件")
    path=base/(local[ident] if ident in local else cli.EDIT[ident])
    if not path.resolve().is_relative_to(base.resolve()):raise ValueError("文件链接指向配置目录之外，未写入。")
    return path

def file_result(path):
    if path.exists() and path.stat().st_size>1024*1024:raise ValueError("文件超过 1 MB，请使用外部编辑器。")
    raw=path.read_bytes() if path.exists() else b""
    return {"path":str(path),"content":raw.decode("utf-8"),"digest":hashlib.sha256(raw).hexdigest() if path.exists() else "absent"}

def install_dependencies(items,home):
    missing=[d for d in items if not d["installed"]]
    if not missing:return {"message":"所选应用与依赖已经安装。","dependencies":items}
    brew=shutil.which("brew")
    if not brew:raise ValueError("请先点击“安装 Homebrew”，在系统安装器完成后回到这里重试。")
    if home.resolve()!=Path.home().resolve():raise ValueError("演示目录不会安装或改动本机软件。")
    env=os.environ.copy();env.update(HOMEBREW_NO_AUTO_UPDATE="1",HOMEBREW_NO_ENV_HINTS="1",NONINTERACTIVE="1")
    for d in missing:
        print("正在安装 "+d["label"]+"…",file=sys.stderr,flush=True)
        args=[brew,"install"]+(["--cask"] if d["kind"]=="cask" else [])+[d["id"]]
        result=subprocess.run(args,stdin=subprocess.DEVNULL,stdout=sys.stderr,stderr=sys.stderr,env=env,timeout=1800)
        if result.returncode:
            raise ValueError(d["label"]+" 未完成安装（可能是网络或系统授权）。已安装的其他依赖会保留；查看运行记录后重试。需要管理员权限的软件可用页面中的官方安装入口。")
    return {"message":"依赖安装完成。"}

def dispatch(request,home):
    payload=cli.ROOT
    root=source_root(home,payload)
    action=request.get("action","snapshot")
    if action=="snapshot":return inventory(home,payload,root)
    args=arguments(request,home)
    if action=="dependencies":return {"dependencies":dependencies(cli.selection(args,home)[1],home)}
    if action=="installDependencies":return install_dependencies(dependencies(cli.selection(args,home)[1],home),home)
    if action not in ("preview","apply","doctor","restore","readFile","saveFile"):
        raise ValueError("未知操作")
    if action in ("preview","apply"):ensure_source(root,payload)
    if not valid_root(root):raise ValueError("请先在“安装配置”中预览并准备配置。")
    cli.ROOT=root
    try:
        if action=="preview":return plan_result(args,home)
        if action=="apply":
            # Revalidate the exact reviewed plan. cli.apply owns the transaction lock.
            current=plan_result(args,home)
            if request.get("token")!=current["token"]:raise ValueError("配置或选择已变化，请重新预览后安装。")
            out,_=capture(cli.apply,args,home)
            return {"installation":json.loads(out),"message":"配置已安装，原配置已备份。重新打开终端和相关应用后生效。"}
        if action=="doctor":
            out,_=capture(cli.doctor,args,home)
            return {"diagnosis":json.loads(out)}
        if action=="restore":
            # No implicit fallback to a different/newer transaction.
            tx=request.get("transaction")
            if not isinstance(tx,str) or not tx:raise ValueError("请选择要恢复的最近一次安装记录。")
            out,_=capture(cli.restore,argparse.Namespace(transaction=tx),home)
            return {"message":"已恢复安装前的配置。个人覆盖文件保留。","detail":out}
        path=edit_path(request,home,root)
        if action=="readFile":return file_result(path)
        text=request.get("content")
        if not isinstance(text,str) or len(text.encode())>1024*1024:raise ValueError("配置文本无效或超过 1 MB")
        _,state=cli.paths(home)
        with cli.locked(state):
            old=file_result(path)
            if old["digest"]!=request.get("digest"):raise ValueError("文件已被其他程序修改，请重新读取后保存。")
            backup=state/"editor-backups"/(time.strftime("%Y%m%d-%H%M%S")+"-"+uuid.uuid4().hex[:6]+"-"+path.name)
            if path.exists():
                backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,backup);backup.chmod(0o600)
            path.parent.mkdir(parents=True,exist_ok=True)
            tmp=path.with_name("."+path.name+".mackit-"+uuid.uuid4().hex)
            try:
                tmp.write_text(text);tmp.chmod(path.stat().st_mode & 0o777 if path.exists() else 0o600);tmp.replace(path)
            finally:
                if tmp.exists():tmp.unlink()
        message="已创建新配置文件。" if old["digest"]=="absent" else "已保存。修改前副本位于恢复记录目录。"
        return {**file_result(path),"message":message,"backup":str(backup) if old["digest"]!="absent" else ""}
    finally:cli.ROOT=payload

def main(home):
    try:
        request=json.load(sys.stdin)
        if not isinstance(request,dict):raise ValueError("请求格式无效")
        result=dispatch(request,home)
        print(json.dumps({"ok":True,**result},ensure_ascii=False))
    except (ValueError,OSError,subprocess.SubprocessError) as exc:
        print(json.dumps({"ok":False,"error":str(exc)},ensure_ascii=False))
    return 0
