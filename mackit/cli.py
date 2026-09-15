"""MacKit CLI: inspectable plans, reversible installs, native config sources."""
from __future__ import annotations
import argparse, contextlib, fcntl, hashlib, json, os, shlex, shutil, subprocess, sys, tempfile, time, uuid
from pathlib import Path

ROOT = Path(sys.executable).resolve().parents[1] if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]
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
 "karabiner": "karabiner/karabiner.json", "yabai": "yabai/config/yabairc",
 "ghostty-keys": "ghostty/keymaps.conf",
 "btop": "btop/btop.conf", "fd": "fd/ignore", "glow": "glow/glow.yml",
}
DEPS = {"zsh":["fzf","fd","ripgrep","zoxide","atuin","starship","eza"], "nvim":["neovim","git","ripgrep","fd"],
 "tmux":["tmux"],"yazi":["yazi"],"lazygit":["lazygit"],"atuin":["atuin"],"starship":["starship"],
 "btop":["btop"],"fd":["fd"],"glow":["glow"]}
CASKS = {"ghostty":"ghostty","hammerspoon":"hammerspoon","karabiner":"karabiner-elements"}
def dump(path, data):
 path.parent.mkdir(parents=True, exist_ok=True)
 tmp=path.with_name(path.name+".tmp-"+uuid.uuid4().hex)
 tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")
 tmp.chmod(0o600);tmp.replace(path)
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
@contextlib.contextmanager
def locked(state):
 state.mkdir(parents=True,exist_ok=True)
 with (state/"lock").open("a") as f:
  fcntl.flock(f,fcntl.LOCK_EX)
  yield
def profile(name):
 return read(ROOT/"profiles"/(name+".json"))
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
   if not src.startswith("generated:") and not source.exists(): raise ValueError("Missing source: "+str(source))
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
def write_generated(generation,home,p):
 generation.mkdir(parents=True,exist_ok=True)
 z= "export MACKIT_ROOT="+shlex.quote(str(ROOT))+"\nsource "+shlex.quote(str(ROOT/"components/zsh/zshrc"))+"\n"
 (generation/"zshrc").write_text(z)
 dump(generation/"profile.json",{"profile":p["profile"],"components":p.get("installed_components",p["components"]),"version":(ROOT/"VERSION").read_text().strip(),"source_root":str(ROOT)})
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
 keyboard=read(ROOT/"components/karabiner/karabiner.json")
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
def apply(args,home):
 config,state=paths(home)
 with locked(state):
  for receipt in (state/"transactions").glob("*.json"):
   if read(receipt).get("status")=="installing":
    raise ValueError("Interrupted installation found. Run mackit restore before applying again.")
  p=plan(args,home)
  saved=read(config/"profile.json",{})
  if saved.get("profile") and saved["profile"]!=p["profile"]:
   raise ValueError("Restore the current preset before switching profiles; this also restores its global keyboard rules.")
  tx=time.strftime("%Y%m%d-%H%M%S")+"-"+uuid.uuid4().hex[:6]
  generation=state/"generations"/tx
  write_generated(generation,home,p)
  entries=p["entries"]+[
   {"source":str(generation/"profile.json"),"target":str(config/"profile.json")},
   {"source":str(generation/"profile.zsh"),"target":str(config/"profile.zsh")},
   {"source":str(generation/"mackit"),"target":str(home/".local/bin/mackit")}]
  record={"id":tx,"status":"installing","profile":p["profile"],"components":p["components"],"operations":[]}
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
  print(json.dumps({"transaction":tx,"changed":len(record["operations"]),"profile":p["profile"],"restore":"mackit restore "+tx},ensure_ascii=False))
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
  print("Restored "+r["id"]+". Existing configuration and local overrides retained.")
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
 seen=set()
 for row in key_data():
  if row["component"] not in p["components"] or row.get("profile",p["profile"])!=p["profile"]:continue
  for mode in row["mode"].split(","):
   identity=(row["component"],mode,row["key"],row.get("condition","always"))
   if identity in seen:issues.append("duplicate declaration: "+" / ".join(identity[:3]))
   seen.add(identity)
 print(json.dumps({"profile":p["profile"],"issues":sorted(set(issues)),"note":"Checks managed sources, dependencies and declared key scope; physical delivery, plugin defaults and external app interception require runtime verification."},ensure_ascii=False,indent=2))
 return bool(issues)
def key_data():
 p=ROOT/"data/keys.json"
 return read(p,[])
def keys(args):
 rows=key_data();term=(args.query or "").lower()
 rows=[r for r in rows if (not args.component or r["component"]==args.component) and term in json.dumps(r,ensure_ascii=False).lower() and (not r.get("profile") or not args.profile or r["profile"]==args.profile)]
 if args.json:print(json.dumps(rows,ensure_ascii=False,indent=2));return
 for r in rows:print(f'{r["component"]:12} {r.get("mode",""):8} {r["key"]:24} {r["description"]}  [{r["source"]}]')
 print(f"{len(rows)} bindings. Native plugin defaults and external application shortcuts are outside this catalog.")
def main(argv=None):
 parser=argparse.ArgumentParser(prog="mackit",description="Mac configuration you can find, understand and restore.")
 parser.add_argument("--home",type=Path,default=Path.home(),help="Target HOME (isolated validation supported)")
 parser.add_argument("--version",action="version",version=(ROOT/"VERSION").read_text().strip())
 subs=parser.add_subparsers(dest="command",required=True)
 for name in ["plan","apply","doctor","deps"]:
  s=subs.add_parser(name);s.add_argument("--profile",choices=["developer","tianli"]);s.add_argument("--components",help="Comma-separated component names")
  if name=="plan":s.add_argument("--json",action="store_true",help="Machine-readable plan")
 subs.add_parser("status")
 s=subs.add_parser("restore");s.add_argument("transaction",nargs="?")
 s=subs.add_parser("edit");s.add_argument("component",nargs="?");s.add_argument("--print",dest="print_path",action="store_true")
 s=subs.add_parser("action");s.add_argument("name");s.add_argument("args",nargs=argparse.REMAINDER)
 s=subs.add_parser("keys");s.add_argument("query",nargs="?");s.add_argument("--component",choices=list(COMPONENTS));s.add_argument("--profile",choices=["developer","tianli"]);s.add_argument("--json",action="store_true")
 subs.add_parser("update")
 subs.add_parser("gui",help=argparse.SUPPRESS)
 args=parser.parse_args(argv);home=args.home.expanduser().absolute()
 try:
  if args.command=="gui":
   from mackit.gui import main as gui_main
   return gui_main(home)
  if args.command=="plan":
   p=plan(args,home)
   if args.json:print(json.dumps(p,ensure_ascii=False,indent=2))
   else:
    print("MacKit · "+p["profile"]+"\nSource: "+p["root"]+"\n")
    for e in p["entries"]:
     print(f'{e["action"]:18} {e["component"]:12} {e["target"]}')
    print("\nAlso manages ~/.local/bin/mackit and profile metadata.\nPreview only. Run mackit apply to install with backups.")
  elif args.command=="apply":apply(args,home)
  elif args.command=="restore":restore(args,home)
  elif args.command=="doctor":return int(doctor(args,home))
  elif args.command=="keys":keys(args)
  elif args.command=="action":
   hooks=read(paths(home)[0]/"actions.json",{})
   command=hooks.get(args.name)
   if not isinstance(command,list) or not command or not all(isinstance(x,str) for x in command):raise ValueError("Configure this optional action in ~/.config/mackit/actions.json: "+args.name)
   extra=args.args[1:] if args.args[:1]==["--"] else args.args
   return subprocess.call([os.path.expanduser(x) for x in command]+extra)
  elif args.command=="status":
   config,state=paths(home)
   print(json.dumps({"installed":read(config/"profile.json",{}),"root":str(ROOT),"transactions":[read(p) for p in sorted((state/"transactions").glob("*.json"))]},ensure_ascii=False,indent=2))
  elif args.command=="edit":
   if not args.component:print("\n".join(f"{k:16} {v}" for k,v in EDIT.items()));return 0
   if args.component in ("local","hs-local","local-keys"):
    p=paths(home)[0]/{"local":"local.zsh","hs-local":"hammerspoon.lua","local-keys":"keymaps.zsh"}[args.component]
    if not args.print_path:p.parent.mkdir(parents=True,exist_ok=True);p.touch(exist_ok=True)
   else:
    if args.component not in EDIT:raise ValueError("Unknown config. Run mackit edit to list.")
    p=ROOT/"components"/EDIT[args.component]
   if args.print_path:print(p)
   else:return subprocess.call(shlex.split(os.environ.get("EDITOR","nvim"))+[str(p)])
  elif args.command=="deps":
   _,selected=selection(args,home)
   formula=sorted(set(x for c in selected for x in DEPS.get(c,[])))
   print("brew install python "+" ".join(formula))
   casks=[CASKS[c] for c in selected if c in CASKS]
   if casks:print("brew install --cask "+" ".join(casks))
   if "yabai" in selected:print("Optional window manager: install yabai/skhd from their official project instructions.")
  elif args.command=="update":
   if not (ROOT/".git").exists():raise ValueError("Release archive: install the new release and apply it; existing configuration is backed up.")
   if subprocess.check_output(["git","-C",str(ROOT),"status","--porcelain"],text=True).strip():raise ValueError("Working tree has edits. Commit or preserve them before update.")
   subprocess.run(["git","-C",str(ROOT),"pull","--ff-only"],check=True)
   print("Updated source. Review mackit plan, then mackit apply.")
  return 0
 except (ValueError,OSError,subprocess.SubprocessError) as exc:
  print("mackit: "+str(exc),file=sys.stderr);return 1
if __name__=="__main__":raise SystemExit(main())
