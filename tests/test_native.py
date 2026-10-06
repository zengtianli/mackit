
import json,os,re,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class NativeTests(unittest.TestCase):
 def test_numbering_through_actual_visual_mapping(self):
  with tempfile.TemporaryDirectory() as t:
   out=Path(t)/"result.json";script=Path(t)/"test.lua"
   script.write_text("""
vim.api.nvim_buf_set_lines(0,0,-1,false,{"alpha","beta","gamma"})
vim.api.nvim_win_set_cursor(0,{1,0})
local keys=vim.api.nvim_replace_termcodes("Vj<Space>nl",true,false,true)
vim.api.nvim_feedkeys(keys,"xt",false)
assert(vim.deep_equal(vim.api.nvim_buf_get_lines(0,0,-1,false),{"01_alpha","02_beta","gamma"}))
assert(vim.fn.maparg("sh","n"):find("leftabove"))
assert(vim.fn.maparg(" nl","x"):find("actions.text"))
vim.fn.writefile({"ok"},"""+json.dumps(str(out))+""")
vim.cmd("qa!")
""")
   env=dict(os.environ,MACKIT_NO_PLUGINS="1",MACKIT_PROFILE="tianli")
   p=subprocess.run(["nvim","--headless","-u",str(ROOT/"components/nvim/init.lua"),"-l",str(script)],env=env,text=True,capture_output=True,timeout=20)
   self.assertTrue(out.exists(),p.stdout+p.stderr)
 def test_native_syntax(self):
  for p in (ROOT/"components/hammerspoon").rglob("*.lua"):
   r=subprocess.run(["luac","-p",str(p)],capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr)
 def test_shell_installed_under_another_home(self):
  with tempfile.TemporaryDirectory() as t:
   home=Path(t)
   subprocess.run([str(ROOT/"bin/mackit"),"--home",t,"apply","--components","zsh"],check=True,capture_output=True)
   env={"HOME":t,"ZDOTDIR":t,"MACKIT_PROFILE":"developer","PATH":os.environ["PATH"],"TERM":"xterm-256color","LANG":"en_US.UTF-8"}
   r=subprocess.run(["zsh","-ic",'bindkey "^P"; bindkey "^A"; config nvim-keys --print'],env=env,text=True,capture_output=True,timeout=20)
   self.assertEqual(r.returncode,0,r.stderr)
   self.assertIn("_mackit_file",r.stdout)
   self.assertIn("beginning-of-line",r.stdout)
   self.assertIn("components/nvim/lua/config/keymaps.lua",r.stdout)
   self.assertNotIn("no such file",r.stderr)
 def karabiner_manipulators(self):
  data=json.loads((ROOT/"components/karabiner/karabiner.json").read_text())
  return [m for p in data["profiles"] for r in p["complex_modifications"]["rules"] if r.get("enabled",True) for m in r["manipulators"]]
 def test_right_option_has_only_one_owner(self):
  # Karabiner owns Right Option → Hyper and every other key; Hammerspoon listens to none.
  self.assertEqual(sum(m.get("from",{}).get("key_code")=="right_option" for m in self.karabiner_manipulators()),1)
  for p in (ROOT/"components/hammerspoon").rglob("*.lua"):
   for listener in ("hs.hotkey.bind","hs.hotkey.new","hs.eventtap.new"):self.assertNotIn(listener,p.read_text(),p)
 def test_shift_tap_keeps_shift_for_clicks_and_switches_with_the_system_shortcut(self):
  # A lazy Shift never reaches a click from a pointer Karabiner does not grab. select_input_source is unreliable
  # for input modes (Karabiner's own note on CJKV), so ABC → Pinyin sends Control-Space instead.
  taps=[m for m in self.karabiner_manipulators() if m.get("from",{}).get("key_code") in ("left_shift","right_shift")]
  self.assertEqual(len(taps),4)
  for m in taps:
   self.assertEqual(m["to"],[{"key_code":m["from"]["key_code"]}],m)
   from_abc="input_source_id" in m["conditions"][0]["input_sources"][0]
   expected={"key_code":"spacebar","modifiers":["left_control"]} if from_abc else {"select_input_source":{"input_source_id":"^com\\.apple\\.keylayout\\.ABC$"}}
   self.assertEqual(m["to_if_alone"],[expected],m)
 def karabiner_commands(self):
  return [(m,to["shell_command"]) for m in self.karabiner_manipulators() for group in ("to","to_if_alone","to_after_key_up") for to in m.get(group,[]) if "shell_command" in to]
 def action_hotkeys(self):
  # The skhd bindings that run an action script or a plain command, by key.
  rows=json.loads((ROOT/"components/yabai/config/skhd/hotkeys.json").read_text())
  return {h["key"]:h["command"] for h in rows if "command" in h}
 ACTIONS="$HOME/.config/yabai/scripts/actions/"
 def test_karabiner_only_remaps_and_skhd_runs_the_actions(self):
  # Karabiner maps keys to keys (2026-10-06). Anything that runs a program is an skhd binding, so no rule carries a shell_command
  # and the keys still work with Hammerspoon closed.
  self.assertEqual(self.karabiner_commands(),[])
  keys=self.action_hotkeys()
  expected={"cmd+ctrl+shift+t":"finder-terminal.sh","cmd+ctrl+shift+;":"music.sh toggle","cmd+ctrl+shift+'":"music.sh next",
   "cmd+ctrl+alt+l":"local.sh lid-sleep","cmd+ctrl+alt+b":"local.sh brew-maintain","cmd+ctrl+alt+p":"local.sh smart-push",
   "cmd+ctrl+shift+y":"yabai-service.sh","cmd+ctrl+shift+m":"mouse-follows-focus.sh","cmd+shift+v":"code-fence-paste.sh"}
  for key,command in expected.items():self.assertEqual(keys.get(key),self.ACTIONS+command,key)
  self.assertEqual(keys.get("cmd+alt+,"),"/usr/bin/open -b com.apple.systempreferences")
  for key,command in keys.items():
   self.assertNotIn("Hammerspoon",command,key)
   # No machine-specific path in the public file: a personal script is reached only through local.sh and the user's own ~/.config/mackit/bin.
   self.assertNotIn("/Users/",command,key);self.assertNotIn("~/Dev",command,key);self.assertNotIn(".config/mackit/bin",command,key)
   if command.startswith(self.ACTIONS):
    script=ROOT/"components/yabai/scripts/actions"/command[len(self.ACTIONS):].split()[0]
    self.assertTrue(os.access(script,os.X_OK),script)
  self.assertEqual({c.split()[-1] for c in keys.values() if "/local.sh " in c},{"lid-sleep","brew-maintain","smart-push"})
  self.assertIn('x="$HOME/.config/mackit/bin/$1"',(ROOT/"components/yabai/scripts/actions/local.sh").read_text())
 def test_every_action_script_reports_with_a_system_notification(self):
  # One kind of feedback for every action key: a macOS notification. Opening System Settings shows itself, and a personal script notifies on its own.
  for p in (ROOT/"components/yabai/scripts/actions").glob("*.sh"):
   if p.name!="local.sh":self.assertIn("display notification",p.read_text(),p)
  # Hyper+P is a plain mapping to the media key; a notification would need a program, which Karabiner no longer runs.
  [p]=[m for m in self.karabiner_manipulators() if any("consumer_key_code" in to for to in m.get("to",[]))]
  self.assertEqual(p["to"],[{"consumer_key_code":"play_or_pause"}])
 def test_code_fence_paste_writes_the_clipboard_before_it_pastes(self):
  # Shift-Command-V: one script rewrites the clipboard and then sends Command-V itself. A timed paste from Karabiner lost the race on a busy Mac.
  self.assertEqual([m for m in self.karabiner_manipulators() if m.get("from",{}).get("key_code")=="v"],[])
  script=(ROOT/"components/yabai/scripts/actions/code-fence-paste.sh").read_text()
  paste=script.index('keystroke("v", {using: "command down"})')
  self.assertLess(script.index("| /usr/bin/pbcopy"),paste)
  # skhd fires while Shift and Command are still down: a Command-V sent then arrives as Shift-Command-V and lands on this binding again.
  self.assertLess(script.index("$.NSEvent.modifierFlags & held"),paste)
  # Held keys or a second press must not wrap the text twice.
  self.assertIn("mackit-code-fence.lock",script)
if __name__=="__main__":unittest.main()
