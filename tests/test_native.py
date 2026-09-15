
import json,os,subprocess,tempfile,unittest
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
 def test_right_option_has_only_one_owner(self):
  data=json.loads((ROOT/"components/karabiner/karabiner.json").read_text())
  for p in data["profiles"]:
   for r in p["complex_modifications"]["rules"]:
    for m in r["manipulators"]:
     self.assertNotEqual(m.get("from",{}).get("key_code"),"right_option")
if __name__=="__main__":unittest.main()
