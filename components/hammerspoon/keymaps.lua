-- 声明式快捷键配置（SoT：条数以本表为准，菜单栏 ⌨ 动态统计，勿在注释/文档写死数字）
-- 一行一个快捷键，自动绑定到对应模块函数；hotkey_overrides.json 可单条停用
-- 历史：2026-04-18 大迁 Raycast；2026-06-13 前端收敛部分迁回（copy/compress/file_print/
--       display/brew/lid 等现均在本表）；2026-07-12 砍 run_scripts_parallel/restartApp 死键位

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
	{
		mods = { "cmd", "ctrl", "shift" },
		key = "n",
		desc = "复制文件名",
		module = "system",
		func = "copy_filenames",
		scope = "finder"
	},
	{
		mods = { "cmd", "ctrl", "shift" },
		key = "c",
		desc = "复制文件名+内容",
		module = "system",
		func = "copy_names_and_content",
		scope = "finder"
	},
	{
		mods = { "cmd", "ctrl", "shift" },
		key = "z",
		desc = "压缩选中文件",
		module = "system",
		func = "compress",
		scope = "finder"
	},
	{
		mods = { "ctrl", "alt" },
		key = "v",
		desc = "粘贴到 Finder",
		module = "system",
		func = "paste_to_finder",
		scope = "finder"
	},
	{
		mods = { "cmd", "ctrl", "shift" },
		key = "9",
		desc = "打印选中文件（默认 app 打开弹打印窗口）",
		module = "system",
		func = "file_print",
		scope = "finder"
	},

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
	{
		mods = { "cmd", "ctrl", "shift" },
		key = "l",
		desc = "上一首",
		module = "media",
		func = "previousTrack",
		scope = "global"
	},
	{
		mods = { "cmd", "ctrl", "shift" },
		key = "p",
		desc = "系统媒体播放/暂停",
		module = "media",
		func = "systemPlayPause",
		scope = "global"
	},

	-- ═══════════════════════════════════════════════════════════════════════
	-- 系统工具（全局）
	-- ═══════════════════════════════════════════════════════════════════════
	{
		mods = { "cmd", "alt" },
		key = ",",
		desc = "打开系统设置",
		module = "system",
		func = "openSettings",
		scope = "global"
	},
	-- 2026-06-13 前端收敛:display/brew/lid 从 raycast 迁入 hammerspoon(原 system.lua 函数已存在,补绑定)
	{
		mods = { "cmd", "ctrl", "alt" },
		key = "4",
		desc = "外接显示器 1080p ↔ 最高原生分辨率 轮换",
		module = "system",
		func = "display_toggle",
		scope = "global"
	},
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
	{
		mods = { "cmd", "ctrl", "shift" },
		key = "g",
		desc = "切换当前 space layout (bsp ↔ float)",
		module = "window",
		func = "toggle_space_layout",
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
	-- 按键重映射（从 Karabiner 迁移，无 HUD，打字高频触发）
	-- ═══════════════════════════════════════════════════════════════════════
	{
		mods = { "cmd" },
		key = "h",
		desc = "删除字符",
		module = "keymap",
		func = "delete_char",
		scope = "global"
	},
	{
		mods = { "cmd", "alt" },
		key = "h",
		desc = "删除单词",
		module = "keymap",
		func = "delete_word",
		scope = "global"
	},
	{
		mods = { "cmd", "ctrl" },
		key = "h",
		desc = "删除到行首",
		module = "keymap",
		func = "delete_to_line_start",
		scope = "global"
	},

	-- ═══════════════════════════════════════════════════════════════════════
	-- 帮助（Hyper = Right Option）
	-- ═══════════════════════════════════════════════════════════════════════
	{
		mods = { "cmd", "ctrl", "shift" },
		key = "h",
		desc = "显示快捷键帮助",
		module = "_hotkey_manager",
		func = "show_help",
		scope = "global"
	},
}

M.right_command = {
	d = "DingTalk",
	b = "Dia",
	m = "Music",
	f = "Finder",
	t = "Ghostty",
	s = "moomoo", -- s=stock 股票 (m 已让给 Music)
	c = "Cardinal",
}
M.ctrl_vim = {
	[4]  = { {}, "left" },                -- h → 左
	[38] = { {}, "down" },                -- j → 下
	[40] = { {}, "up" },                  -- k → 上
	[37] = { {}, "right" },               -- l → 右
}
M.hyper_keycode = 61
M.wechat = {mods={"ctrl","alt"}, key="w", desc="打开微信"}
return M
