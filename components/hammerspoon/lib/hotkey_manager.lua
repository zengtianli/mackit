-- 快捷键管理器
-- 自动绑定 config/hotkeys.lua 中定义的快捷键
-- 支持通过 hotkey_overrides.json 禁用单条快捷键（M3）

local utils = require("lib.utils")

local M = {}

-- 存储应用专用热键
local app_hotkeys = {}
local app_watcher = nil

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
-- 否则算出的 id 与绑定端不一致 → toggle 写了但不生效（暴露为 M.* 供 menubar 复用）
function M.hotkey_id(hk)
    return (hk.scope or "global") .. ":" .. table.concat(hk.mods, "+") .. ":" .. hk.key
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

-- 包一层 fn：按下时把 hotkey 显示写进 utils.current_hotkey，异步 HUD 也能带前缀
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

-- 清理监听器
function M.cleanup()
    if app_watcher then
        app_watcher:stop()
        app_watcher = nil
    end
    app_hotkeys = {}
end

-- 注册应用专用热键
local function register_app_hotkey(appName, mods, key, desc, fn)
    if not app_hotkeys[appName] then
        app_hotkeys[appName] = {}
    end

    -- 第 3 参数 nil 避免 HS 自动弹 "<mods><key>: <desc>" HUD（desc 留给 show_help 用）
    local hotkey = hs.hotkey.new(mods, key, nil, fn)
    if hotkey then
        table.insert(app_hotkeys[appName], hotkey)

        -- 根据当前前台应用决定是否启用
        if hs.application.frontmostApplication():name() == appName then
            hotkey:enable()
        end
    end
end

-- 启动应用监听器
local function start_app_watcher()
    if app_watcher or not next(app_hotkeys) then return end

    app_watcher = hs.application.watcher.new(function(appName, eventType, _)
        if eventType == hs.application.watcher.activated then
            for registered_app, hotkeys in pairs(app_hotkeys) do
                for _, hotkey in ipairs(hotkeys) do
                    if registered_app == appName then
                        hotkey:enable()
                    else
                        hotkey:disable()
                    end
                end
            end
        elseif eventType == hs.application.watcher.deactivated then
            if app_hotkeys[appName] then
                for _, hotkey in ipairs(app_hotkeys[appName]) do
                    hotkey:disable()
                end
            end
        end
    end)
    app_watcher:start()
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

-- 初始化所有快捷键
function M.init()
    local hotkey_config = require("keymaps")
    local overrides = load_overrides()
    local count = 0
    local skipped = 0

    -- 加载模块缓存
    local modules = {}

    for _, hk in ipairs(hotkey_config) do
        -- 网页端启停 override
        local ov = overrides[M.hotkey_id(hk)]
        if not M.is_enabled(ov) then
            skipped = skipped + 1
            goto continue
        end

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
            goto continue
        end

        -- 绑定快捷键（包一层把 hotkey label 注入到 utils.current_hotkey）
        local wrapped = wrap_with_context(fn, hk)
        if hk.scope == "finder" then
            register_app_hotkey("Finder", hk.mods, hk.key, hk.desc, wrapped)
        else
            hs.hotkey.bind(hk.mods, hk.key, nil, wrapped)
        end
        count = count + 1

        ::continue::
    end

    -- 启动应用监听
    start_app_watcher()

    if skipped > 0 then
        utils.log("HotkeyManager", string.format("已注册 %d 个快捷键，跳过 %d 个（override disabled）", count, skipped))
    else
        utils.log("HotkeyManager", "已注册 " .. count .. " 个快捷键")
    end
    return count
end

return M

