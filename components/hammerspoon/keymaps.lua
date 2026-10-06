-- 动作声明表（SoT：条数以本表为准，菜单栏 ⌨ 动态统计，勿在注释/文档写死数字）
-- 现状（2026-10-06 起）：Karabiner 只做键到键的映射，动作键由 skhd 绑定并执行、弹系统通知
--（components/yabai/config/skhd/hotkeys.json 与 components/yabai/scripts/actions/），
-- 不经 hs 命令行、不调 mackit_run；本人决定不再使用 Hammerspoon，本机已退出，启动清单也不再拉起它。
-- 本表因此不被任何按键调用，只在两种情况下还有用：
--   1) 用 mackit restore 回到“Karabiner 监听、Hammerspoon 执行”的那一代配置时，规则按这里的 module.func 调用；
--   2) 有人手动打开 Hammerspoon 时，菜单栏和帮助卡照此显示。
-- 本人确认直连版本各键都正常后，本表和 modules/ 里对应的动作可以整体删除（见 handoffs/current.md）。
-- Hammerspoon 自己不监听任何按键（tests/test_native.py 核对）。
-- 键到键的映射（⌘H 删除、Ctrl+HJKL 方向键、右 Option → Hyper、打开系统设置）整条写在 Karabiner，不进本表。
-- 历史：2026-04-18 大迁 Raycast；2026-06-13 前端收敛部分迁回（copy/compress/file_print/
--       display/brew/lid 等现均在本表）；2026-07-12 砍 run_scripts_parallel/restartApp 死键位
--       2026-10-05 按键监听全部迁到 Karabiner，本表只留动作声明；同日晚 Karabiner 改为直接执行

local M = {
	-- ═══════════════════════════════════════════════════════════════════════
	-- 应用控制（Finder 专用）
	-- ═══════════════════════════════════════════════════════════════════════
	{
		mods = { "cmd", "ctrl", "shift" },
		key = "t",
		desc = "终端在此处打开",
		module = "apps",
		func = "open_terminal",
		scope = "finder"
	},
	{
		mods = { "cmd", "ctrl", "shift" },
		key = "i",
		desc = "Nvim 编辑文件",
		module = "apps",
		func = "open_nvim",
		scope = "finder"
	},
	{
		mods = { "cmd", "shift" },
		key = "n",
		desc = "创建新文件夹",
		module = "apps",
		func = "create_folder",
		scope = "finder"
	},
	{
		mods = { "cmd", "alt" },
		key = "n",
		desc = "在当前目录打开新 Finder 窗口",
		module = "apps",
		func = "open_finder_here",
		scope = "finder"
	},

	-- ═══════════════════════════════════════════════════════════════════════
	-- 文件操作（Finder 专用）
	-- ═══════════════════════════════════════════════════════════════════════

	-- ═══════════════════════════════════════════════════════════════════════
	-- 媒体控制（全局）
	-- ═══════════════════════════════════════════════════════════════════════
	{
		mods = { "cmd", "ctrl", "shift" },
		key = ";",
		desc = "播放/暂停",
		module = "media",
		func = "togglePlayback",
		scope = "global"
	},
	{
		mods = { "cmd", "ctrl", "shift" },
		key = "'",
		desc = "下一首",
		module = "media",
		func = "nextTrack",
		scope = "global"
	},

	-- ═══════════════════════════════════════════════════════════════════════
	-- 系统工具（全局）
	-- ═══════════════════════════════════════════════════════════════════════
	-- 2026-06-13 前端收敛:display/brew/lid 从 raycast 迁入 hammerspoon(原 system.lua 函数已存在,补绑定)
	{
		mods = { "cmd", "ctrl", "alt" },
		key = "l",
		desc = "合盖休眠开关(防睡)",
		module = "system",
		func = "lid_sleep_toggle",
		scope = "global"
	},
	{
		mods = { "cmd", "ctrl", "alt" },
		key = "b",
		desc = "Homebrew 全量维护",
		module = "system",
		func = "brew_maintain",
		scope = "global"
	},
	{
		mods = { "cmd", "ctrl", "alt" },
		key = "p",
		desc = "全仓 smart-push(批量 commit&push 所有改动 repo)",
		module = "system",
		func = "git_smart_push",
		scope = "global"
	},

	-- ═══════════════════════════════════════════════════════════════════════
	-- 窗口管理（全局）
	-- ═══════════════════════════════════════════════════════════════════════
	{
		mods = { "cmd", "ctrl", "shift" },
		key = "y",
		desc = "启停 Yabai",
		module = "window",
		func = "toggle_yabai",
		scope = "global"
	},
	-- 2026-06-13 精简：删 toggle_float(f)/organize(o)/restart_yabai(e) 三个低频动作
	-- (restart 走 CLI `yabai --restart-service`；float/organize 日常用不上)
	{
		mods = { "cmd", "ctrl", "shift" },
		key = "m",
		desc = "切换鼠标跟焦 (mouse follows focus)",
		module = "window",
		func = "toggle_mouse",
		scope = "global"
	},

	-- ═══════════════════════════════════════════════════════════════════════
	-- 帮助（Hyper = 右 Option，由 Karabiner 映射为 ⇧⌘⌃）
	-- ═══════════════════════════════════════════════════════════════════════
}

M.right_command = {
	d = "DingTalk",
	b = "Dia",
	m = "Music",
	f = "Finder",
	t = "Ghostty",
	s = "moomoo", -- s=stock 股票 (m 已让给 Music)
	c = "Sift", -- c 原为 Cardinal；2026-09-23 换成替代它的 Sift，右⌘+C 习惯不变
}
-- 仅微信未运行时生效：Karabiner 按变量 mackit_wechat_launch 决定截下还是放行（modules/apps.lua 维护）
M.wechat = {mods={"ctrl","alt"}, key="w", desc="打开微信", module="apps", func="wechat_launch"}
return M
