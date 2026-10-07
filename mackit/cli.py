"""MacKit CLI: inspectable plans, reversible installs, native config sources."""
from __future__ import annotations
import argparse, contextlib, fcntl, hashlib, json, os, plistlib, shlex, shutil, subprocess, sys, tempfile, time, uuid
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
def bundle_build():
 """CFBundleVersion of the App this command ships in (what its 配置与更新 window shows); "" from a source checkout."""
 exe=bundled_cli();app=next((p for p in exe.parents if p.suffix==".app"),None) if exe else None
 try:return str(plistlib.loads((app/"Contents/Info.plist").read_bytes()).get("CFBundleVersion","")) if app else ""
 except (OSError,ValueError,TypeError,AttributeError):return ""
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
  before=None
  if "karabiner" in p["components"] and not isolated(home):  # what Karabiner's log says before the link moves
   from mackit import karabiner
   before=karabiner.loaded(home/".config/karabiner")
  link_entries(home,state,tx,record,entries,generation)
 result={"ok":True,"transaction":tx,"changed":len(record["operations"]),"profile":p["profile"],"restore":"mackit restore "+tx}
 if "karabiner" in p["components"]:result["karabiner"]=karabiner_reload(home,state,tx,record["operations"],before)
 print(json.dumps(result,ensure_ascii=False))
def karabiner_reload(home,state,tx,operations,before=None):
 """After apply: have the running Karabiner hold the active file, and say how that is known (karabiner.reload).
 A new log line is only looked for when the file changed after Karabiner's last logged load. An isolated
 --home never reaches Karabiner: "unchanged" when nothing was re-pointed there, else "isolated_home"."""
 from mackit import karabiner
 skipped={"attempted":False,"reloaded":False,"current":None,"expected":None,"nudged":[],"waited_ms":0,"log":str(karabiner.LOG),"line":""}
 if isolated(home):
  return {**skipped,"reason":"isolated_home" if any(Path(op["target"])==home/".config/karabiner" for op in operations) else "unchanged"}
 return karabiner.reload(state,skip=tx,link=home/".config/karabiner",before=before)
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

def karabiner_source(home):
 """The Karabiner source file the 配置文件 page edits (the built-in copy until a source is prepared)."""
 from mackit import gui
 root=gui.source_root(home,ROOT);ready=gui.valid_root(root)
 path=(root if ready else ROOT)/"components"/EDIT["karabiner"]
 raw=path.read_bytes()
 return path,raw.decode("utf-8"),hashlib.sha256(raw).hexdigest(),ready and gui.writable(root,home)

def karabiner_command(args,home):
 """Karabiner rules: read, add, remove, enable, disable. Saves go through the 配置文件 page's own save for the id
 karabiner (path guard, digest check, lock, editor-backups); --apply then runs the same apply as the App."""
 from mackit import gui, karabiner
 verb=args.karabiner_command
 if verb=="reload":
  if isolated(home):raise Failure("An isolated --home never touches the running Karabiner.",code="isolated_home")
  result=karabiner.reload(paths(home)[1],link=home/".config/karabiner")
  if not (result["reloaded"] or result["current"]):
   unseen="no new \""+karabiner.MARK+"\" line appeared in "+result["log"]+" within the wait"
   why={"not_installed":"Karabiner-Elements is not installed.","not_running":"Karabiner is not running.","no_generation":"No applied Karabiner configuration yet (mackit apply --components karabiner).",
    "log_unreadable":"Asked Karabiner to re-read, but "+result["log"]+" cannot be read to confirm it.",
    "not_confirmed":("The active configuration changed after Karabiner's last logged load, it was asked to re-read, and "+unseen+": it should have re-read and did not."
     if result["expected"] else "Asked Karabiner to re-read and "+unseen+". The log holds no earlier load to compare with, so this cannot tell \"already current\" from \"did not re-read\".")}[result["reason"]]
   raise Failure(why,code=result["reason"],reload=result)
  return emit(args,{"ok":True,"reload":result},("Karabiner re-read its configuration: " if result["reloaded"] else
   "Nothing to re-read: Karabiner's log already shows a load after the active file last changed: ")+result["line"])
 path,text,digest,editable=karabiner_source(home)
 data=karabiner.parse(text);profile=karabiner.profile_of(data);rules=karabiner.rules_of(profile)
 if verb=="status":
  link=home/".config/karabiner";_,state=paths(home)
  value={"installed":karabiner.installed(),"running":karabiner.running(),"source":str(path),"editable":editable,"digest":digest,
   "profile":str(profile.get("name","")),"rules":len(rules),"enabled":sum(karabiner.enabled(r) for r in rules),
   "simpleModifications":len(profile.get("simple_modifications") or []),"shellCommands":sum(karabiner.has_command(r) for r in rules),
   "config":{"path":str(link),"target":os.readlink(link) if link.is_symlink() else "","managed":link.is_symlink() and link.resolve().is_relative_to((state/"generations").resolve())},
   "lastReload":karabiner.last_reload()}
  # Has the running Karabiner loaded the active file since it last changed? (not asked of a sandbox: it is not what Karabiner reads)
  seen=karabiner.loaded(link) if not isolated(home) else {"current":None,"changedAt":"","loadedAt":""}
  value["loaded"]={k:seen[k] for k in ("current","changedAt","loadedAt")}
  return emit(args,{"ok":True,"karabiner":value},"\n".join([
   "Karabiner  "+("running" if value["running"] else ("installed, stopped" if value["installed"] else "not installed")),
   f'rules: {value["rules"]} ({value["enabled"]} enabled)  simple: {value["simpleModifications"]}  editable: {editable}  digest: {digest}',
   "source: "+str(path),"active:  "+(value["config"]["target"] or "(not installed by MacKit)"),"last re-read: "+(value["lastReload"] or "(none in the log)"),
   "active file loaded since it last changed: "+{True:"yes",False:"no (run mackit karabiner reload)",None:"unknown"}[value["loaded"]["current"]]]))
 verb=args.rule_command
 if verb=="list":
  rows=[karabiner.summary(r,i+1) for i,r in enumerate(rules)]
  return emit(args,{"ok":True,"source":str(path),"digest":digest,"profile":str(profile.get("name","")),"count":len(rows),"rules":rows},
   "\n".join(f'{r["index"]:>3} {"on " if r["enabled"] else "off"} {r["description"]}  [{", ".join(r["from"])}]' for r in rows) or "No rules.")
 if verb=="show":
  at=karabiner.find(rules,args.index,args.description)
  if args.json:return emit(args,{"ok":True,"source":str(path),"digest":digest,**karabiner.summary(rules[at],at+1),"rule":rules[at]})
  print(json.dumps(rules[at],ensure_ascii=False,indent=2));return
 require_source(home)
 if args.digest and args.digest!=digest:raise Failure("karabiner.json changed since that digest. Run mackit karabiner rule list --json again and pass the new one.",code="stale_digest")
 replaced=False;changed=True
 if verb=="add":
  at,replaced=karabiner.add(rules,json.loads(read_text(args.source)),args.at,args.replace)
  note=("Replaced" if replaced else "Added")+f' rule {at+1}: {rules[at]["description"]}'
 else:
  at=karabiner.find(rules,args.index,args.description);name=str(rules[at].get("description",""))
  if verb=="remove":del rules[at];note=f"Removed rule {at+1}: {name}"
  else:
   changed=karabiner.set_enabled(rules,at,verb=="enable")
   note=(f"Rule {at+1} is now {verb}d: " if changed else f"Rule {at+1} was already {verb}d: ")+name
 out={"ok":True,"action":verb,"changed":changed,"replaced":replaced,"index":at+1,"description":name if verb!="add" else rules[at]["description"],
  "count":len(rules),"path":str(path),"digest":digest,"backup":"","applied":False}
 if changed:
  saved=gui.dispatch({"action":"saveFile","file":"karabiner","content":karabiner.render(data),"digest":digest},home)
  out.update(digest=saved["digest"],backup=saved.get("backup",""))
  if out["backup"]:note+="\nBackup: "+out["backup"]
 if args.apply:
  if "karabiner" not in read(paths(home)[0]/"profile.json",{}).get("components",[]):
   out["applyNote"]="The karabiner component is not installed here; run mackit apply --components karabiner."
  else:
   if getattr(sys,"frozen",False) or isolated(home):prepare_root(home,"apply")
   printed,_=gui.capture(apply,argparse.Namespace(profile=None,components="karabiner",token=None),home)
   out["installation"]=json.loads(printed);out["applied"]=True
   reloaded=out["installation"].get("karabiner",{})
   why=" ("+str(reloaded.get("reason"))+")."
   out["applyNote"]="Applied as "+out["installation"]["transaction"]+"; Karabiner "+("re-read it." if reloaded.get("reloaded") else
    "already holds this content"+why if reloaded.get("current") else "was not asked to re-read"+why if not reloaded.get("attempted") else "re-read not confirmed"+why)
  note+="\n"+out["applyNote"]
 return emit(args,out,note)

def select_command(args,home):
 """The preset picker and component checkboxes of the 安装配置 page: remembered, nothing installed."""
 from mackit import gui
 if not args.profile and not args.components:raise Failure("Nothing to remember: pass --profile and/or --components.",code="nothing_to_change")
 saved=read(paths(home)[0]/"profile.json",{})
 if args.profile and saved.get("profile") and saved["profile"]!=args.profile:
  raise Failure("The installed preset ("+saved["profile"]+") is locked, as in the App; restore the installation before choosing another.",code="preset_locked")
 name,selected=selection(args,home)
 result=gui.save_portable_preferences({"profile":name,"components":selected},home)
 emit(args,{"ok":True,"profile":name,"components":sorted(selected),"message":result["message"]},f'Remembered {name}: '+", ".join(sorted(selected)))

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
 value["app"]["appBuild"]=bundle_build()
 value["commandLink"]=command_link(home)
 print(json.dumps(value,ensure_ascii=False,indent=2))

# `config …`, `update check` and `update install` are the items of the App's 配置与更新… window. They belong to the App
# itself (its preference domain, its version, its release channel, the bundle on disk), so the App executable runs
# them: the shared command layer macos/Sources/AppLifecycleCLI.swift, entered in MacKitMain.main before any window
# exists (Lifecycle.command). This command only forwards. The shared layer waits at most 30 seconds for one sync pass
# or one release lookup; an import with sync on does a write and a pass.
LIFECYCLE_SECONDS=60
# `update install` is the long one. The shared layer bounds each of its own steps (AppLifecycleCLI.Product: timeout 30 for
# the release lookup, upgradeTimeout 330 for the download and its verification, quitTimeout 20 for a running App to
# quit, upgradeTimeout 330 again for the replacement) and answers by itself when one of them runs out. The forwarding
# waits longer than all of them together, so that answer always arrives; it is a last resort, not the limit.
LIFECYCLE_INSTALL_SECONDS=30+330+20+330+40
# The shared layer's own help lines for `mackit` (AppLifecycleCLI.helpRead / helpWrite), verbatim.
# tests/test_lifecycle_cli.py looks each of them up in what the compiled App prints for `config --help`.
LIFECYCLE_READS=(
 "  config status              「使用 iCloud 记住配置」开关、开关下面那句同步状态、当前可迁移的配置项、App 是否在运行（只读）",
 "  update check               检查更新：当前版本、此渠道最新版本、有没有新版、怎么升级（只读；私有渠道读 iCloud Drive 里的发行记录，公开渠道联网读发行记录）")
LIFECYCLE_WRITES=(
 "  config export -o <file>        导出配置：与窗口「导出配置…」同一份文件；不改设置，只写你指定的那个文件（--force 覆盖；-o - 输出到标准输出，不写文件）",
 "  config import <file> --yes     导入配置：先备份原配置再覆盖，与窗口「导入配置…」相同",
 "  config sync on|off --yes       拨动「使用 iCloud 记住配置」（--dry-run 只看会不会变；用 mackit config status 回读）",
 "  update install --yes           升级到新版：与窗口「升级到新版…」同一条路——验证发行包与签名、替换当前 App，运行中的先退出、换好再重开；配置保留，替换失败回滚（--dry-run 只看会做什么；用 mackit update check 回读）")
def lifecycle_seconds(words):
 """How long the forwarding waits for the App executable. `words` is what lifecycle_words returned: --home, the
 home, then the command. Only `update install` gets the long wait."""
 return LIFECYCLE_INSTALL_SECONDS if [w for w in words[2:] if not w.startswith("-")][:2]==["update","install"] else LIFECYCLE_SECONDS
def lifecycle_words(given):
 """The words to hand to the App executable when it is the one that answers, else None: `config …`, or `update`
 followed by a word (`update check`, `update install`). Plain `mackit update` stays the source-checkout pull it always was. Only
 --home may come before the command. It is always passed on, as an absolute path: the App refuses a home that is
 not this Mac's own, so a sandbox (or a changed $HOME) never reaches the owner's switch or iCloud copy."""
 home=None;i=0
 while i<len(given):
  if given[i]=="--home" and i+1<len(given):home=given[i+1];i+=2
  elif given[i].startswith("--home="):home=given[i][len("--home="):];i+=1
  else:break
 rest=list(given[i:])
 if not rest or not (rest[0]=="config" or (rest[0]=="update" and any(not w.startswith("-") for w in rest[1:]))):return None
 return ["--home",str((Path(home).expanduser() if home is not None else Path.home()).absolute())]+rest
def lifecycle_binary():
 """The App executable that carries the shared command layer: the one of the bundle this command ships in. From a
 source checkout there is no bundle, and MACKIT_NATIVE may name a compiled App binary (the tests do); the App's
 own command ignores it."""
 if getattr(sys,"frozen",False):
  exe=bundled_cli();app=next((p for p in exe.parents if p.suffix==".app"),None) if exe else None
  try:binary=app/"Contents/MacOS"/plistlib.loads((app/"Contents/Info.plist").read_bytes())["CFBundleExecutable"]
  except (OSError,ValueError,KeyError,TypeError,AttributeError):return None
  return binary if binary.is_file() else None
 named=os.environ.get("MACKIT_NATIVE")
 return Path(named) if named and Path(named).is_file() else None
def relay(stream,data):
 """The child's bytes as they are; a text-only stream (in-process callers) gets them decoded."""
 raw=getattr(stream,"buffer",None)
 if raw is None:stream.write(data.decode("utf-8","replace"));return
 stream.flush();raw.write(data);raw.flush()
def lifecycle_failure(words,code,message):
 """The forwarding itself failed: the shared layer's failure shape, which otherwise passes through untouched."""
 if "--json" in words:
  rest=[w for w in words[2:] if not w.startswith("-")]
  print(json.dumps({"ok":False,"command":" ".join(rest[:2]),"error":{"code":code,"message":message}},ensure_ascii=False))
 print("mackit: "+message,file=sys.stderr);return 1
def lifecycle_command(words):
 """`mackit config …`, `mackit update check` and `mackit update install`: the words go to the App executable
 unchanged and its stdout, stderr and exit code come back unchanged; nothing is parsed or re-implemented here. No
 window is opened. A running MacKit follows config changes on its own (AppLifecycleCLI.follow); only
 `update install --yes` asks it to quit, as the window's own 升级到新版… does.

 `update install --yes` replaces the whole MacKit.app, and this command runs from inside it. Everything used after
 the App executable returns is already loaded before it starts (relay, json, the failure text): by then the files
 this process was started from have been moved to the Trash and the same paths hold the new version."""
 binary=lifecycle_binary()
 if binary is None:
  return lifecycle_failure(words,"app_missing","config, update check and update install are answered by the MacKit App itself, and this command is not inside a MacKit.app. Run the App's own command (MacKit.app/Contents/Resources/core/bin/mackit, linked as ~/.local/bin/mackit).")
 seconds=lifecycle_seconds(words)
 readback="mackit update check" if words[2:3]==["update"] else "mackit config status"
 try:done=subprocess.run([str(binary),*words],stdin=subprocess.DEVNULL,capture_output=True,timeout=seconds)
 except subprocess.TimeoutExpired:
  return lifecycle_failure(words,"timeout",f"No answer within {seconds} seconds; the App executable was stopped. Read the state back with {readback} before sending the command again.")
 except OSError as exc:
  return lifecycle_failure(words,"app_missing",f"Cannot run {binary}: {exc}")
 if done.returncode<0:
  return lifecycle_failure(words,"app_failed",f"The App executable was ended by signal {-done.returncode} and gave no result. Read the state back with {readback}.")
 relay(sys.stdout,done.stdout);relay(sys.stderr,done.stderr)
 return done.returncode

class Failure(ValueError):
 """A refused or unconfirmed operation with a stable code, and facts to report: they join the --json answer."""
 def __init__(self,message,code="refused",**extra):super().__init__(message);self.code=code;self.extra=extra
# Commands written under the shared convention answer {"error": {"code", "message"}}; the older ones keep the string their readers parse.
CODED_ERRORS=("karabiner","select")
def error_code(exc):
 if getattr(exc,"code",None):return exc.code
 if str(exc)==NOT_PREPARED:return "not_prepared"
 if isinstance(exc,json.JSONDecodeError):return "invalid_json"
 if isinstance(exc,subprocess.SubprocessError):return "subprocess_failed"
 return "io_error" if isinstance(exc,OSError) else "refused"
def first_command(argv):
 """The command word of an argument list (skips --home VALUE and other options)."""
 words=iter(argv)
 for word in words:
  if word=="--home":next(words,None)
  elif not word.startswith("-"):return word
 return ""
class Parser(argparse.ArgumentParser):
 """Usage errors keep argparse's stderr text and exit code 2; with --json they also print the error object."""
 json_errors=False;coded=False
 def error(self,message):
  if Parser.json_errors:print(json.dumps({"ok":False,"error":{"code":"usage","message":message} if Parser.coded else "usage: "+message},ensure_ascii=False))
  super().error(message)
HELP_EPILOG="""\
读命令 Read commands (write nothing):
  status · plan · doctor · deps (without --install) · keys · file list · file read · window status ·
  karabiner status · karabiner rule list · karabiner rule show · edit (no id, or --print)
  From the App's 配置与更新… window (the App itself answers; shapes and codes: mackit config --help):
@LIFECYCLE_READS@
写命令 Write commands:
  prepare · select · apply · restore · link · deps --install · file write ·
  window save · window set · window hotkey add|remove · window rule add|remove · window service ·
  karabiner rule add|remove|enable|disable · karabiner reload · action · update
  Saves check a digest (window status / file read / karabiner rule list --json), keep a copy of what
  they replace, and print where it is. apply and restore are one recorded transaction each.
  From the App's 配置与更新… window (sync, import and update install need --yes; import backs up what
  it replaces; update install replaces MacKit.app itself and can take minutes: --dry-run first):
@LIFECYCLE_WRITES@

--json 输出形状 Output: one object on stdout.
  success  {"ok": true, ...command fields...}
  failure  {"ok": false, "error": "<reason>"}   (usage errors: "usage: ...")
           karabiner and select: {"ok": false, "error": {"code": "<stable code>", "message": "<reason>"}}
           (codes: usage, not_found, exists, ambiguous, stale_digest, invalid_rule, shell_command,
           invalid_json, not_prepared, preset_locked, isolated_home, not_confirmed, not_running, ...;
           karabiner reload adds "reload")
           config, update check and update install (answered by the App): {"ok": false,
           "command": "<verb sub>", "error": {"code", "message"}} (codes: usage,
           confirmation_required, file_exists, not_found, import_rejected, export_failed,
           sync_incomplete, check_incomplete, no_settings, failed; update install adds manual_install,
           needs_product_installer, upgrade_failed, app_busy, replace_failed, cleanup_failed;
           MacKit's own: isolated_home, isolation_incomplete; when the forwarding itself fails:
           app_missing, app_failed, timeout)
  config status: has_settings, sync_enabled, sync_status {text, at, from, live}, keys, app_running,
    problem. sync_status is the sentence under the window's switch; from is app (the running App
    shows it now, live true), record (the App is not running: the last pass left it, at says when)
    or derived (no usable record: what a window shows before its first pass).
  update install: installed, state (installed | up_to_date | ahead_of_channel), message, current,
    latest, source, app_running; once installed also previous, backup (null), old_app_cleanup
    (trashed: the replaced App is in the Trash), relaunched; --dry-run gives would_install {from, to},
    installation, will_quit_app, will_relaunch and installs nothing.
  status, apply and doctor print JSON without the flag. status: installed, transactions, commandLink,
  app.selected, app.appVersion, app.appBuild (the build number the App's own window shows).
  apply with karabiner selected adds "karabiner": {reloaded, current, expected, reason, nudged, line}:
    reloaded            a re-read line newer than this change is in Karabiner's log
    already_current     the log already shows a load after the active file last changed; no new line
                        is expected and nothing is renamed (content_unchanged: re-pointed, same bytes)
    not_confirmed       expected true: the file changed after the last logged load and no line came
                        (it should have re-read and did not); expected null: no earlier line to compare

退出码 Exit codes:
  0  success (an empty search or list is still success; karabiner reload with nothing to re-read)
  1  the operation failed or was refused: stale digest, failed validation, doctor found issues,
     deps --check found something missing, karabiner reload not confirmed. apply and --apply still
     exit 0 when the install itself worked: read karabiner.reloaded / karabiner.current / reason.
  2  usage error (unknown command or argument)
     also config import / config sync / update install without --yes (confirmation_required), and
     config export onto an existing file without --force (file_exists)
     update install exits 0 when there is nothing newer (installed false); 1 with one of its codes
     above when it did not finish (the current App is kept or rolled back; cleanup_failed: the new
     version is in place, the old bundle could not be moved to the Trash).
  action returns the configured program's own exit code.

仅在窗口中 Window only (no command; the facts are in the read commands):
  switch pages (sidebar, ⌘1-⌘5)
  toolbar 使用帮助 and menu 打开在线手册 (open web pages)
  Homebrew website and Karabiner installer links
  install Homebrew with the system installer (administrator password; URL: deps --json)
  open Accessibility / Input Monitoring settings (only a person can grant them)
  click a shortcut's source (GitHub page or Finder; the path is in keys --json)
  show a config file in Finder (path: file list)
  open the backup folder (~/.local/state/mackit; status lists the transactions)
  record a key by pressing it (pass --key instead)
  discard an unsaved draft, and the unsaved-changes prompt on quit (commands hold no draft)
  the 操作进行中 prompt when quitting during an operation (a command runs to its own exit)
  the progress bar and the success / error banners (a command prints its result and exit code)
  menu 配置与更新… (opens that window; its items are config … and update check / update install above)

Without --home, commands act on this Mac and its recorded configuration source. Try writes on a
sandbox first: mackit --home /tmp/demo prepare
config, update check and update install act on the App itself (its preference domain, its iCloud
copy, its release channel, the installed MacKit.app): a sandbox --home has none of these. config and
update install answer isolated_home there and touch nothing; update check still reads the channel.
"""
HELP_EPILOG=HELP_EPILOG.replace("@LIFECYCLE_READS@","\n".join(LIFECYCLE_READS)).replace("@LIFECYCLE_WRITES@","\n".join(LIFECYCLE_WRITES))
def main(argv=None):
 global ROOT,READ_ROOT
 payload=ROOT;READ_ROOT=None
 try:return run(argv,payload)
 finally:ROOT,READ_ROOT=payload,None  # one command per call; the next call starts from the App's payload again
def run(argv,payload):
 given=sys.argv[1:] if argv is None else argv
 forwarded=lifecycle_words(given)
 if forwarded is not None:return lifecycle_command(forwarded)
 Parser.json_errors="--json" in given;Parser.coded=first_command(given) in CODED_ERRORS
 parser=Parser(prog="mackit",formatter_class=argparse.RawDescriptionHelpFormatter,epilog=HELP_EPILOG,description="Mac configuration you can find, understand and restore. Every command works on the same files as the MacKit App; --json gives a stable object with \"ok\", and failures exit non-zero.")
 parser.add_argument("--home",type=Path,default=Path.home(),help="Target HOME (default: yours). Any other folder is a sandbox: its configuration source is prepared inside it (<HOME>/.local/share/mackit), and nothing outside it is written, installed or started")
 parser.add_argument("--version",action="version",version=(ROOT/"VERSION").read_text().strip())
 subs=parser.add_subparsers(dest="command",required=True,metavar="COMMAND")
 def selector(s):s.add_argument("--profile",choices=["developer","tianli"],help="Preset (default: the installed one, else developer)");s.add_argument("--components",help="Comma-separated component names")
 s=subs.add_parser("prepare",help="Create the configuration source the App uses, as its 预览 does (no-op when ready)")
 s.add_argument("--json",action="store_true",help="Machine-readable result")
 s=subs.add_parser("select",help="Remember the preset and components the App's 安装配置 page shows (installs nothing)");selector(s)
 s.add_argument("--json",action="store_true",help="Machine-readable result")
 s=subs.add_parser("plan",help="Preview what apply would link, back up or generate (read-only)");selector(s)
 s.add_argument("--json",action="store_true",help="Machine-readable plan, including the token apply --token checks")
 s=subs.add_parser("apply",help="Back up and install the selected configuration as one restorable transaction; a running Karabiner is told to re-read when its file changed, and its log is checked (result: karabiner)");selector(s)
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
 s=subs.add_parser("karabiner",help="Karabiner key-to-key rules: status, rule list/show/add/remove/enable/disable, reload")
 k=s.add_subparsers(dest="karabiner_command",required=True,metavar="ACTION")
 t=k.add_parser("status",help="Installed/running, source file and digest, rule counts, active generation, last re-read, and whether the active file was loaded since it last changed (read-only)");t.add_argument("--json",action="store_true")
 t=k.add_parser("reload",help="Have the running Karabiner hold the active file: nothing is done when its log already shows a load after the file last changed; otherwise it is told to re-read and the log is checked (exit 1 when that is not confirmed; real HOME only)");t.add_argument("--json",action="store_true")
 t=k.add_parser("rule",help="List, show, add, remove, enable or disable a rule in components/karabiner/karabiner.json")
 r=t.add_subparsers(dest="rule_command",required=True,metavar="ACTION")
 def which(u):
  g=u.add_mutually_exclusive_group(required=True);g.add_argument("--index",type=int,help="Its number in rule list (from 1)");g.add_argument("--description",help="Its exact description")
 def writing(u):
  u.add_argument("--digest",help="Refuse if karabiner.json changed since this digest (from rule list --json)")
  u.add_argument("--apply",action="store_true",help="Also run apply for the karabiner component; on your own HOME a running Karabiner is then told to re-read");u.add_argument("--json",action="store_true")
 u=r.add_parser("list",help="Every rule: number, on/off, description, the keys it starts from");u.add_argument("--json",action="store_true")
 u=r.add_parser("show",help="One rule as JSON");which(u);u.add_argument("--json",action="store_true",help="Wrap it with index, enabled and the file digest")
 u=r.add_parser("add",help="Add one rule object (description + manipulators); a rule with shell_command is refused")
 u.add_argument("--from",dest="source",default="-",metavar="PATH",help="JSON file with the rule, or - for stdin (default)")
 u.add_argument("--at",type=int,help="Insert before this number (default: append; earlier rules win)");u.add_argument("--replace",action="store_true",help="Replace the rule that has the same description");writing(u)
 u=r.add_parser("remove",help="Delete a rule");which(u);writing(u)
 u=r.add_parser("enable",help="Turn a rule on");which(u);writing(u)
 u=r.add_parser("disable",help="Turn a rule off, keeping it in the file");which(u);writing(u)
 s=subs.add_parser("edit",help="Open a config in $EDITOR, or list the ids (use file read/write when not interactive)");s.add_argument("component",nargs="?");s.add_argument("--print",dest="print_path",action="store_true",help="Print the path only")
 s.add_argument("--json",action="store_true",help="With no id: the list as JSON")
 s=subs.add_parser("action",help="Run an optional action configured in ~/.config/mackit/actions.json");s.add_argument("name");s.add_argument("args",nargs=argparse.REMAINDER)
 subs.add_parser("update",help="git pull --ff-only a clean source checkout; update check asks the App's release channel for a newer version (read-only); update install --yes upgrades the installed App to it",
  epilog="mackit update check [--json] is answered by the App: current and latest version, whether there is a newer one, how to upgrade. mackit update install --yes [--dry-run] [--json] is the window's 升级到新版…: it verifies the release and its signature, replaces MacKit.app (a running one quits first and is reopened), keeps the configuration and rolls back when the replacement fails. See mackit config --help.")
 s=subs.add_parser("config",help="The App's 配置与更新… window as commands: status (with the sync status sentence), export, import, sync on|off (answered by the App; mackit config --help)")
 s.add_argument("words",nargs=argparse.REMAINDER)
 subs.add_parser("gui")  # the App's stdin JSON bridge; deliberately not listed
 args=parser.parse_args(argv);home=args.home.expanduser().absolute()
 try:
  if args.command=="gui":
   from mackit.gui import main as gui_main
   return gui_main(home)
  if args.command=="config":return lifecycle_command(["--home",str(home),"config",*args.words])
  os.environ["PATH"]=tool_path()
  # These go through the App's bridge before any source switch, so they resolve the source exactly as the App does.
  if args.command=="window":return window_command(args,home) or 0
  if args.command=="file":return file_command(args,home) or 0
  if args.command=="prepare":return prepare_command(args,home,payload) or 0
  if args.command=="karabiner":return karabiner_command(args,home) or 0
  if args.command=="select":return select_command(args,home) or 0
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
  if getattr(args,"json",False):
   error={"code":error_code(exc),"message":str(exc)} if args.command in CODED_ERRORS else str(exc)
   print(json.dumps({"ok":False,"error":error,**getattr(exc,"extra",{})},ensure_ascii=False))
  print("mackit: "+str(exc),file=sys.stderr);return 1
if __name__=="__main__":raise SystemExit(main())
