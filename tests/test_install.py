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
  # An isolated --home installs from its own prepared source, never by linking into this checkout.
  self.assertTrue(z.is_symlink());self.assertEqual(n.resolve(),(self.home/".local/share/mackit/components/nvim").resolve())
  again=json.loads(self.run_cli("apply","--components","zsh,nvim").stdout)
  self.assertEqual(again["changed"],0)
  self.run_cli("restore",r["transaction"])
  self.assertEqual(z.read_text(),"original shell\n");self.assertEqual((n/"user.lua").read_text(),"private edits")
 def fake_app(self):
  app=self.home/"Applications/MacKit.app/Contents/Resources/core";(app/"bin").mkdir(parents=True)
  exe=app/"bin/mackit";exe.write_text("#!/bin/sh\n");exe.chmod(0o755);(app/"VERSION").write_text("0\n")
  return app,exe
 def test_app_cli_on_new_mac_prepares_app_source_not_bundle(self):
  # The App's CLI must behave like the App: configs live in ~/.local/share/mackit, never inside the signed bundle.
  app,exe=self.fake_app();source=self.home/".local/share/mackit"
  with patch.object(sys,"frozen",True,create=True),patch.object(sys,"executable",str(exe)),patch.object(cli,"ROOT",ROOT),contextlib.redirect_stdout(io.StringIO()) as out:
   self.assertEqual(cli.main(["--home",str(self.home),"plan","--components","nvim","--json"]),0)
   planned=json.loads(out.getvalue());out.seek(0);out.truncate()
   self.assertEqual(planned["root"],str(source));self.assertFalse(planned["source_ready"])
   self.assertFalse(source.exists(),"plan must not create the source")
   self.assertEqual(cli.main(["--home",str(self.home),"apply","--components","nvim","--token",planned["token"]]),0)
   self.assertEqual((self.home/".local/bin/mackit").resolve(),exe.resolve())
   self.assertEqual((self.home/".config/nvim").resolve(),(source/"components/nvim").resolve())
   cli.ROOT=app;self.assertEqual(cli.main(["--home",str(self.home),"edit","nvim-keys","--print"]),0)
  lines=out.getvalue().splitlines()
  self.assertEqual(lines[-1],str(source/"components/nvim/lua/config/keymaps.lua"))
  self.run_cli("restore",json.loads(lines[0])["transaction"])
  self.assertFalse(os.path.lexists(self.home/".local/bin/mackit"))
 def test_app_cli_uses_recorded_source_and_stale_token_is_refused(self):
  app,exe=self.fake_app();cfg=self.home/".config/mackit";cfg.mkdir(parents=True)
  (cfg/"profile.json").write_text(json.dumps({"profile":"developer","components":["nvim"],"source_root":str(ROOT)}))
  with patch.object(sys,"frozen",True,create=True),patch.object(sys,"executable",str(exe)),patch.object(cli,"ROOT",app),contextlib.redirect_stdout(io.StringIO()) as out,contextlib.redirect_stderr(io.StringIO()):
   self.assertEqual(cli.main(["--home",str(self.home),"edit","nvim-keys","--print"]),0)
   self.assertEqual(out.getvalue().splitlines()[-1],str(ROOT/"components/nvim/lua/config/keymaps.lua"))
   self.assertEqual(cli.main(["--home",str(self.home),"apply","--components","nvim","--token","0"*64]),1)
  self.assertFalse((self.home/".config/nvim").exists())
 def test_link_command_is_recorded_and_restorable(self):
  old=self.home/".local/bin/mackit";old.parent.mkdir(parents=True)
  old.symlink_to(str(self.home/"gone/Tianli MacKit.app/Contents/Resources/core/bin/mackit"))  # a renamed App's leftover
  status=json.loads(self.run_cli("status","--json").stdout)
  self.assertEqual(status["commandLink"]["target"],str(self.home/"gone/Tianli MacKit.app/Contents/Resources/core/bin/mackit"))
  self.assertFalse(status["commandLink"]["resolves"])
  done=json.loads(self.run_cli("link","--json").stdout)
  self.assertEqual(done["changed"],1);self.assertTrue(old.exists())
  self.assertEqual(json.loads(self.run_cli("link","--json").stdout)["changed"],0)
  self.run_cli("restore",done["transaction"])
  self.assertEqual(os.readlink(old),str(self.home/"gone/Tianli MacKit.app/Contents/Resources/core/bin/mackit"))
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
  refused=self.run_cli("edit","nvim-keys","--print",ok=False)
  self.assertNotEqual(refused.returncode,0);self.assertIn("mackit prepare",refused.stderr)
  prepared=json.loads(self.run_cli("prepare","--json").stdout)
  self.assertTrue(prepared["created"]);self.assertFalse(json.loads(self.run_cli("prepare","--json").stdout)["created"])
  p=Path(self.run_cli("edit","nvim-keys","--print").stdout.strip())
  self.assertEqual(p,Path(prepared["root"])/"components/nvim/lua/config/keymaps.lua");self.assertTrue(p.is_file())
 def test_app_cli_accepts_a_source_recorded_in_its_own_bundle(self):
  # 0.3.3/0.3.4's bundled apply on a new Mac recorded the bundle's core; the App keeps working on it, so must the CLI.
  cfg=self.home/".config/mackit";cfg.mkdir(parents=True)
  (cfg/"profile.json").write_text(json.dumps({"profile":"developer","components":["nvim"],"source_root":str(ROOT)}))
  with patch.object(sys,"frozen",True,create=True),patch.object(cli,"ROOT",ROOT),contextlib.redirect_stdout(io.StringIO()) as out:
   self.assertEqual(cli.main(["--home",str(self.home),"plan","--components","nvim","--json"]),0)
  self.assertEqual(json.loads(out.getvalue())["root"],str(ROOT))
 def test_config_action_preserves_argument_boundaries(self):
  cfg=self.home/".config/mackit";cfg.mkdir(parents=True)
  (cfg/"actions.json").write_text(json.dumps({"echo":[sys.executable,"-c","import sys; print(repr(sys.argv[1:]))"]}))
  r=self.run_cli("action","echo","--","file with space","a;echo nope")
  self.assertIn("['file with space', 'a;echo nope']",r.stdout)
if __name__=="__main__":unittest.main()
