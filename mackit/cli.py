"""MacKit CLI: inspectable plans, reversible installs, native config sources."""
from __future__ import annotations
import argparse, contextlib, fcntl, hashlib, json, os, shlex, shutil, subprocess, sys, tempfile, time, uuid
from pathlib import Path
try:
 from mackit.localkeys import local_rows, conflicts, clashes, combo
except ImportError:  # run as a script from the repo
 from localkeys import local_rows, conflicts, clashes, combo

ROOT = Path(sys.executable).resolve().parents[1] if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]
# Where configuration content is read from while ROOT names a source that apply has not created yet
# (the App's CLI on a new Mac plans against ~/.local/share/mackit but reads its bundled payload).
READ_ROOT = None
COMPONENTS = {
 "zsh": [("generated:zshrc", ".zshrc")],
 "nvim": [("nvim", ".config/nvim")],
 "ghostty": [("generated:ghostty", ".config/ghostty")],
 "tmux": [("tmux", ".config/tmux"), ("tmux/tmux.conf", ".tmux.conf")],
 "yazi": [("yazi", ".config/yazi")],
 "starship": [("starship/starship.toml", ".config/starship.toml")],
 "lazygit": [("lazygit", ".config/lazygit")],
 "atuin": [("atuin", ".config/atuin")],
 "hammerspoon": [("hammerspoon", ".hammerspoon")],
 "karabiner": [("generated:karabiner", ".config/karabiner")],
 "yabai": [("yabai/config", ".config/yabai"), ("yabai/config/skhd", ".config/skhd")],
 "btop": [("btop/btop.conf", ".config/btop/btop.conf")],
 "fd": [("fd/ignore", ".config/fd/ignore")],
 "glow": [("glow/glow.yml", ".config/glow/glow.yml")],
}
EDIT = {
 "nvim": "nvim/init.lua", "vim": "nvim/init.lua", "number": "nvim/lua/config/options.lua",
 "nvim-keys": "nvim/lua/config/keymaps.lua", "zsh": "zsh/zshrc", "zsh-keys": "zsh/keymaps.zsh",
 "hammerspoon": "hammerspoon/init.lua", "hs-keys": "hammerspoon/keymaps.lua",
 "ghostty": "ghostty/config", "tmux": "tmux/tmux.conf", "tmux-keys": "tmux/keymaps.conf",
 "yazi": "yazi/yazi.toml", "yazi-keys": "yazi/keymap.toml",
 "karabiner": "karabiner/karabiner.json",
 "ghostty-keys": "ghostty/keymaps.conf",
 "btop": "btop/btop.conf", "fd": "fd/ignore", "glow": "glow/glow.yml",
}
# yabairc/skhdrc are generated from settings.json/hotkeys.json: `mackit window` or the 窗口 page edits them.
GENERATED = {"yabai": "yabai/skhd settings are generated; change them with `mackit window` (or the App's 窗口 page)."}
LOCAL_EDIT = {"local": "local.zsh", "local-keys": "keymaps.zsh", "hs-local": "hammerspoon.lua"}
DEPS = {"zsh":["fzf","fd","ripgrep","zoxide","atuin","starship","eza"], "nvim":["neovim","git","ripgrep","fd"],
 "tmux":["tmux"],"yazi":["yazi"],"lazygit":["lazygit"],"atuin":["atuin"],"starship":["starship"],
 "btop":["btop"],"fd":["fd"],"glow":["glow"]}
CASKS = {"ghostty":"ghostty","hammerspoon":"hammerspoon","karabiner":"karabiner-elements"}
def dump(path, data):
 path.parent.mkdir(parents=True, exist_ok=True)
 tmp=path.with_name(path.name+".tmp-"+uuid.uuid4().hex)
 tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")
 tmp.chmod(0o600);tmp.replace(path)
def data_root(): return READ_ROOT or ROOT
def edit_files(home, root, aliases=True):
 """Editable configuration ids: component sources under root, then personal overrides in ~/.config/mackit."""
 files=[{"id":k,"path":str(root/"components"/v),"local":False} for k,v in EDIT.items() if aliases or k!="vim"]
 return files+[{"id":k,"path":str(paths(home)[0]/v),"local":True} for k,v in LOCAL_EDIT.items()]
def tool_path():
 """The caller's PATH plus the locations the App's engine always searches (EngineClient.swift)."""
 parts=os.environ.get("PATH","").split(os.pathsep)
 extra=["/opt/homebrew/bin","/usr/local/bin",str(Path.home()/".local/bin"),"/usr/bin","/bin","/usr/sbin","/sbin"]
 return os.pathsep.join([p for p in parts if p]+[p for p in extra if p not in parts])
def read(path, default=None):
 return json.loads(path.read_text()) if path.exists() else default
def exists(path): return path.exists() or path.is_symlink()
def fingerprint(path):
 if path.is_symlink(): return "link:"+os.readlink(path)
 if path.is_file(): return "sha256:"+hashlib.sha256(path.read_bytes()).hexdigest()
 if path.is_dir(): return "directory"
 return "absent"
def tree_digest(path):
 return [(str(p.relative_to(path)),fingerprint(p)) for p in sorted(path.rglob("*")) if not p.is_dir() or p.is_symlink()]
def paths(home):
 result=(home/".config/mackit",home/".local/state/mackit")
 for p in result:
  if not p.resolve().is_relative_to(home.resolve()):raise ValueError("MacKit state escapes target home: "+str(p))
 return result
def bundled_cli():
 """The CLI inside an installed MacKit.app, or None when running from a source checkout."""
 exe=Path(sys.executable).resolve()
 return exe if getattr(sys,"frozen",False) and ".app/Contents/" in str(exe) else None
def isolated(home):
 """Any --home other than your own is a sandbox: nothing outside it is written, installed or started."""
 return home.resolve()!=Path.home().resolve()
@contextlib.contextmanager
def locked(state):
 state.mkdir(parents=True,exist_ok=True)
 with (state/"lock").open("a") as f:
  fcntl.flock(f,fcntl.LOCK_EX)
  yield
def profile(name):
 return read(data_root()/"profiles"/(name+".json"))
def selection(args, home):
 saved=read(paths(home)[0]/"profile.json",{})
 name=args.profile or saved.get("profile","developer")
 chosen=args.components.split(",") if args.components else (profile(name)["components"] if args.profile else saved.get("components",profile(name)["components"]))
 unknown=set(chosen)-COMPONENTS.keys()
 if unknown: raise ValueError("Unknown components: "+", ".join(sorted(unknown)))
 return name,list(dict.fromkeys(chosen))
def plan(args,home):
 name,selected=selection(args,home)
 entries=[]
 for comp in selected:
  for src,dest in COMPONENTS[comp]:
   source=ROOT/"components"/src
   if not src.startswith("generated:") and not (data_root()/"components"/src).exists(): raise ValueError("Missing source: "+str(source))
   target=home/dest
   # A linked config entry is OK; a symlinked parent escaping HOME is not.
   parent=target.parent.resolve()
   if not parent.is_relative_to(home.resolve()): raise ValueError("Target parent escapes home: "+str(target))
   status="unchanged" if src.startswith("generated:") is False and target.is_symlink() and target.resolve()==source.resolve() else ("backup + install" if exists(target) else "install")
   entries.append({"component":comp,"source":str(source) if not src.startswith("generated:") else src,"target":str(target),"action":status})
 result={"profile":name,"components":selected,"root":str(ROOT),"entries":entries}
 saved=read(paths(home)[0]/"profile.json",{})
 result["installed_components"]=list(dict.fromkeys((saved.get("components",[]) if saved.get("profile")==name else [])+selected))
 with tempfile.TemporaryDirectory(prefix="mackit-plan-") as temp:
  proposed=Path(temp);write_generated(proposed,home,result)
  for e in entries:
   if not e["source"].startswith("generated:"):continue
   source=proposed/e["source"].split(":",1)[1];target=Path(e["target"])
   if target.is_symlink() and target.resolve().is_relative_to((paths(home)[1]/"generations").resolve()):
    if source.is_file() and target.is_file() and source.read_bytes()==target.read_bytes():e["action"]="unchanged"
    elif source.is_dir() and target.is_dir() and tree_digest(source)==tree_digest(target.resolve()):e["action"]="unchanged"
 return result
def plan_token(p):
 """Binds an apply to the reviewed plan and the targets' current state (same token the App's preview returns)."""
 fingerprints=[fingerprint(Path(e["target"])) for e in p["entries"]]
 return hashlib.sha256(json.dumps([p,fingerprints],sort_keys=True).encode()).hexdigest()
def write_generated(generation,home,p):
 generation.mkdir(parents=True,exist_ok=True)
 z= "export MACKIT_ROOT="+shlex.quote(str(ROOT))+"\nsource "+shlex.quote(str(ROOT/"components/zsh/zshrc"))+"\n"
 (generation/"zshrc").write_text(z)
 dump(generation/"profile.json",{"profile":p["profile"],"components":p.get("installed_components",p["components"]),"version":(data_root()/"VERSION").read_text().strip(),"source_root":str(ROOT)})
 (generation/"profile.zsh").write_text("export MACKIT_PROFILE="+shlex.quote(p["profile"])+"\n")
 (generation/"mackit").write_text("#!/bin/sh\nexec "+shlex.quote(str(ROOT/"bin/mackit"))+' "$@"\n')
 (generation/"mackit").chmod(0o755)
 ghost= generation/"ghostty"
 ghost.mkdir()
 includes=[ROOT/"components/ghostty/config"]
 if p["profile"]=="tianli":includes.append(ROOT/"components/ghostty/keymaps.conf")
 content="\n".join("config-file = "+str(x) for x in includes)
 content+="\nconfig-file = ?"+str(home/".config/mackit/ghostty.conf")+"\n"
 (ghost/"config").write_text(content)
 # Karabiner rewrites its JSON. Keep machine identifiers out of the source
 # repository and generate a writable installation per transaction.
 karabiner=generation/"karabiner";karabiner.mkdir()
 keyboard=read(data_root()/"components/karabiner/karabiner.json")
 local=read(home/".config/mackit/karabiner-device-settings.json",{})
 if "machine_specific" in local:keyboard["machine_specific"]=local["machine_specific"]
 for item in keyboard["profiles"]:
  if "devices" in local:item["devices"]=local["devices"]
 dump(karabiner/"karabiner.json",keyboard)
def restore_ops(ops, check=True):
 if check:
  for op in ops:
   if fingerprint(Path(op["target"]))!=op["installed"]:
    raise ValueError("Changed since install; preserve or move before restore: "+op["target"])
 else:
  for op in ops:
   current=fingerprint(Path(op["target"]))
   if current not in (op["before"],op["installed"],"absent"):
    raise ValueError("Interrupted install has new user changes; preserve before restore: "+op["target"])
 for op in reversed(ops):
  target=Path(op["target"]);backup=Path(op["backup"])
  if not check and not exists(backup) and fingerprint(target)==op["before"]:continue
  if exists(target):
   if target.is_dir() and not target.is_symlink(): raise ValueError("Refusing to remove directory: "+str(target))
   target.unlink()
  if exists(backup):backup.replace(target)
def interrupted(state):
 for receipt in (state/"transactions").glob("*.json"):
  if read(receipt).get("status")=="installing":
   raise ValueError("Interrupted installation found. Run mackit restore before applying again.")
def new_tx(): return time.strftime("%Y%m%d-%H%M%S")+"-"+uuid.uuid4().hex[:6]
def link_entries(home,state,tx,record,entries,generation):
 """Back up and link each target under one receipt; any failure restores every step taken."""
 receipt=state/"transactions"/(tx+".json");dump(receipt,record)
 try:
  for i,e in enumerate(entries):
   source=generation/e["source"].split(":",1)[1] if e["source"].startswith("generated:") else Path(e["source"])
   target=Path(e["target"])
   if target.is_symlink() and target.resolve()==source.resolve():continue
   if source.is_file() and target.is_symlink() and target.resolve().is_file() and target.read_bytes()==source.read_bytes() and target.resolve().is_relative_to((state/"generations").resolve()):continue
   if source.is_dir() and target.is_symlink() and target.resolve().is_dir() and target.resolve().is_relative_to((state/"generations").resolve()) and tree_digest(source)==tree_digest(target.resolve()):continue
   if not target.parent.resolve().is_relative_to(home.resolve()):raise ValueError("Target parent escapes home: "+str(target))
   target.parent.mkdir(parents=True,exist_ok=True)
   backup=state/"backups"/tx/str(i);backup.parent.mkdir(parents=True,exist_ok=True)
   op={"target":str(target),"backup":str(backup),"before":fingerprint(target),"installed":"link:"+str(source)}
   record["operations"].append(op);dump(receipt,record)
   if exists(target): target.replace(backup)
   target.symlink_to(source)
  record["status"]="applied";dump(receipt,record)
 except BaseException:
  restore_ops(record["operations"],check=False);record["status"]="rolled_back";dump(receipt,record)
  raise
def apply(args,home):
 global READ_ROOT
 config,state=paths(home)
 with locked(state):
  interrupted(state)
  p=plan(args,home)
  token=getattr(args,"token",None)
  if token and token!=plan_token(p):raise ValueError("The plan changed since it was reviewed. Run mackit plan --json again and pass the new token.")
  saved=read(config/"profile.json",{})
  if saved.get("profile") and saved["profile"]!=p["profile"]:
   raise ValueError("Restore the current preset before switching profiles; this also restores its global keyboard rules.")
  if READ_ROOT:  # the plan holds, so create the source it names now (a refused apply leaves nothing behind)
   from mackit import gui
   gui.ensure_source(ROOT,READ_ROOT);READ_ROOT=None
  tx=new_tx()
  generation=state/"generations"/tx
  write_generated(generation,home,p)
  entries=p["entries"]+[
   {"source":str(generation/"profile.json"),"target":str(config/"profile.json")},
   {"source":str(generation/"profile.zsh"),"target":str(config/"profile.zsh")},
   {"source":str(bundled_cli() or generation/"mackit"),"target":str(home/".local/bin/mackit")}]
  record={"id":tx,"status":"installing","profile":p["profile"],"components":p["components"],"operations":[]}
  link_entries(home,state,tx,record,entries,generation)
  print(json.dumps({"ok":True,"transaction":tx,"changed":len(record["operations"]),"profile":p["profile"],"restore":"mackit restore "+tx},ensure_ascii=False))
def command_link(home):
 """Where ~/.local/bin/mackit points, and whether that is this command (an App rename leaves old links behind)."""
 link=home/".local/bin/mackit";current=bundled_cli()
 if not link.is_symlink():return {"path":str(link),"exists":link.exists(),"symlink":False}
 target=os.readlink(link)
 return {"path":str(link),"target":target,"symlink":True,"resolves":link.exists(),
  "current":bool(current) and link.exists() and link.resolve()==current}
def relink(args,home,payload):
 """Point ~/.local/bin/mackit at this copy of the command as one recorded, restorable change."""
 config,state=paths(home)
 with locked(state):
  interrupted(state)
  target=home/".local/bin/mackit";source=bundled_cli()
  if source and target.is_symlink() and target.resolve()==source:
   return {"ok":True,"changed":0,"target":str(target),"source":str(source),"message":"Already linked."}
  tx=new_tx();generation=state/"generations"/tx
  if not source:
   generation.mkdir(parents=True,exist_ok=True);source=generation/"mackit"
   source.write_text("#!/bin/sh\nexec "+shlex.quote(str(payload/"bin/mackit"))+' "$@"\n');source.chmod(0o755)
  saved=read(config/"profile.json",{})
  record={"id":tx,"status":"installing","profile":saved.get("profile","developer"),"components":saved.get("components",[]),"operations":[]}
  link_entries(home,state,tx,record,[{"source":str(source),"target":str(target)}],generation)
  if not record["operations"]:
   (state/"transactions"/(tx+".json")).unlink();shutil.rmtree(generation,ignore_errors=True)
  return {"ok":True,"changed":len(record["operations"]),"transaction":tx if record["operations"] else "","target":str(target),"source":str(source),
   "restore":"mackit restore "+tx if record["operations"] else ""}
def restore(args,home):
 _,state=paths(home)
 with locked(state):
  records=sorted((state/"transactions").glob("*.json"))
  active=[(p,read(p)) for p in records if read(p)["status"] in ["applied","installing"] and read(p)["operations"]]
  if not active:raise ValueError("No active installation to restore")
  p,r=active[-1]
  if args.transaction and args.transaction!=r["id"]:raise ValueError("Restore newest active transaction first: "+r["id"])
  restore_ops(r["operations"],check=r["status"]=="applied")
  r["status"]="restored";dump(p,r)
  if getattr(args,"json",False):print(json.dumps({"ok":True,"restored":r["id"],"changed":len(r["operations"])},ensure_ascii=False))
  else:print("Restored "+r["id"]+". Existing configuration and local overrides retained.")
def doctor(args,home):
 p=plan(args,home);issues=[]
 for e in p["entries"]:
  if not exists(Path(e["target"])):issues.append("not installed: "+e["component"])
  elif e["action"]!="unchanged":issues.append("different source or generated configuration: "+e["component"])
 for comp in p["components"]:
  for dep in DEPS.get(comp,[]):
   executable={"neovim":"nvim","ripgrep":"rg"}.get(dep,dep)
   if not shutil.which(executable):issues.append("missing command: "+executable)
 for comp in p["components"]:
  if comp in CASKS:
   app={"ghostty":"Ghostty","hammerspoon":"Hammerspoon","karabiner":"Karabiner-Elements"}[comp]
   if sys.platform=="darwin" and not Path("/Applications/"+app+".app").exists():issues.append("missing app: "+app)
 link=command_link(home)
 if link["symlink"] and not link["resolves"]:issues.append("broken command link: "+link["path"]+" -> "+link["target"]+" (run mackit link from the installed App)")
 seen=set()
 for row in key_data():
  if row["component"] not in p["components"] or row.get("profile",p["profile"])!=p["profile"]:continue
  for mode in row["mode"].split(","):
   identity=(row["component"],mode,row["key"],row.get("condition","always"))
   if identity in seen:issues.append("duplicate declaration: "+" / ".join(identity[:3]))
   seen.add(identity)
 extra,extra_issues=local_rows(home);issues+=extra_issues
 issues+=conflicts([r for r in key_data() if r.get("profile",p["profile"])==p["profile"]]+extra,home)
 print(json.dumps({"ok":not issues,"profile":p["profile"],"issues":sorted(set(issues)),"note":"Checks managed sources, dependencies, declared key scope, and keys registered by apps (keys.d) or Keyboard Maestro; physical delivery, plugin defaults and undeclared app interception require runtime verification."},ensure_ascii=False,indent=2))
 return bool(issues)
def key_data():
 p=data_root()/"data/keys.json"
 return read(p,[])
def keys(args,home,payload):
 from mackit import gui
 try:root=gui.source_root(home,payload)
 except ValueError:root=payload  # a moved source still leaves the built-in catalog to search
 rows=gui.key_rows(home,payload,root)
 if args.conflicts_with:
  if not combo(args.conflicts_with):raise ValueError("Not a modifier combination: "+args.conflicts_with+" (e.g. ctrl+alt+h)")
  name=args.profile or read(paths(home)[0]/"profile.json",{}).get("profile","developer")
  found=clashes(args.conflicts_with,rows,name)
  if args.json:print(json.dumps({"ok":True,"key":args.conflicts_with,"profile":name,"clear":not found,"conflicts":found},ensure_ascii=False,indent=2));return
  for r in found:print(f'{r["component"]:12} {r.get("mode",""):8} {r["key"]:24} {r["description"]}  [{r["source"]}]')
  print(f"{len(found)} global keys already use {args.conflicts_with} ({name} preset).")
  return
 term=(args.query or "").lower()
 rows=[r for r in rows if (not args.component or r["component"]==args.component) and term in json.dumps(r,ensure_ascii=False).lower() and (not r.get("profile") or not args.profile or r["profile"]==args.profile)]
 if args.json:print(json.dumps({"ok":True,"count":len(rows),"rows":rows},ensure_ascii=False,indent=2));return
 for r in rows:print(f'{r["component"]:12} {r.get("mode",""):8} {r["key"]:24} {r["description"]}  [{r["source"]}]')
 print(f"{len(rows)} bindings. Includes apps registered in ~/.config/mackit/keys.d and active Keyboard Maestro hot keys; native plugin defaults and unregistered apps are outside this catalog.")

SOURCE_COMMANDS=("plan","apply","doctor","edit")
NOT_PREPARED="The configuration source is not prepared yet. Run mackit prepare (what the App's 预览 does) or mackit apply first."

def prepare_root(home,command):
 """The App's own CLI, and any CLI on an isolated --home, works on the source the App uses: the
 recorded install source, else ~/.local/share/mackit made from the built-in copy (so a sandbox never
 links to or writes into a source checkout or the signed bundle). Read commands plan against the
 built-in copy and report the root that prepare/apply will create; nothing else creates it."""
 global ROOT,READ_ROOT
 from mackit import gui
 recorded=read(paths(home)[0]/"profile.json",{}).get("source_root")
 if recorded and not gui.valid_root(Path(recorded)):
  if command in SOURCE_COMMANDS:
   raise ValueError("The recorded configuration source has moved: "+recorded+". Put it back (or restore the installation) first.")
  return  # status, restore and the rest still work
 try:root=gui.source_root(home,ROOT)
 except ValueError:
  if command in SOURCE_COMMANDS:raise
  return
 if gui.valid_root(root):ROOT=root
 else:READ_ROOT,ROOT=ROOT,root

def prepare_command(args,home,payload):
 """What the App's 预览 does first: resolve the configuration source and create it from the built-in copy."""
 from mackit import gui
 root=gui.source_root(home,payload);created=False
 if not gui.valid_root(root):
  _,state=paths(home)
  with locked(state):
   if not gui.valid_root(root):gui.ensure_source(root,payload);created=True
 value={"ok":True,"root":str(root),"created":created,"version":(root/"VERSION").read_text().strip()}
 emit(args,value,("Prepared " if created else "Already prepared: ")+str(root))

def require_source(home):
 """File and window writes need a prepared source, like the App's pages; say how to get one."""
 from mackit import gui
 root=gui.source_root(home,ROOT)
 if not gui.valid_root(root):raise ValueError(NOT_PREPARED)
 return root

def emit(args,value,text=None):
 """--json prints the stable object; otherwise a short human line (or the object when no text is given)."""
 if getattr(args,"json",False) or text is None:print(json.dumps(value,ensure_ascii=False,indent=2))
 else:print(text)

def read_text(source):
 return sys.stdin.read() if source=="-" else Path(source).expanduser().read_text()

def window_command(args,home):
 """The 窗口 page through the App's own bridge: same source resolution, validation, digest lock and backups."""
 from mackit import gui, window
 verb=args.window_command
 if verb=="status":
  w=gui.dispatch({"action":"windowSnapshot"},home)["window"]
  text=[f'yabai  {"running" if w["yabai"]["running"] else ("installed, stopped" if w["yabai"]["installed"] else "not installed")}  {w["yabai"]["version"]}',
        f'skhd   {"running" if w["skhd"]["running"] else ("installed, stopped" if w["skhd"]["installed"] else "not installed")}  {w["skhd"]["version"]}',
        "settings: "+(", ".join(f"{k}={v}" for k,v in w["settings"].items()) or "(yabai defaults)"),
        f'hotkeys: {len(w["hotkeys"])}  rules: {len(w["rules"])}  editable: {w["editable"]}  digest: {w["digest"]}']
  return emit(args,{"ok":True,"window":w},"\n".join(text))
 require_source(home)
 if verb=="service":
  result=gui.dispatch({"action":"windowService","service":args.service,"start":args.state=="start"},home)
  return emit(args,{"ok":True,**result},result["message"])
 current,digest=gui.window_saved(home)
 if verb=="save":
  data=json.loads(read_text(args.source))
  data=data.get("window",data) if isinstance(data,dict) else None
  if not isinstance(data,dict):raise ValueError("Expected a JSON object with settings, rules and hotkeys (the window object of mackit window status --json).")
  wanted=args.digest or data.get("digest")
  if not wanted:raise ValueError("Pass --digest from mackit window status --json so a newer change is not overwritten.")
  request={"settings":data.get("settings",{}),"rules":data.get("rules",[]),"hotkeys":data.get("hotkeys",[])}
  if not isinstance(request["settings"],dict) or not all(isinstance(x,list) and all(isinstance(i,dict) for i in x) for x in (request["rules"],request["hotkeys"])):
   raise ValueError("settings must be an object; rules and hotkeys must be lists of objects.")
 else:
  wanted=args.digest or digest
  request={"settings":dict(current["settings"]),"rules":[dict(r) for r in current["rules"]],"hotkeys":[dict(h) for h in current["hotkeys"]]}
  warn=[]
  if verb=="set":
   for pair in args.values:
    key,sep,value=pair.partition("=")
    if not sep or not key:raise ValueError("Use key=value, e.g. window_gap=8")
    request["settings"][key.strip()]=value.strip()
   for key in args.unset or []:request["settings"].pop(key,None)
   if not args.values and not args.unset:raise ValueError("Nothing to change: give key=value pairs or --unset KEY.")
  elif verb=="hotkey":
   key=window.canonical_key(args.key)
   same=[i for i,h in enumerate(request["hotkeys"]) if window.canonical_key(h["key"])==key]
   if args.hotkey_command=="remove":
    if not same:raise ValueError("No skhd hotkey on "+key)
    del request["hotkeys"][same[0]]
   else:
    if same and not args.replace:raise ValueError(key+" is already bound; pass --replace to re-bind it.")
    row={"key":key,**({"action":args.action} if args.action else {"command":args.shell_command})}
    if args.note:row["note"]=args.note
    if same:request["hotkeys"][same[0]]=row
    else:request["hotkeys"].append(row)
    rows=gui.key_rows(home,ROOT,gui.source_root(home,ROOT))  # the rows the 窗口 page warns from
    name=read(paths(home)[0]/"profile.json",{}).get("profile","developer")
    warn=[{k:r.get(k) for k in ("component","mode","key","description","source")} for r in clashes(key,rows,name)]
  elif verb=="rule":
   same=[i for i,r in enumerate(request["rules"]) if r.get("app")==args.app]
   if args.rule_command=="remove":
    if not same:raise ValueError("No app rule for "+args.app)
    del request["rules"][same[0]]
   else:
    if same and not args.replace:raise ValueError(args.app+" already has a rule; pass --replace to change it.")
    row={"app":args.app,**{k:getattr(args,k) for k in ("manage","sticky","space") if getattr(args,k) not in (None,"")}}
    if same:request["rules"][same[0]]=row
    else:request["rules"].append(row)
 result=gui.dispatch({"action":"windowSave","digest":wanted,"applyNow":bool(args.apply),**request},home)
 out={"ok":True,**result}
 if verb=="hotkey" and args.hotkey_command=="add":out["conflicts"]=warn
 note=result["message"]
 if verb=="hotkey" and args.hotkey_command=="add" and warn:note+="\nAlso held by: "+"; ".join(f'{r["component"]} ({r["description"]})' for r in warn)
 if args.apply and not result.get("applied"):note+="\nNot applied live: "+("isolated --home" if home.resolve()!=Path.home().resolve() else "yabai/skhd not running")+"."
 return emit(args,out,note)

def file_command(args,home):
 """The 配置文件 page: same ids, path guard, 1 MB limit, digest check, lock and editor-backups."""
 from mackit import gui
 if args.file_command=="list":
  listed=gui.file_list(home)
  return emit(args,{"ok":True,**listed},"\n".join(f'{f["id"]:16} {f["path"]}' for f in listed["files"]))
 require_source(home)
 if args.file_command=="read":
  result=gui.dispatch({"action":"readFile","file":args.id},home)
  if args.json:return emit(args,{"ok":True,**result})
  sys.stdout.write(result["content"]);return
 content=read_text(args.source)
 result=gui.dispatch({"action":"saveFile","file":args.id,"content":content,"digest":args.digest},home)
 out={"ok":True,**{k:v for k,v in result.items() if k!="content"},"bytes":len(content.encode())}
 emit(args,out,result["message"]+(" Backup: "+result["backup"] if result.get("backup") else ""))

def deps_command(args,home):
 from mackit import gui
 name,selected=selection(args,home)
 items=gui.dependencies(selected,home)
 missing=[d for d in items if not d["installed"]]
 if args.install:
  result=gui.install_dependencies(items,home)
  return emit(args,{"ok":True,"profile":name,**result,"dependencies":gui.dependencies(selected,home)},result["message"])
 if args.json or args.check:
  brew=shutil.which("brew") or ""
  value={"ok":not (args.check and missing),"profile":name,"components":selected,"brew":brew,"dependencies":items,"missing":[d["id"] for d in missing]}
  if not brew:value["brewInstaller"]="https://github.com/Homebrew/brew/releases/latest/download/Homebrew.pkg"
  emit(args,value,f'{len(items)-len(missing)} of {len(items)} installed'+(" · missing: "+", ".join(value["missing"]) if missing else ""))
  return 1 if args.check and missing else 0
 formula=sorted(set(x for c in selected for x in DEPS.get(c,[])))
 print("brew install python "+" ".join(formula))
 casks=[CASKS[c] for c in selected if c in CASKS]
 if casks:print("brew install --cask "+" ".join(casks))
 if "yabai" in selected:print("Optional window manager: install yabai/skhd from their official project instructions.")

def status_command(args,home,payload):
 config,state=paths(home)
 value={"ok":True,"installed":read(config/"profile.json",{}),"root":str(ROOT),"transactions":[read(p) for p in sorted((state/"transactions").glob("*.json"))]}
 from mackit import gui
 try:
  inv=gui.inventory(home,payload,gui.source_root(home,payload))
  inv["keyCount"]=len(inv.pop("keys"))
  value["app"]=inv
 except (ValueError,OSError) as exc:value["app"]={"error":str(exc)}
 value["commandLink"]=command_link(home)
 print(json.dumps(value,ensure_ascii=False,indent=2))

def main(argv=None):
 global ROOT,READ_ROOT
 payload=ROOT;READ_ROOT=None
 try:return run(argv,payload)
 finally:ROOT,READ_ROOT=payload,None  # one command per call; the next call starts from the App's payload again
def run(argv,payload):
 parser=argparse.ArgumentParser(prog="mackit",description="Mac configuration you can find, understand and restore. Every command works on the same files as the MacKit App; --json gives a stable object with \"ok\", and failures exit non-zero.")
 parser.add_argument("--home",type=Path,default=Path.home(),help="Target HOME (default: yours). Any other folder is a sandbox: its configuration source is prepared inside it (<HOME>/.local/share/mackit), and nothing outside it is written, installed or started")
 parser.add_argument("--version",action="version",version=(ROOT/"VERSION").read_text().strip())
 subs=parser.add_subparsers(dest="command",required=True,metavar="COMMAND")
 def selector(s):s.add_argument("--profile",choices=["developer","tianli"],help="Preset (default: the installed one, else developer)");s.add_argument("--components",help="Comma-separated component names")
 s=subs.add_parser("prepare",help="Create the configuration source the App uses, as its 预览 does (no-op when ready)")
 s.add_argument("--json",action="store_true",help="Machine-readable result")
 s=subs.add_parser("plan",help="Preview what apply would link, back up or generate (read-only)");selector(s)
 s.add_argument("--json",action="store_true",help="Machine-readable plan, including the token apply --token checks")
 s=subs.add_parser("apply",help="Back up and install the selected configuration as one restorable transaction");selector(s)
 s.add_argument("--token",help="Refuse unless the plan still matches this plan --json token");s.add_argument("--json",action="store_true",help="JSON result (the default output)")
 s=subs.add_parser("doctor",help="Check sources, dependencies, the command link and key conflicts (exit 1 on issues)");selector(s)
 s.add_argument("--json",action="store_true",help="JSON result (the default output)")
 s=subs.add_parser("deps",help="Software each component needs: brew lines, --json state, or --install the missing ones");selector(s)
 s.add_argument("--json",action="store_true",help="Installed state per formula/cask");s.add_argument("--check",action="store_true",help="Exit 1 when anything is missing")
 s.add_argument("--install",action="store_true",help="brew install only what is missing (real HOME only; runs until done, progress on stderr)")
 s=subs.add_parser("status",help="Installed preset, source, App and source versions, transactions, command link (JSON)")
 s.add_argument("--json",action="store_true",help="JSON result (the default output)")
 s=subs.add_parser("restore",help="Undo the newest active transaction");s.add_argument("transaction",nargs="?",help="Its id; required to match the newest one")
 s.add_argument("--json",action="store_true",help="Machine-readable result")
 s=subs.add_parser("link",help="Point ~/.local/bin/mackit at this copy of the command (recorded; mackit restore undoes it)")
 s.add_argument("--json",action="store_true",help="Machine-readable result")
 s=subs.add_parser("keys",help="Search the shortcut catalog, or check a candidate key for conflicts");s.add_argument("query",nargs="?")
 s.add_argument("--component",help="e.g. nvim, hammerspoon, initials, keyboard-maestro");s.add_argument("--profile",choices=["developer","tianli"]);s.add_argument("--json",action="store_true")
 s.add_argument("--conflicts-with",metavar="KEY",help="Global keys that already use KEY, as the 窗口 page warns (e.g. ctrl+alt+h)")
 s=subs.add_parser("menu",help="Current App menu commands: native search panel, read-only scan and exact-path execution")
 menus=s.add_subparsers(dest="menu_command",required=True,metavar="ACTION")
 for verb in ("status","show","scan","execute"):
  t=menus.add_parser(verb,help={"status":"Read native accessibility permission (no prompt)","show":"Open the native menu search panel", "scan":"Read all menu commands and current states without showing UI", "execute":"Execute a unique full menu path in the frontmost App"}[verb])
  t.add_argument("--json",action="store_true")
  if verb in ("scan","execute"):t.add_argument("--pid",type=int,help="Target App process; execute requires that App to be frontmost")
  if verb=="execute":t.add_argument("--path-json",required=True,help='Exact full path, e.g. ["View","Show Status Bar"]')
 s=subs.add_parser("file",help="List, read or write editable config files with digest checks and backups")
 f=s.add_subparsers(dest="file_command",required=True,metavar="ACTION")
 t=f.add_parser("list",help="Editable ids and paths");t.add_argument("--json",action="store_true")
 t=f.add_parser("read",help="Print a file (--json adds path and sha256 digest)");t.add_argument("id");t.add_argument("--json",action="store_true")
 t=f.add_parser("write",help="Replace a file after a digest check; the old copy goes to editor-backups")
 t.add_argument("id");t.add_argument("--digest",required=True,help="Digest from file read --json (\"absent\" for a new file)")
 t.add_argument("--from",dest="source",required=True,metavar="PATH",help="New content file, or - for stdin");t.add_argument("--json",action="store_true")
 s=subs.add_parser("window",help="yabai settings, skhd hotkeys, app rules and services (the App's 窗口 page)")
 w=s.add_subparsers(dest="window_command",required=True,metavar="ACTION")
 def saving(t):
  t.add_argument("--digest",help="Refuse if the saved settings changed since this digest (from window status --json)")
  t.add_argument("--apply",action="store_true",help="Also apply to the running yabai/skhd (real HOME only)");t.add_argument("--json",action="store_true")
 t=w.add_parser("status",help="Services, live values, saved settings/rules/hotkeys, actions, setting specs, digest");t.add_argument("--json",action="store_true")
 t=w.add_parser("save",help="Replace settings, rules and hotkeys from JSON and regenerate yabairc/skhdrc");saving(t)
 t.add_argument("--from",dest="source",default="-",metavar="PATH",help="JSON file with settings/rules/hotkeys, or - for stdin (default)")
 t=w.add_parser("set",help="Change yabai settings: key=value ...");t.add_argument("values",nargs="*",metavar="KEY=VALUE");t.add_argument("--unset",action="append",metavar="KEY",help="Remove a setting (back to the yabai default)");saving(t)
 t=w.add_parser("hotkey",help="Add, re-bind or remove an skhd hotkey")
 h=t.add_subparsers(dest="hotkey_command",required=True,metavar="ACTION")
 u=h.add_parser("add",help="Bind a key to a catalog action or a one-line command");u.add_argument("--key",required=True,help="e.g. ctrl+alt+h")
 g=u.add_mutually_exclusive_group(required=True);g.add_argument("--action",help="Catalog action id (see window status --json actions)");g.add_argument("--command",dest="shell_command",metavar="COMMAND",help="One-line shell command")
 u.add_argument("--note");u.add_argument("--replace",action="store_true",help="Re-bind a key that is already bound");saving(u)
 u=h.add_parser("remove",help="Remove the binding on a key");u.add_argument("--key",required=True);saving(u)
 t=w.add_parser("rule",help="Add, change or remove an app rule")
 r=t.add_subparsers(dest="rule_command",required=True,metavar="ACTION")
 u=r.add_parser("add",help="Rule for one app (by its display name)");u.add_argument("--app",required=True)
 u.add_argument("--manage",choices=["on","off"]);u.add_argument("--sticky",choices=["on","off"]);u.add_argument("--space",type=int,help="Desktop 1-16")
 u.add_argument("--replace",action="store_true",help="Change the app's existing rule");saving(u)
 u=r.add_parser("remove",help="Remove the app's rule");u.add_argument("--app",required=True);saving(u)
 t=w.add_parser("service",help="Start or stop yabai or skhd (real HOME only)");t.add_argument("state",choices=["start","stop"]);t.add_argument("service",choices=["yabai","skhd"]);t.add_argument("--json",action="store_true")
 s=subs.add_parser("edit",help="Open a config in $EDITOR, or list the ids (use file read/write when not interactive)");s.add_argument("component",nargs="?");s.add_argument("--print",dest="print_path",action="store_true",help="Print the path only")
 s.add_argument("--json",action="store_true",help="With no id: the list as JSON")
 s=subs.add_parser("action",help="Run an optional action configured in ~/.config/mackit/actions.json");s.add_argument("name");s.add_argument("args",nargs=argparse.REMAINDER)
 subs.add_parser("update",help="git pull --ff-only a clean source checkout")
 subs.add_parser("gui")  # the App's stdin JSON bridge; deliberately not listed
 args=parser.parse_args(argv);home=args.home.expanduser().absolute()
 try:
  if args.command=="gui":
   from mackit.gui import main as gui_main
   return gui_main(home)
  os.environ["PATH"]=tool_path()
  # These go through the App's bridge before any source switch, so they resolve the source exactly as the App does.
  if args.command=="window":return window_command(args,home) or 0
  if args.command=="file":return file_command(args,home) or 0
  if args.command=="prepare":return prepare_command(args,home,payload) or 0
  if args.command=="menu":
   from mackit import menu
   result=menu.command(args,home,payload)
   emit(args,result,json.dumps(result,ensure_ascii=False,indent=2));return 0
  if getattr(sys,"frozen",False) or isolated(home):prepare_root(home,args.command)
  if args.command=="plan":
   p=plan(args,home);p["token"]=plan_token(p);p["source_ready"]=READ_ROOT is None
   if args.json:print(json.dumps({"ok":True,**p},ensure_ascii=False,indent=2))
   else:
    print("MacKit · "+p["profile"]+"\nSource: "+p["root"]+("" if p["source_ready"] else " (mackit prepare or apply creates it from the built-in copy)")+"\n")
    for e in p["entries"]:
     print(f'{e["action"]:18} {e["component"]:12} {e["target"]}')
    print("\nAlso manages ~/.local/bin/mackit and profile metadata.\nPreview only. Run mackit apply to install with backups.")
  elif args.command=="apply":apply(args,home)
  elif args.command=="restore":restore(args,home)
  elif args.command=="link":
   result=relink(args,home,payload)
   emit(args,result,("Linked "+result["target"]+" -> "+result["source"]+". Undo: "+result["restore"]) if result["changed"] else result.get("message","Already linked."))
  elif args.command=="doctor":return int(doctor(args,home))
  elif args.command=="keys":keys(args,home,payload)
  elif args.command=="deps":return deps_command(args,home) or 0
  elif args.command=="action":
   hooks=read(paths(home)[0]/"actions.json",{})
   command=hooks.get(args.name)
   if not isinstance(command,list) or not command or not all(isinstance(x,str) for x in command):raise ValueError("Configure this optional action in ~/.config/mackit/actions.json: "+args.name)
   extra=args.args[1:] if args.args[:1]==["--"] else args.args
   return subprocess.call([os.path.expanduser(x) for x in command]+extra)
  elif args.command=="status":status_command(args,home,payload)
  elif args.command=="edit":
   files=edit_files(home,ROOT)
   if not args.component:
    if args.json:print(json.dumps({"ok":True,"files":files},ensure_ascii=False,indent=2))
    else:print("\n".join(f'{f["id"]:16} {f["path"]}' for f in files))
    return 0
   if args.component in GENERATED:raise ValueError(GENERATED[args.component])
   if args.component in LOCAL_EDIT:
    p=paths(home)[0]/LOCAL_EDIT[args.component]
    if not args.print_path:p.parent.mkdir(parents=True,exist_ok=True);p.touch(exist_ok=True)
   else:
    if args.component not in EDIT:raise ValueError("Unknown config. Run mackit edit to list.")
    if READ_ROOT:raise ValueError(NOT_PREPARED)
    p=ROOT/"components"/EDIT[args.component]
   if args.print_path:print(p)
   else:return subprocess.call(shlex.split(os.environ.get("EDITOR","nvim"))+[str(p)])
  elif args.command=="update":
   if isolated(home):raise ValueError("update pulls the source checkout; run it without --home.")
   if not (ROOT/".git").exists():raise ValueError("Release archive: install the new release and apply it; existing configuration is backed up.")
   if subprocess.check_output(["git","-C",str(ROOT),"status","--porcelain"],text=True).strip():raise ValueError("Working tree has edits. Commit or preserve them before update.")
   subprocess.run(["git","-C",str(ROOT),"pull","--ff-only"],check=True)
   print("Updated source. Review mackit plan, then mackit apply.")
  return 0
 except (ValueError,TypeError,OSError,subprocess.SubprocessError) as exc:  # TypeError: JSON input of the wrong shape
  if getattr(args,"json",False):print(json.dumps({"ok":False,"error":str(exc)},ensure_ascii=False))
  print("mackit: "+str(exc),file=sys.stderr);return 1
if __name__=="__main__":raise SystemExit(main())
