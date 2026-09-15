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
-- 微信快捷键（特殊处理：只在微信未运行时生效）
-- ═══════════════════════════════════════════════════════════════════════════

local wechat_hotkey = nil
local wechat_watcher = nil

function M.init_wechat_hotkey()
    wechat_hotkey = hs.hotkey.new(require("keymaps").wechat.mods, require("keymaps").wechat.key, function()
        local app = hs.application.find("WeChat")
        if not app then
            -- 微信未运行，启动它
            hs.application.open("WeChat")
            hs.timer.doAfter(0.5, function()
                hs.eventtap.keyStroke({}, "return")
            end)
        end
        -- 微信已运行，不做任何事，让快捷键穿透给微信
    end)

    -- 监听微信启动/退出
    wechat_watcher = hs.application.watcher.new(function(appName, eventType, app)
        if appName == "WeChat" then
            if eventType == hs.application.watcher.launched then
                if wechat_hotkey then wechat_hotkey:disable() end
            elseif eventType == hs.application.watcher.terminated then
                if wechat_hotkey then wechat_hotkey:enable() end
            end
        end
    end)
    wechat_watcher:start()

    -- 初始状态
    if hs.application.find("WeChat") then
        wechat_hotkey:disable()
    else
        wechat_hotkey:enable()
    end
end

return M

