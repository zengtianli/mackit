"""Installer tests use isolated homes and real CLI entrypoints, never the user's links."""
import contextlib, importlib, io, json, os, subprocess, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from mackit import cli
class InstallTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def run_cli(self,*args,ok=True):
  proc=subprocess.run([sys.executable,str(ROOT/"bin/mackit"),"--home",str(self.home),*args],capture_output=True,text=True)
  if ok:self.assertEqual(proc.returncode,0,proc.stderr)
  return proc
 def test_real_install_idempotence_and_restore_existing_files(self):
  z=self.home/".zshrc";z.write_text("original shell\n")
  n=self.home/".config/nvim";n.mkdir(parents=True);(n/"user.lua").write_text("private edits")
  r=json.loads(self.run_cli("apply","--components","zsh,nvim").stdout)
  self.assertTrue(z.is_symlink());self.assertEqual(n.resolve(),ROOT/"components/nvim")
  again=json.loads(self.run_cli("apply","--components","zsh,nvim").stdout)
  self.assertEqual(again["changed"],0)
  self.run_cli("restore",r["transaction"])
  self.assertEqual(z.read_text(),"original shell\n");self.assertEqual((n/"user.lua").read_text(),"private edits")
 def test_restore_does_not_delete_new_user_config(self):
  self.run_cli("apply","--components","zsh")
  z=self.home/".zshrc";z.unlink();z.write_text("new work")
  proc=self.run_cli("restore",ok=False)
  self.assertNotEqual(proc.returncode,0);self.assertEqual(z.read_text(),"new work")
 def test_target_parent_escape_rejected(self):
  with tempfile.TemporaryDirectory() as outside:
   (self.home/".config").symlink_to(outside)
   proc=self.run_cli("apply","--components","nvim",ok=False)
   self.assertNotEqual(proc.returncode,0);self.assertEqual(list(Path(outside).iterdir()),[])
 def test_error_after_first_link_restores_all(self):
  (self.home/".zshrc").write_text("before")
  original=Path.symlink_to;calls=0
  def fail(path,*args,**kwargs):
   nonlocal calls
   calls+=1
   if calls==2:raise OSError("injected install failure")
   return original(path,*args,**kwargs)
  with patch.object(Path,"symlink_to",fail),contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
   rc=cli.main(["--home",str(self.home),"apply","--components","zsh,nvim"])
  self.assertEqual(rc,1);self.assertEqual((self.home/".zshrc").read_text(),"before")
  self.assertFalse((self.home/".config/nvim").exists())
 def test_generated_configs_are_idempotent_and_keep_device_overrides_local(self):
  cfg=self.home/".config/mackit";cfg.mkdir(parents=True)
  (cfg/"karabiner-device-settings.json").write_text(json.dumps({"devices":[{"identifiers":{"vendor_id":1234}}]}))
  self.run_cli("apply","--profile","tianli","--components","ghostty,karabiner")
  value=json.loads((self.home/".config/karabiner/karabiner.json").read_text())
  self.assertEqual(value["profiles"][0]["devices"][0]["identifiers"]["vendor_id"],1234)
  self.assertNotIn("devices",json.loads((ROOT/"components/karabiner/karabiner.json").read_text())["profiles"][0])
  self.assertIn("keymaps.conf",(self.home/".config/ghostty/config").read_text())
  self.assertEqual(json.loads(self.run_cli("apply").stdout)["changed"],0)
  self.assertNotEqual(self.run_cli("apply","--profile","developer",ok=False).returncode,0)
  self.run_cli("restore")
  self.run_cli("apply","--profile","developer","--components","ghostty")
  self.assertNotIn("keymaps.conf",(self.home/".config/ghostty/config").read_text())
 def test_interrupted_install_requires_restore_and_protects_new_edits(self):
  result=json.loads(self.run_cli("apply","--components","zsh").stdout)
  receipt=self.home/".local/state/mackit/transactions"/(result["transaction"]+".json")
  data=json.loads(receipt.read_text());data["status"]="installing";receipt.write_text(json.dumps(data))
  self.assertNotEqual(self.run_cli("apply",ok=False).returncode,0)
  z=self.home/".zshrc";z.unlink();z.write_text("new work")
  self.assertNotEqual(self.run_cli("restore",ok=False).returncode,0)
  self.assertEqual(z.read_text(),"new work")
 def test_edit_returns_real_key_owner(self):
  p=self.run_cli("edit","nvim-keys","--print").stdout.strip()
  self.assertEqual(Path(p),ROOT/"components/nvim/lua/config/keymaps.lua")
 def test_config_action_preserves_argument_boundaries(self):
  cfg=self.home/".config/mackit";cfg.mkdir(parents=True)
  (cfg/"actions.json").write_text(json.dumps({"echo":[sys.executable,"-c","import sys; print(repr(sys.argv[1:]))"]}))
  r=self.run_cli("action","echo","--","file with space","a;echo nope")
  self.assertIn("['file with space', 'a;echo nope']",r.stdout)
if __name__=="__main__":unittest.main()
