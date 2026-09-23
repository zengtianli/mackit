import json, os, plistlib, tempfile, unittest
from pathlib import Path
from mackit import localkeys


class LocalKeysTests(unittest.TestCase):
 def setUp(self):
  self.tmp = tempfile.TemporaryDirectory()
  self.home = Path(self.tmp.name)
  os.environ.pop("XDG_CONFIG_HOME", None)
  self.keysd = self.home / ".config/mackit/keys.d"
  self.keysd.mkdir(parents=True)

 def tearDown(self):
  self.tmp.cleanup()

 def test_normalize_orders_modifiers_and_keeps_right_cmd_distinct(self):
  self.assertEqual(localkeys.normalize("cmd+ctrl+shift+h"), localkeys.normalize("shift+ctrl+cmd+H"))
  self.assertEqual(localkeys.normalize("right-cmd+c"), "right-cmd+c")
  self.assertNotEqual(localkeys.normalize("right-cmd+c"), localkeys.normalize("cmd+c"))
  # Holding left ⌘ + C is the same key press as ⌘C, so it conflicts with app shortcuts.
  self.assertEqual(localkeys.normalize("left-cmd+c"), localkeys.normalize("cmd+c"))
  self.assertEqual(localkeys.normalize("space"), "space")
  self.assertIsNone(localkeys.normalize("super+x"))

 def test_app_manifest_rows_and_bad_files_are_reported(self):
  (self.keysd / "demo.json").write_text(json.dumps([{"component": "demo", "mode": "app:Demo", "key": "cmd+y", "description": "history"}]))
  (self.keysd / "broken.json").write_text("{nope")
  rows, issues = localkeys.app_rows(self.home)
  self.assertEqual([r["key"] for r in rows], ["cmd+y"])
  self.assertEqual(len(issues), 1)
  self.assertIn("broken.json", issues[0])

 def test_conflicts_between_tools_and_shadowed_app_keys(self):
  rows = [
   {"component": "hammerspoon", "mode": "global", "key": "right-cmd+c", "description": "Cardinal"},
   {"component": "initials", "mode": "global", "key": "right-cmd+c", "description": "Sift"},
   {"component": "hammerspoon", "mode": "global", "key": "cmd+h", "description": "delete"},
   {"component": "sift", "mode": "app:Sift", "key": "cmd+h", "description": "hide"},
   {"component": "sift", "mode": "app:Sift", "key": "cmd+y", "description": "history"},
   {"component": "hammerspoon", "mode": "finder", "key": "cmd+shift+n", "description": "folder"},
  ]
  issues = localkeys.conflicts(rows, self.home)
  self.assertEqual(len(issues), 2, issues)
  self.assertTrue(any("claimed twice: right-cmd+c" in i for i in issues))
  self.assertTrue(any("Sift key cmd+h" in i for i in issues))
  # Turning Hammerspoon's rcmd off removes its right-⌘ claims.
  (self.home / ".config/mackit/hotkey_overrides.json").write_text(json.dumps({"features": {"rcmd": False}}))
  issues = localkeys.conflicts(rows, self.home)
  self.assertFalse(any("right-cmd" in i for i in issues), issues)

 def test_keyboard_maestro_active_hot_keys_only(self):
  folder = self.home / "Library/Application Support/Keyboard Maestro"
  folder.mkdir(parents=True)
  macros = {"MacroGroups": [
   {"Name": "mine", "Targeting": {"Targeting": "All"}, "Macros": [
    {"Name": "snippet", "Triggers": [{"MacroTriggerType": "HotKey", "KeyCode": 9, "Modifiers": 768}]},
    {"Name": "off", "IsActive": False, "Triggers": [{"MacroTriggerType": "HotKey", "KeyCode": 35, "Modifiers": 256}]},
   ]},
   {"Name": "word", "IsActive": False, "Macros": [
    {"Name": "style", "Triggers": [{"MacroTriggerType": "HotKey", "KeyCode": 46, "Modifiers": 4864}]}]},
  ]}
  (folder / "Keyboard Maestro Macros.plist").write_bytes(plistlib.dumps(macros))
  rows = localkeys.keyboard_maestro_rows(self.home)
  self.assertEqual([(r["key"], r["description"], r["mode"]) for r in rows], [("cmd+shift+v", "snippet", "global")])


if __name__ == "__main__":
 unittest.main()
