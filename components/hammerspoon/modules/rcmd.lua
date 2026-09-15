-- rcmd 复刻：右 ⌘ + 字母 → 聚焦/隐藏/轮换 app
-- 背景: rcmd.app 在 macOS 27 失效 (2026-06-12)，用 Hammerspoon eventtap 自实现
-- 行为对齐 rcmd 默认:
--   右⌘ + 字母 → 聚焦「名字以该字母开头」的运行中 app
--   目标已在前台 → 隐藏它 (再按一次切回来)
--   同字母多个 app → 依次轮换
--   PINNED 表钉死的映射优先 (未运行也会启动)
-- 左 ⌘ 完全不受影响；右⌘ 含 shift/alt/ctrl 的组合键放行不劫持
--
-- 2026-07-21 抗失效重构（旧版「经常失效」的 3 个根因逐条消除）:
--   ① 旧版用 flagsChanged 维护 right_cmd_held 状态——释放事件丢一次(锁屏/安全输入/唤醒)
--      状态就永久卡错。现 keyDown 回调里直接读 rawFlags 的右⌘设备位，无状态不可能卡死
--   ② 旧版在 eventtap 回调里同步跑 runningApplications/find/launchOrFocus(可达数百 ms)，
--      超时会被 macOS 以 kCGEventTapDisabledByTimeout 静默禁用整个 tap。
--      现回调只判断(<1ms)，重活 hs.timer.doAfter 延后到回调外执行
--   ③ 安全输入(密码框)/睡眠唤醒禁用 tap 后无人恢复。现托管 lib/tap_guard
--      (30s watchdog 自动拉起 + caffeinate watcher 唤醒/解锁重启)。诊断入口 M.status()

local tap_guard = require("lib.tap_guard")

local M = {}

-- 钉死映射: 字母 → app 名 (hs.application.launchOrFocus 的参数)
-- 原理 = 按角色助记，不死磕首字母 (2026-06-12 用户钦定):
--   d=钉钉 / b=browser(Dia) / m=music / f=finder / t=terminal(Ghostty)
-- 首字母撞车时让位给角色语义 (Dia 不占 d，d 给钉钉)
local PINNED = require("keymaps").right_command

local keys_tap = nil

-- 右⌘ 物理键的设备位 (NX_DEVICERCMDKEYMASK)；hs 常量缺失时兜底 0x10
local RCMD_MASK = (hs.eventtap.event.rawFlagMasks
	and hs.eventtap.event.rawFlagMasks.deviceRightCommand) or 0x00000010

-- 找所有「名字以 letter 开头」的常规运行中 app (kind==1 = 出现在 Dock)
local function running_apps_by_letter(letter)
	local matches = {}
	for _, app in ipairs(hs.application.runningApplications()) do
		local name = app:name() or ""
		if app:kind() == 1 and name:lower():sub(1, 1) == letter then
			table.insert(matches, app)
		end
	end
	table.sort(matches, function(a, b) return (a:name() or "") < (b:name() or "") end)
	return matches
end

local function handle_letter(letter)
	local pinned = PINNED[letter]
	if pinned then
		-- get = 精确名匹配，比 find 的模糊扫描快一个量级
		local app = hs.application.get(pinned)
		if app and app:isFrontmost() then
			app:hide()
		else
			hs.application.launchOrFocus(pinned)
		end
		return
	end

	local matches = running_apps_by_letter(letter)
	if #matches == 0 then return end

	-- 前台 app 在匹配列表里 → 轮换到下一个；只有它一个 → 隐藏
	local front = hs.application.frontmostApplication()
	for i, app in ipairs(matches) do
		if front and app:pid() == front:pid() then
			if #matches == 1 then
				app:hide()
			else
				matches[i % #matches + 1]:activate(true)
			end
			return
		end
	end
	matches[1]:activate(true)
end

function M.init()
	keys_tap = hs.eventtap.new({ hs.eventtap.event.types.keyDown }, function(event)
		-- 无状态: rawFlags 设备位直接区分左右 ⌘，不依赖任何跨事件跟踪
		if event:rawFlags() & RCMD_MASK == 0 then return false end
		local flags = event:getFlags()
		if flags.alt or flags.ctrl or flags.shift then return false end
		local char = hs.keycodes.map[event:getKeyCode()]
		if type(char) ~= "string" or not char:match("^%a$") then return false end
		-- 重活延后到回调外，回调保持微秒级，杜绝 kCGEventTapDisabledByTimeout
		local letter = char:lower()
		hs.timer.doAfter(0, function() handle_letter(letter) end)
		return true -- 吃掉，避免误触目标 app 的 ⌘ 快捷键
	end)
	tap_guard.register("rcmd", keys_tap)

	print("[rcmd] 右 ⌘ + 字母 切 app 已启用 (无状态 rawFlags + tap_guard)")
end

-- 诊断: hs -c 'local s=require("modules.rcmd").status() print(hs.inspect(s))'
function M.status()
	return tap_guard.status()
end

function M.cleanup()
	-- 必须走 unregister：只 stop 的话 watchdog 30s 内会把 tap 重新拉活
	tap_guard.unregister("rcmd")
	keys_tap = nil
end

return M
