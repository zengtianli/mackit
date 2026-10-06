"""Build the handbook from native key declarations, not a second shortcut list."""
from pathlib import Path
import html,json,re,subprocess,tempfile,tomllib
ROOT=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as temp:
 output=Path(temp)/"keys.json"
 subprocess.run(["nvim","--clean","--headless","-l",str(ROOT/"scripts/export-keys.lua"),str(ROOT),str(output)],check=True)
 rows=json.loads(output.read_text())
def add(comp,mode,key,desc,source,**extra):rows.append(dict(component=comp,mode=mode,key=key,description=desc,source=source,**extra))
p=ROOT/"components/zsh/keymaps.zsh"
for line in p.read_text().splitlines():
 m=re.search(r"bindkey -M (\S+) '([^']+)' (\S+)\s*#\s*(.*)",line)
 if m:add("zsh",m[1],m[2],m[4],str(p.relative_to(ROOT)),condition="without-atuin" if "history-incremental" in m[3] else ("with-atuin" if m[3].startswith("atuin") else "always"))
for comp,filename in [("tmux","keymaps.conf"),("ghostty","keymaps.conf")]:
 p=ROOT/"components"/comp/filename
 for line in p.read_text().splitlines():
  if line.startswith("bind "):
   before,_,comment=line.partition(" #")
   parts=before.split()
   if parts[1]=="-n":mode,key="global",parts[2]
   elif parts[1]=="-T":mode,key=parts[2],parts[3]
   else:mode,key="prefix",parts[1]
   add(comp,mode,key,comment.strip() or before,str(p.relative_to(ROOT)))
  elif line.startswith("keybind"):
   combo,action=line.split("=",1)[1].strip().split("=",1)
   add(comp,"global" if combo.startswith("global:") else "terminal",combo.removeprefix("global:"),action,str(p.relative_to(ROOT)),profile="tianli")
p=ROOT/"components/yazi/keymap.toml"
data=tomllib.loads(p.read_text())
for mode,group in data.items():
 if isinstance(group,dict):
  for groupname,entries in group.items():
   if isinstance(entries,list):
    for item in entries:
     if isinstance(item,dict) and "on" in item:
      key=" ".join(item["on"]) if isinstance(item["on"],list) else item["on"]
      add("yazi",mode,key,item.get("desc") or str(item.get("run","")),str(p.relative_to(ROOT)))
p=ROOT/"components/yabai/config/skhd/skhdrc"
label=""
for line in p.read_text().splitlines():
 # MacKit writes each binding's label as the comment line above it.
 if line.startswith("# "):label=line[2:].strip();continue
 if not line.strip() or ":" not in line:label="";continue
 key,cmd=line.split(":",1);add("yabai","global",key.strip(),label or cmd.strip(),str(p.relative_to(ROOT)));label=""
p=ROOT/"components/karabiner/karabiner.json"
KARABINER_MODS={"command":"cmd","control":"ctrl","option":"alt","shift":"shift","fn":"fn"}
KARABINER_KEYS={"semicolon":";","quote":"'","comma":","}
def karabiner_key(source):
 """An exact chord in the form localkeys.normalize reads; the raw `from` JSON for layers and buttons."""
 mods=source.get("modifiers",{});code=source.get("key_code")
 held=[KARABINER_MODS.get(m.removeprefix("left_").removeprefix("right_")) for m in mods.get("mandatory",[])]
 if not code or None in held or "any" in mods.get("optional",[]):return json.dumps(source,ensure_ascii=False)
 return "+".join(held+[KARABINER_KEYS.get(code,code.replace("_","-"))])
def karabiner_mode(rule,conditions):
 """Where the key is held: only 'global' and 'outside-terminals' rows compete for a system-wide key."""
 if rule.get("enabled",True) is False:return "disabled"
 mode="global"
 for c in conditions:
  if c["type"]=="frontmost_application_if":mode="finder" if any("finder" in b for b in c.get("bundle_identifiers",[])) else "app"
  elif c["type"]=="frontmost_application_unless":mode="outside-terminals"
  elif c["type"]=="variable_if" and c.get("name")=="mackit_wechat_launch":mode="wechat-not-running"
  elif c["type"]=="variable_if" and c.get("name")=="tab pressed" and c.get("value")==1:mode="tab-layer"
 return mode
for profile in json.loads(p.read_text())["profiles"]:
 for rule in profile.get("complex_modifications",{}).get("rules",[]):
  for mapping in rule.get("manipulators",[]):
   conditions=mapping.get("conditions",[])
   add("karabiner",karabiner_mode(rule,conditions),karabiner_key(mapping.get("from",{})),mapping.get("description") or rule.get("description",""),str(p.relative_to(ROOT)),profile="tianli",condition=json.dumps(conditions,ensure_ascii=False))
rows.sort(key=lambda r:(r["component"],r["mode"],r["key"],r.get("profile","")))
(ROOT/"data").mkdir(exist_ok=True);(ROOT/"data/keys.json").write_text(json.dumps(rows,ensure_ascii=False,indent=2,sort_keys=True)+"\n")
e=html.escape
body=''.join('<tr data-component="'+e(r["component"])+ '" data-profile="'+e(r.get("profile",""))+'" data-advanced="'+("1" if r["description"].startswith("编码跳行") else "")+'"><td>'+e(r["component"])+'<small>'+e(r.get("profile","通用"))+'</small></td><td><kbd>'+e(r["key"])+ '</kbd></td><td>'+e(r["description"])+'<small>'+e(r["mode"])+'</small></td><td><a href="https://github.com/zengtianli/mackit/blob/main/'+e(r["source"])+'"><code>'+e(r["source"])+ '</code></a></td></tr>' for r in rows)
page=(ROOT/"site/keys.template.html").read_text().replace("__ROWS__",body).replace("__OPTIONS__",''.join('<option>'+e(c)+'</option>' for c in sorted({r['component'] for r in rows})))
(ROOT/"site/keys.html").write_text(page)
print(f"Generated {len(rows)} declarations from native configuration.")
