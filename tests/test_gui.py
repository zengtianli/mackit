"""Exercise the native app's actual JSON protocol against disposable homes."""
import hashlib,json,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class AppBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="mackit-app-test-");self.home=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def call(self,action,ok=True,**values):
        r=subprocess.run([sys.executable,str(ROOT/"bin/mackit"),"--home",str(self.home),"gui"],input=json.dumps({"action":action,**values}),capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr)
        result=json.loads(r.stdout);self.assertEqual(result["ok"],ok,result)
        return result
    def test_preview_install_reload_edit_and_restore(self):
        (self.home/".zshrc").write_text("original\n")
        snap=self.call("snapshot");self.assertFalse(snap["installed"])
        self.assertGreater(len(snap["keys"]),500)
        selection={"profile":"developer","components":["zsh","nvim"]}
        preview=self.call("preview",**selection)
        self.assertFalse((self.home/".zshrc").is_symlink())
        applied=self.call("apply",token=preview["token"],**selection)
        self.assertTrue((self.home/".zshrc").is_symlink())
        current=self.call("snapshot");self.assertTrue(current["installed"])
        self.assertEqual(current["sourceRoot"],str(self.home/".local/share/mackit"))
        file=self.call("readFile",file="nvim-keys")
        content=file["content"]+"\n-- app test\n"
        saved=self.call("saveFile",file="nvim-keys",content=content,digest=file["digest"])
        self.assertTrue(Path(saved["backup"]).exists())
        self.assertEqual(self.call("readFile",file="nvim-keys")["content"],content)
        self.call("restore",transaction=applied["installation"]["transaction"])
        self.assertEqual((self.home/".zshrc").read_text(),"original\n")
    def test_stale_preview_and_external_edit_are_rejected(self):
        selection={"profile":"developer","components":["zsh"]}
        p=self.call("preview",**selection)
        (self.home/".zshrc").write_text("new work")
        self.call("apply",token=p["token"],ok=False,**selection)
        self.assertEqual((self.home/".zshrc").read_text(),"new work")
        f=self.call("readFile",file="nvim-keys")
        Path(f["path"]).write_text("another editor")
        self.call("saveFile",file="nvim-keys",content="overwrite",digest=f["digest"],ok=False)
        self.assertEqual(Path(f["path"]).read_text(),"another editor")
    def test_preview_preserves_unrelated_source_directory(self):
        root=self.home/".local/share/mackit";root.mkdir(parents=True);(root/"private.txt").write_text("keep")
        self.call("preview",components=["nvim"],ok=False)
        self.assertEqual((root/"private.txt").read_text(),"keep")
    def test_invalid_file_and_empty_selection_rejected(self):
        self.call("preview",components=[],ok=False)
        self.call("preview",components=["nvim"])
        self.call("readFile",file="../../secret",ok=False)
    def test_restore_requires_exact_receipt(self):
        p=self.call("preview",components=["nvim"])
        self.call("apply",components=["nvim"],token=p["token"])
        self.call("restore",transaction="wrong",ok=False)
        self.assertTrue((self.home/".config/nvim").is_symlink())

if __name__=="__main__":unittest.main()
