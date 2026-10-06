-- 动作分发器
-- Hammerspoon 自己不监听按键：Karabiner 监听后经 hs 命令行调 mackit_run("<module>.<func>")，
-- 这里只执行 keymaps.lua 声明过、且未被停用的动作
-- 支持通过 hotkey_overrides.json 停用单条动作（M3）

local utils = require("lib.utils")

local M = {}

-- "<module>.<func>" → { fn = 包装后的动作, scope = 声明的 scope }；init() 重建
local actions = {}

-- 读取 hotkey_overrides.json，返回 {id: {enabled=bool}} 的 map
-- id 格式: "<scope>:<mods>:<key>"，例如 "global:cmd+ctrl+shift:1"
local function load_overrides()
    local path = require("lib.settings").overrides_path
    local f = io.open(path, "r")
    if not f then return {} end
    local content = f:read("*all")
    f:close()
    if not content or content == "" then return {} end

    local ok, decoded = pcall(hs.json.decode, content)
    if not ok or type(decoded) ~= "table" then
        utils.log("HotkeyManager", "overrides.json 解析失败，已忽略")
        return {}
    end
    return decoded.hotkeys or {}
end

-- id 格式 "<scope>:<mods>:<key>"；菜单栏/网页端写 override 必须复用此函数，
-- 否则算出的 id 与分发端不一致 → toggle 写了但不生效（暴露为 M.* 供 menubar 复用）
function M.hotkey_id(hk)
    return (hk.scope or "global") .. ":" .. table.concat(hk.mods, "+") .. ":" .. hk.key
end

-- Karabiner 规则里写的动作 id
function M.action_id(hk)
    return hk.module .. "." .. hk.func
end

-- 快捷键显示（如 "⌘⌃⇧;"），给 HUD 前缀 + 菜单栏用
local MOD_SYMBOLS = { cmd = "⌘", ctrl = "⌃", alt = "⌥", shift = "⇧" }
function M.hotkey_display(hk)
    local parts = {}
    for _, mod in ipairs({ "cmd", "ctrl", "alt", "shift" }) do
        for _, m in ipairs(hk.mods) do
            if m == mod then table.insert(parts, MOD_SYMBOLS[mod]); break end
        end
    end
    table.insert(parts, hk.key:upper())
    return table.concat(parts)
end

-- 写一行使用日志（与 ~/.useful_scripts_usage.log 共享同一格式）
local USAGE_LOG = os.getenv("HOME") .. "/.useful_scripts_usage.log"
local function log_usage(hk)
    if not require("lib.settings").usage_log then return end
    local f = io.open(USAGE_LOG, "a")
    if not f then return end
    local script = "hs:" .. hk.module .. "." .. hk.func
    f:write(string.format("%s,%s,hammerspoon\n", os.date("%Y-%m-%d %H:%M:%S"), script))
    f:close()
end

-- 包一层 fn：执行时把按键显示写进 utils.current_hotkey，异步 HUD 也能带前缀
local function wrap_with_context(fn, hk)
    local label = M.hotkey_display(hk)
    return function()
        log_usage(hk)
        utils.current_hotkey = label
        local ok, err = pcall(fn)
        if not ok then utils.log("Hotkey", tostring(err)) end
        -- 3 秒后清除，让慢回调也能带上前缀
        hs.timer.doAfter(3, function()
            if utils.current_hotkey == label then utils.current_hotkey = nil end
        end)
    end
end

-- 重载前清空动作表
function M.cleanup()
    actions = {}
end

-- 显示快捷键帮助（统一走 utils.card 卡片：标题 + 分组行）
function M.show_help()
    local hotkey_config = require("keymaps")

    local sections = {
        finder = { title = "Finder 专用", items = {} },
        global = { title = "全局", items = {} }
    }

    for _, hk in ipairs(hotkey_config) do
        -- 未知 scope 兜底进 global，不因新 scope 崩帮助卡
        local section = sections[hk.scope or "global"] or sections.global
        table.insert(section.items,
            string.format("%-14s %s", M.hotkey_display(hk), hk.desc))
    end

    -- 固定顺序：先 finder 再 global
    local rows = {}
    for _, key in ipairs({ "finder", "global" }) do
        local section = sections[key]
        if #section.items > 0 then
            if #rows > 0 then table.insert(rows, "") end
            table.insert(rows, "— " .. section.title .. " —")
            for _, item in ipairs(section.items) do
                table.insert(rows, item)
            end
        end
    end

    utils.card({
        eyebrow  = "⌘⌃⇧H",
        title    = "Hammerspoon 快捷键",
        rows     = rows,
        kind     = "info",
        duration = 15,
    })
end

function M.is_enabled(ov)
 if ov ~= nil then return ov.enabled ~= false end
 return require("lib.settings").enable_shortcuts
end

local function finder_frontmost()
    local app = hs.application.frontmostApplication()
    return app ~= nil and app:bundleID() == "com.apple.finder"
end

-- Karabiner 的入口：hs -c 'mackit_run("<module>.<func>")'
-- 未声明、已停用、或 Finder 专用动作不在 Finder 前台时返回 false，不执行。
-- 先返回再执行：命令行不等动作跑完。
function M.run(id)
    local action = actions[id]
    if not action then
        utils.log("HotkeyManager", "未声明或已停用的动作: " .. tostring(id))
        return false
    end
    if action.scope == "finder" and not finder_frontmost() then return false end
    hs.timer.doAfter(0, action.fn)
    return true
end

-- 只读查询：该动作当前是否会被执行（给回读与测试用）
function M.is_runnable(id)
    return actions[id] ~= nil
end

-- 登记全部已启用的动作，返回数量（不含微信键，它由 settings.wechat 单独开关）
function M.init()
    local hotkey_config = require("keymaps")
    local settings = require("lib.settings")
    local overrides = load_overrides()
    local count = 0
    local skipped = 0

    -- 加载模块缓存
    local modules = {}
    actions = {}

    local function register(hk)
        -- 获取模块
        local mod
        if hk.module == "_hotkey_manager" then
            mod = M
        else
            if not modules[hk.module] then
                local ok, m = pcall(require, "modules." .. hk.module)
                if ok then modules[hk.module] = m end
            end
            mod = modules[hk.module]
        end

        -- 获取函数
        local fn = mod and mod[hk.func]
        if not fn then
            utils.log("HotkeyManager", "函数未找到: " .. hk.module .. "." .. hk.func)
            return false
        end

        -- 包一层把按键 label 注入到 utils.current_hotkey
        actions[M.action_id(hk)] = { fn = wrap_with_context(fn, hk), scope = hk.scope }
        return true
    end

    for _, hk in ipairs(hotkey_config) do
        -- 菜单栏/网页端启停 override
        if not M.is_enabled(overrides[M.hotkey_id(hk)]) then
            skipped = skipped + 1
        elseif register(hk) then
            count = count + 1
        end
    end

    if settings.wechat and hotkey_config.wechat then register(hotkey_config.wechat) end

    if skipped > 0 then
        utils.log("HotkeyManager", string.format("已登记 %d 个动作，跳过 %d 个（override disabled）", count, skipped))
    else
        utils.log("HotkeyManager", "已登记 " .. count .. " 个动作")
    end
    return count
end

return M
