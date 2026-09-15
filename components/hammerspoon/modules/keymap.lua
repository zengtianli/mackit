-- 按键重映射
-- 从 Karabiner 迁移的键位映射
--
-- 2026-07-21 抗失效重构（对齐 rcmd.lua 同日方案，三根因逐条消除）:
--   ① 旧版用 flagsChanged 维护 right_option_held 状态——释放事件丢一次(锁屏/安全输入/唤醒)
--      就永久卡 true，之后所有按键被强加 ⌘⌃⇧、整个键盘废掉。现 keyDown 回调里直接读
--      rawFlags 的右⌥设备位，无状态不可能卡死
--   ② 回调保持微秒级：vim 导航先判 flags(位运算)再查映射表，最贵的 frontmostApplication
--      放最后短路，杜绝 kCGEventTapDisabledByTimeout
--   ③ 三个 tap 全部注册进 lib/tap_guard（30s watchdog + 唤醒/解锁重启），不再裸奔

local tap_guard = require("lib.tap_guard")

local M = {}

-- ═══════════════════════════════════════════════════════════════════════════
-- Cmd+H → Delete 系列
-- ═══════════════════════════════════════════════════════════════════════════

function M.delete_char()
	hs.eventtap.keyStroke({}, "delete", 0)
end

function M.delete_word()
	hs.eventtap.keyStroke({"alt"}, "delete", 0)
end

function M.delete_to_line_start()
	hs.eventtap.keyStroke({"cmd"}, "delete", 0)
end

-- ═══════════════════════════════════════════════════════════════════════════
-- Right Option → Hyper (Shift+Cmd+Ctrl)
-- ═══════════════════════════════════════════════════════════════════════════

-- 右⌥ 物理键的设备位 (NX_DEVICERALTKEYMASK)；hs 常量缺失时兜底 0x40
local RALT_MASK = (hs.eventtap.event.rawFlagMasks
	and hs.eventtap.event.rawFlagMasks.deviceRightAlternate) or 0x00000040

function M.init_hyper()
	-- 吃掉右 Option 自己的 flagsChanged，避免 app 看到裸 ⌥ 按下（如菜单栏高亮）
	local hyper_flags = hs.eventtap.new({ hs.eventtap.event.types.flagsChanged }, function(event)
		return event:getKeyCode() == require("keymaps").hyper_keycode -- right option
	end)

	-- 右⌥ 按住时把按键修饰替换为 Hyper；无状态：rawFlags 设备位直接判断
	local hyper_keys = hs.eventtap.new(
		{ hs.eventtap.event.types.keyDown, hs.eventtap.event.types.keyUp },
		function(event)
			if event:rawFlags() & RALT_MASK ~= 0 then
				event:setFlags({ shift = true, cmd = true, ctrl = true })
			end
			return false -- 修改后放行
		end)

	tap_guard.register("hyper_flags", hyper_flags)
	tap_guard.register("hyper_keys", hyper_keys)
	print("[Keymap] Right Option → Hyper 已启用 (无状态 rawFlags + tap_guard)")
end

-- ═══════════════════════════════════════════════════════════════════════════
-- Ctrl + Vim 导航
-- ═══════════════════════════════════════════════════════════════════════════

-- Ctrl+key → 目标按键的映射表
local ctrl_vim_map = require("keymaps").ctrl_vim

-- 终端应用列表（在这些应用中不拦截 Ctrl+HJKL）
local terminal_apps = {
	["com.apple.Terminal"] = true,
	["com.googlecode.iterm2"] = true,
	["com.mitchellh.ghostty"] = true,
	["org.alacritty"] = true,
	["net.kovidgoyal.kitty"] = true,
	["dev.warp.Warp-Stable"] = true,
}

local function is_terminal()
	local app = hs.application.frontmostApplication()
	return (app and terminal_apps[app:bundleID()]) or false
end

function M.init_vim_nav()
	local ctrl_tap = hs.eventtap.new({ hs.eventtap.event.types.keyDown }, function(event)
		-- 廉价判断在前：flags 位运算 → 映射表查询；frontmostApplication 最贵放最后
		local flags = event:getFlags()
		if not (flags.ctrl and not flags.cmd and not flags.alt and not flags.shift) then
			return false
		end
		local mapping = ctrl_vim_map[event:getKeyCode()]
		if not mapping then return false end
		if is_terminal() then return false end -- 终端里不拦截，留给 shell/vim 自己
		hs.eventtap.keyStroke(mapping[1], mapping[2], 0)
		return true -- 拦截
	end)
	tap_guard.register("ctrl_vim", ctrl_tap)
	print("[Keymap] Ctrl+Vim 导航已启用（终端除外）")
end

return M
