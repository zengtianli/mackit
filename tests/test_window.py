"""窗口页引擎：数据源 → 生成文件，校验、备份与 App 协议。不触碰本机 yabai/skhd。"""
import json, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mackit import window  # noqa: E402


class WindowEngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mackit-window-")
        self.root = Path(self.temp.name) / "src"
        shutil.copytree(ROOT / "components/yabai", self.root / "components/yabai")
        self.state = Path(self.temp.name) / "state"

    def tearDown(self):
        self.temp.cleanup()

    def test_checked_in_files_are_generated_from_json(self):
        # 生成门：仓库里的 yabairc / skhdrc 必须是 JSON 源渲染的结果，手改会在这里失败。
        data = window.load(ROOT)
        p = window.paths(ROOT)
        self.assertEqual(p["yabairc"].read_text(), window.render_yabairc(data))
        self.assertEqual(p["skhdrc"].read_text(), window.render_skhdrc(data["hotkeys"]))
        self.assertGreaterEqual(len(data["hotkeys"]), 11)

    def test_skhd_syntax_and_hex_for_punctuation(self):
        self.assertEqual(window.skhd_key("ctrl+shift+y"), "ctrl + shift - y")
        self.assertEqual(window.skhd_key("ctrl+shift+;"), "ctrl + shift - 0x29")
        self.assertEqual(window.skhd_key("cmd+alt+space"), "cmd + alt - space")
        self.assertEqual(window.canonical_key("shift+ctrl+Y"), "ctrl+shift+y")

    def test_invalid_values_rejected_before_any_write(self):
        before = {k: v.read_text() for k, v in window.paths(self.root).items()}
        bad = [
            {"settings": {"layout": "grid"}},
            {"settings": {"window_gap": 999}},
            {"settings": {"no_such_key": "on"}},
            {"hotkeys": [{"key": "y", "action": "full"}]},                      # 没有修饰键
            {"hotkeys": [{"key": "ctrl+y", "action": "full"}, {"key": "ctrl+y", "action": "left"}]},  # 重复
            {"hotkeys": [{"key": "ctrl+y", "action": "rm-rf"}]},                # 未知动作
            {"hotkeys": [{"key": "ctrl+y", "command": "a\nb"}]},                # 多行命令
            {"rules": [{"app": "Evil\"; rm", "manage": "off"}]},               # 应用名注入
            {"rules": [{"app": "Finder"}]},                                     # 空规则
        ]
        for request in bad:
            with self.subTest(request=request):
                with self.assertRaises(ValueError):
                    window.save(self.root, self.state, request)
        after = {k: v.read_text() for k, v in window.paths(self.root).items()}
        self.assertEqual(before, after)

    def test_save_renders_backs_up_and_yabairc_is_valid_bash(self):
        request = {"settings": {"layout": "bsp", "window_gap": "8", "split_ratio": 0.6},
                   "rules": [{"app": "System Settings", "manage": "off"}],
                   "hotkeys": [{"key": "cmd+alt+f", "action": "full", "note": "全屏"},
                               {"key": "ctrl+alt+h", "command": "yabai -m window --focus west"}]}
        saved = window.save(self.root, self.state, request)
        self.assertTrue(Path(saved["backup"]).is_dir())
        rc = (self.root / "components/yabai/config/yabairc").read_text()
        self.assertIn("yabai -m config layout bsp", rc)
        self.assertIn("yabai -m config window_gap 8", rc)
        self.assertIn('app="^System\\ Settings$" manage=off', rc)
        self.assertEqual(subprocess.run(["bash", "-n", str(self.root / "components/yabai/config/yabairc")]).returncode, 0)
        skhd = (self.root / "components/yabai/config/skhd/skhdrc").read_text()
        self.assertIn("cmd + alt - f : $HOME/.config/yabai/scripts/window/position.sh full", skhd)
        self.assertIn("ctrl + alt - h : yabai -m window --focus west", skhd)
        self.assertEqual(window.load(self.root)["settings"]["window_gap"], 8)


class WindowBridgeTests(unittest.TestCase):
    """App 协议：演示 HOME 只读快照；未安装时拒绝保存。"""
    def test_snapshot_lists_specs_actions_and_digest(self):
        with tempfile.TemporaryDirectory(prefix="mackit-window-home-") as home:
            r = subprocess.run([sys.executable, str(ROOT / "bin/mackit"), "--home", home, "gui"],
                               input=json.dumps({"action": "windowSnapshot"}), capture_output=True, text=True)
            out = json.loads(r.stdout)
            self.assertTrue(out["ok"], out)
            w = out["window"]
            self.assertEqual({s["key"] for s in w["settingSpecs"]}, set(window.SPEC))
            self.assertIn("full", {a["id"] for a in w["actions"]})
            self.assertEqual(len(w["digest"]), 64)
            self.assertFalse(w["editable"])
            r = subprocess.run([sys.executable, str(ROOT / "bin/mackit"), "--home", home, "gui"],
                               input=json.dumps({"action": "windowSave", "digest": w["digest"], "settings": {}}), capture_output=True, text=True)
            self.assertFalse(json.loads(r.stdout)["ok"])

    def test_installed_source_save_and_external_edit_rejected(self):
        with tempfile.TemporaryDirectory(prefix="mackit-window-home-") as home:
            def call(action, **values):
                r = subprocess.run([sys.executable, str(ROOT / "bin/mackit"), "--home", home, "gui"],
                                   input=json.dumps({"action": action, **values}), capture_output=True, text=True)
                return json.loads(r.stdout)
            sel = {"profile": "developer", "components": ["yabai"]}
            preview = call("preview", **sel)
            self.assertTrue(call("apply", token=preview["token"], **sel)["ok"])
            w = call("windowSnapshot")["window"]
            self.assertTrue(w["editable"])
            base = {"digest": w["digest"], "settings": {"layout": "bsp"}, "hotkeys": w["hotkeys"], "rules": []}
            ok = call("windowSave", **base)
            self.assertTrue(ok["ok"], ok)
            src = Path(home) / ".local/share/mackit/components/yabai/config"
            self.assertIn("layout bsp", (src / "yabairc").read_text())
            (src / "settings.json").write_text('{"settings": {"layout": "stack"}, "rules": []}\n')
            stale = call("windowSave", **base)          # 旧 digest
            self.assertFalse(stale["ok"])
            self.assertIn("layout", (src / "settings.json").read_text())
            self.assertIn("stack", (src / "settings.json").read_text())


if __name__ == "__main__":
    unittest.main()
