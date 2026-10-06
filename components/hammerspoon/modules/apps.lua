-- 应用控制模块
local utils = require("lib.utils")
local settings = require("lib.settings")

local M = {}

-- ═══════════════════════════════════════════════════════════════════════════
-- 终端控制
-- ═══════════════════════════════════════════════════════════════════════════

local terminal_handlers = {
    Ghostty = function(dir)
        utils.runInApp("Ghostty", string.format('cd "%s"', dir), { "cmd", "n" })
    end,
    Warp = function(dir)
        utils.runInApp("Warp", string.format('cd "%s"', dir), { "cmd", "t" })
    end,
    Terminal = function(dir)
        utils.runInApp("Terminal", string.format('cd "%s"', dir), { "cmd", "t" })
    end,
}

function M.open_terminal()
    local dir = utils.getFinderDir()
    local handler = terminal_handlers[settings.preferred_terminal]
    if handler then
        handler(dir)
        utils.display(settings.preferred_terminal, "已打开 " .. hs.fs.displayName(dir), "success")
    end
end

-- ═══════════════════════════════════════════════════════════════════════════
-- Nvim 编辑
-- ═══════════════════════════════════════════════════════════════════════════

function M.open_nvim()
    local file = utils.getSelectedFile()
    if not file then return utils.display("Nvim", "没有选中文件", "error") end

    local dir = utils.getDirectory(file) or "."
    utils.runInApp("Ghostty", string.format('cd "%s" && nvim "%s"', dir, file), { "cmd", "n" })
    utils.display("Nvim", "已打开 " .. hs.fs.displayName(file), "success")
end

-- ═══════════════════════════════════════════════════════════════════════════
-- Finder 操作
-- ═══════════════════════════════════════════════════════════════════════════

function M.create_folder()
    local dir = utils.getFinderDir()
    if not dir then return utils.display("Finder", "无法获取当前目录", "error") end

    local base, counter = "untitled folder", 2
    local name = base

    while hs.fs.attributes(dir .. "/" .. name, "mode") do
        name = base .. " " .. counter
        counter = counter + 1
    end

    local path = dir .. "/" .. name
    if hs.fs.mkdir(path) then
        utils.applescript(string.format([[
            tell application "Finder"
                activate
                select POSIX file "%s"
            end tell
        ]], path))
        utils.display("Finder", "已创建 " .. name, "success")
    else
        utils.display("Finder", "创建文件夹失败", "error")
    end
end

function M.open_finder_here()
    local dir = utils.getFinderDir()
    if not dir then return utils.display("Finder", "无法获取当前目录", "error") end

    utils.applescript(string.format([[
        tell application "Finder"
            activate
            make new Finder window to folder (POSIX file "%s")
        end tell
    ]], dir))
    utils.display("Finder", "新窗口: " .. hs.fs.displayName(dir), "success")
end

-- ═══════════════════════════════════════════════════════════════════════════
-- 微信键 ⌃⌥W（只在微信未运行时生效）
-- 按键由 Karabiner 监听：变量 mackit_wechat_launch 为 1 时截下并调 apps.wechat_launch，
-- 为 0 或未设置时原样放行，微信自己的全局快捷键照常收到。
-- 本模块按微信的启动/退出维护这个变量；Hammerspoon 退出或重载前置 0，按键不会被白白吃掉。
-- ═══════════════════════════════════════════════════════════════════════════

local KARABINER_CLI = "/Library/Application Support/org.pqrs/Karabiner-Elements/bin/karabiner_cli"
local wechat_watcher = nil

local function set_wechat_launch(on)
    if not hs.fs.attributes(KARABINER_CLI) then return end
    hs.execute(string.format([['%s' --set-variables '{"mackit_wechat_launch":%d}']], KARABINER_CLI, on and 1 or 0))
end

function M.wechat_launch()
    if hs.application.find("WeChat") then return end
    hs.application.open("WeChat")
    hs.timer.doAfter(0.5, function()
        hs.eventtap.keyStroke({}, "return")
    end)
end

-- enabled == false：功能关闭，只把变量清 0
function M.init_wechat_hotkey(enabled)
    if enabled == false then return set_wechat_launch(false) end

    -- 监听微信启动/退出
    wechat_watcher = hs.application.watcher.new(function(appName, eventType)
        if appName == "WeChat" then
            if eventType == hs.application.watcher.launched then
                set_wechat_launch(false)
            elseif eventType == hs.application.watcher.terminated then
                set_wechat_launch(true)
            end
        end
    end)
    wechat_watcher:start()

    -- 初始状态
    set_wechat_launch(not hs.application.find("WeChat"))
    hs.shutdownCallback = function() set_wechat_launch(false) end
end

return M

