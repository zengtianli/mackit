"""Application language changes use disposable bundles and preferences only."""
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mackit import application_settings as apps, cli, gui


def fixture(home, bundle="com.example.Editor", name="Editor", languages=("en", "zh_CN")):
    root = home/"Applications"/(name+".app")/"Contents"
    (root/"Resources").mkdir(parents=True)
    (root/"Info.plist").write_bytes(plistlib.dumps({"CFBundleIdentifier":bundle, "CFBundleName":name}))
    for language in languages:
        (root/"Resources"/(language+".lproj")).mkdir()
    return root.parent


class ApplicationSettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mackit-app-settings-")
        self.home = Path(self.temp.name).resolve()
        fixture(self.home)
        self.bundle = "com.example.Editor"

    def tearDown(self):
        self.temp.cleanup()

    def row(self, bundle=None):
        return next(r for r in apps.snapshot(self.home)["apps"] if r["id"] == (bundle or self.bundle))

    def change(self, language, bundle=None, **extra):
        return apps.change(self.home, [{"id":bundle or self.bundle, "language":language, **extra}])

    def test_list_is_read_only_and_searches_office(self):
        for bundle, name in [("com.microsoft.Word","Word"),("com.microsoft.Excel","Excel"),("com.microsoft.Powerpoint","PowerPoint")]:
            fixture(self.home,bundle,name)
        result = gui.dispatch({"action":"applicationSnapshot","query":"Office"}, self.home)
        self.assertEqual(len(result["applications"]["apps"]),3)
        self.assertFalse((self.home/".local").exists())
        self.assertFalse((self.home/"Library").exists())
        self.assertEqual({v["id"] for v in self.row()["languages"]},{"system","en","zh-Hans"})

    def test_external_copy_changes_on_read_and_corrupt_override_falls_back(self):
        path = self.home/".config/mackit/application-settings.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"copy":{"saved":"稍后重开"}}))
        self.change("zh-Hans")
        self.assertEqual(self.row()["status"],"稍后重开")
        path.write_text("invalid JSON")
        self.assertIn("下次打开",self.row()["status"])

    def test_write_restore_and_system_keep_unrelated_preferences(self):
        path = apps.preference_path(self.bundle,self.home)
        path.parent.mkdir(parents=True)
        path.write_bytes(plistlib.dumps({"OtherSetting":{"keep":True},"AppleLanguages":["en","ja"]}))
        before = path.read_bytes()
        changed = self.change("zh-Hans",digest=self.row()["digest"])
        self.assertEqual(changed["changed"],1)
        self.assertEqual(self.row()["selected"],"zh-Hans")
        self.assertEqual(apps.load_plist(path)["OtherSetting"],{"keep":True})
        apps.restore(self.home,changed["transaction"])
        self.assertEqual(path.read_bytes(),before)
        self.change("system")
        self.assertNotIn("AppleLanguages",apps.load_plist(path))
        self.assertEqual(apps.load_plist(path)["OtherSetting"],{"keep":True})
        apps.restore(self.home)
        self.assertEqual(apps.preference(self.bundle,self.home),["en","ja"])

    def test_noop_preserves_exact_existing_language_array(self):
        apps.write_preference(self.bundle,["zh-Hans-CN","en"],self.home)
        self.assertEqual(self.change("zh-Hans")["changed"],0)
        self.assertIsNone(apps.latest(self.home))
        self.assertEqual(apps.preference(self.bundle,self.home),["zh-Hans-CN","en"])

    def test_batch_preflight_rejects_one_unsupported_language_without_writes(self):
        fixture(self.home,"com.example.Second","Second",("en",))
        with self.assertRaisesRegex(cli.Failure,"未提供"):
            apps.change(self.home,[{"id":self.bundle,"language":"zh-Hans"},{"id":"com.example.Second","language":"zh-Hans"}])
        self.assertIsNone(apps.preference(self.bundle,self.home))
        self.assertFalse(apps.records_dir(self.home).exists())

    def test_failed_batch_rolls_back_an_already_written_preference(self):
        fixture(self.home,"com.example.Second","Second")
        write = apps.write_preference
        def fail(bundle,value,home):
            if bundle == "com.example.Second" and value == ["zh-Hans"]:
                raise OSError("injected second write failure")
            return write(bundle,value,home)
        with patch.object(apps,"write_preference",side_effect=fail):
            with self.assertRaises(cli.Failure):
                apps.change(self.home,[{"id":self.bundle,"language":"zh-Hans"},{"id":"com.example.Second","language":"zh-Hans"}])
        self.assertIsNone(apps.preference(self.bundle,self.home))
        self.assertIsNone(apps.preference("com.example.Second",self.home))
        self.assertIsNone(apps.latest(self.home))

    def test_stale_snapshot_and_restore_preserve_external_change(self):
        old = self.row()["digest"]
        self.change("en")
        with self.assertRaisesRegex(cli.Failure,"其他程序"):
            self.change("zh-Hans",digest=old)
        apps.write_preference(self.bundle,["ja"],self.home)
        with self.assertRaisesRegex(cli.Failure,"其他程序"):
            apps.restore(self.home)
        self.assertEqual(apps.preference(self.bundle,self.home),["ja"])

    def test_interrupted_batch_can_be_recovered(self):
        fixture(self.home,"com.example.Second","Second")
        changed = apps.change(self.home,[{"id":self.bundle,"language":"zh-Hans"},{"id":"com.example.Second","language":"zh-Hans"}])
        record = apps.latest(self.home)
        record["status"] = "preparing"
        cli.dump(apps.records_dir(self.home)/(changed["transaction"]+".json"),record)
        apps.write_preference("com.example.Second",None,self.home)
        with self.assertRaisesRegex(cli.Failure,"未完成"):
            self.change("en")
        apps.restore(self.home)
        self.assertIsNone(apps.preference(self.bundle,self.home))
        self.assertIsNone(apps.preference("com.example.Second",self.home))

    def test_isolation_rejects_escaping_symlinks_even_with_home_environment_override(self):
        with tempfile.TemporaryDirectory(prefix="mackit-outside-") as outside:
            external = Path(outside)
            fixture(external,"com.example.Outside","Outside")
            (self.home/"Applications/Outside.app").symlink_to(external/"Applications/Outside.app",target_is_directory=True)
            with patch.dict(os.environ,{"HOME":str(self.home)}):
                self.assertTrue(apps.isolated(self.home))
                self.assertEqual(len(apps.snapshot(self.home)["apps"]),1)
            (self.home/"Library").symlink_to(external,target_is_directory=True)
            with self.assertRaisesRegex(cli.Failure,"目录之外"):
                self.change("zh-Hans")
            self.assertFalse((external/"Preferences").exists())

    def test_cli_and_gui_share_preferences_and_errors(self):
        def call(*words,code=0):
            result = subprocess.run([sys.executable,str(ROOT/"bin/mackit"),"--home",str(self.home),"apps",*words,"--json"],capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,code,result.stderr+result.stdout)
            data = json.loads(result.stdout)
            self.assertEqual(data["ok"], code == 0)
            return data
        self.assertEqual(len(call("list")["applications"]["apps"]),1)
        call("language","set",self.bundle,"zh-Hans")
        self.assertEqual(gui.dispatch({"action":"applicationSnapshot"},self.home)["applications"]["apps"][0]["selected"],"zh-Hans")
        self.assertEqual(call("language","set",self.bundle,"unsupported",code=1)["error"]["code"],"unsupported_language")
        call("language","restore")
        self.assertIsNone(apps.preference(self.bundle,self.home))
        self.assertEqual(call("language","set",self.bundle,code=2)["error"]["code"],"usage")


if __name__ == "__main__":
    unittest.main()
