-- 核心工具函数库
local settings = require("lib.settings")

local M = {}

-- ═══════════════════════════════════════════════════════════════════════════
-- 统一显示（HUD 浮层，所有模块共用这一个入口）
-- kind: "info"(默认) | "success" | "error" | "detail"
-- ═══════════════════════════════════════════════════════════════════════════

local DISPLAY_CONFIG = {
    info    = { icon = "ℹ️", duration = 2 },
    success = { icon = "✅", duration = 2 },
    error   = { icon = "❌", duration = 3 },
    detail  = { icon = "📋", duration = 5 },
}

-- 由 hotkey_manager 在按键触发时写入（如 "⌘⌃⇧;"），3 秒后清空
M.current_hotkey = nil

-- ═══════════════════════════════════════════════════════════════════════════
-- 富 HUD 卡片（hs.canvas 绘制圆角卡 + 左侧 accent 条 + SF 字体）
-- 所有模块的 HUD 统一入口；display() 也走这里，不再用 hs.alert 的 ASCII 拼贴
-- opts = { eyebrow, title, subtitle, rows = {...},
--          kind = "success|warn|error|info", duration }
-- ═══════════════════════════════════════════════════════════════════════════

local CARD_ACCENT = {
    success = { red = 0.20, green = 0.83, blue = 0.60, alpha = 1 },
    warn    = { red = 0.98, green = 0.75, blue = 0.20, alpha = 1 },
    error   = { red = 0.97, green = 0.44, blue = 0.44, alpha = 1 },
    info    = { red = 0.38, green = 0.65, blue = 0.98, alpha = 1 },
}

-- 估算文本占几行：CJK 记 2 个半角单位，其余记 1
local function estimateLines(text, fontSize, width)
    local units = 0
    for _, cp in utf8.codes(text or "") do
        units = units + (cp > 0x2000 and 2 or 1)
    end
    local perLine = math.max(1, math.floor(width / (fontSize * 0.55)))
    return math.max(1, math.ceil(units / perLine))
end

M._card = nil

function M.card(opts)
    opts = opts or {}
    local accent   = CARD_ACCENT[opts.kind or "info"] or CARD_ACCENT.info
    local dim       = { red = accent.red, green = accent.green, blue = accent.blue, alpha = 0.95 }
    local duration = opts.duration or 3.5
    local rows     = opts.rows or {}

    local W        = 440
    local PAD      = 22
    local STRIPE_X = 18
    local STRIPE_W = 5
    local TEXT_X   = STRIPE_X + STRIPE_W + 16
    local TEXT_W   = W - TEXT_X - PAD

    local elements = {
        { type = "rectangle", action = "fill",
          roundedRectRadii = { xRadius = 16, yRadius = 16 },
          fillColor   = { red = 0.10, green = 0.10, blue = 0.11, alpha = 0.97 },
          strokeColor = { white = 1, alpha = 0.07 }, strokeWidth = 1 },
    }

    local y = PAD
    if opts.eyebrow then
        table.insert(elements, { type = "text", text = opts.eyebrow,
            textFont = ".AppleSystemUIFont", textSize = 11,
            textColor = dim,
            frame = { x = TEXT_X, y = y, w = TEXT_W, h = 15 } })
        y = y + 18
    end
    if opts.title then
        local lines = math.min(3, estimateLines(opts.title, 19, TEXT_W))
        local h = lines * 25
        table.insert(elements, { type = "text", text = opts.title,
            textFont = ".AppleSystemUIFont", textSize = 19,
            textColor = { white = 1, alpha = 0.98 },
            frame = { x = TEXT_X, y = y, w = TEXT_W, h = h + 4 } })
        y = y + h + 4
    end
    if opts.subtitle then
        local lines = math.min(3, estimateLines(opts.subtitle, 13.5, TEXT_W))
        local h = lines * 19
        table.insert(elements, { type = "text", text = opts.subtitle,
            textFont = ".AppleSystemUIFont", textSize = 13.5,
            textColor = { white = 0.66, alpha = 1 },
            frame = { x = TEXT_X, y = y, w = TEXT_W, h = h + 2 } })
        y = y + h + (#rows > 0 and 8 or 2)
    end
    for _, r in ipairs(rows) do
        table.insert(elements, { type = "text", text = r,
            textFont = "Menlo-Regular", textSize = 13,
            textColor = { white = 0.80, alpha = 1 },
            frame = { x = TEXT_X, y = y, w = TEXT_W, h = 19 } })
        y = y + 21
    end
    local H = y + PAD - 2

    -- accent 条（圆角竖条，置于背景之上、文字之下）
    table.insert(elements, 2, { type = "rectangle", action = "fill",
        roundedRectRadii = { xRadius = 2.5, yRadius = 2.5 },
        fillColor = accent,
        frame = { x = STRIPE_X, y = PAD, w = STRIPE_W, h = H - PAD * 2 } })

    local scr = hs.screen.mainScreen():frame()
    local cv = hs.canvas.new({
        x = scr.x + (scr.w - W) / 2,
        y = scr.y + scr.h * 0.15,
        w = W, h = H,
    })
    cv:appendElements(elements)
    cv:level(hs.canvas.windowLevels.overlay)

    if M._card then M._card:delete() end   -- 不堆叠，新卡覆盖旧卡
    cv:show(0.12)
    M._card = cv
    hs.timer.doAfter(duration, function()
        if M._card == cv then
            cv:delete(0.3)
            M._card = nil
        end
    end)
end

-- 统一 HUD 入口：module(eyebrow) + message(title) + kind(accent 色) → 卡片
-- eyebrow = 触发热键（若有）+ 模块名，保留来源信息
function M.display(module, message, kind)
    local cfg = DISPLAY_CONFIG[kind or "info"] or DISPLAY_CONFIG.info
    local accentKind = (kind == "detail") and "info" or (kind or "info")
    local eyebrow = M.current_hotkey
        and (M.current_hotkey .. "   ·   " .. module)
        or module
    M.card({
        eyebrow  = eyebrow,
        title    = message,
        kind     = accentKind,
        duration = cfg.duration,
    })
    print(string.format("%s [%s] %s", cfg.icon, module, message))
end

function M.log(module, message)
    print(string.format("[%s] %s", module, message))
end

-- ═══════════════════════════════════════════════════════════════════════════
-- 文件系统操作
-- ═══════════════════════════════════════════════════════════════════════════

function M.fileExists(path)
    return hs.fs.attributes(path) ~= nil
end

function M.getDirectory(path)
    return path:match("(.*/)")
end

-- ═══════════════════════════════════════════════════════════════════════════
-- Finder 操作
-- ═══════════════════════════════════════════════════════════════════════════

function M.getFinderDir()
    local script = [[
        tell application "Finder"
            if (count of (selection as list)) > 0 then
                set firstItem to item 1 of (selection as list)
                if class of firstItem is folder then
                    POSIX path of (firstItem as alias)
                else
                    POSIX path of (container of firstItem as alias)
                end if
            else
                POSIX path of (insertion location as alias)
            end if
        end tell
    ]]
    local ok, result = hs.osascript.applescript(script)
    return ok and result and result:gsub("%s+$", "") or os.getenv("HOME")
end

function M.getSelectedFile()
    local script = [[
        tell application "Finder"
            if (count of (selection as list)) > 0 then
                POSIX path of (item 1 of (selection as list) as alias)
            else
                ""
            end if
        end tell
    ]]
    local ok, result = hs.osascript.applescript(script)
    return ok and result and result ~= "" and result:gsub("%s+$", "") or nil
end

function M.getSelectedFiles()
    -- 分隔符用 linefeed：文件名常含逗号/空格（旧逗号分隔会切碎路径），含换行的文件名
    -- 理论上存在但实际几乎不出现，是各分隔符里唯一安全的选择
    local script = [[
        tell application "Finder"
            set selectedItems to selection as list
            set posixPaths to {}
            if (count of selectedItems) > 0 then
                repeat with i from 1 to count of selectedItems
                    set thisItem to item i of selectedItems
                    set end of posixPaths to POSIX path of (thisItem as alias)
                end repeat
                set AppleScript's text item delimiters to linefeed
                set pathsText to posixPaths as text
                set AppleScript's text item delimiters to ""
                return pathsText
            else
                return ""
            end if
        end tell
    ]]
    local ok, result = hs.osascript.applescript(script)
    if not ok or not result or result == "" then return {} end

    local files = {}
    for file in result:gmatch("[^\n]+") do
        local path = file:gsub("\r$", "")
        if path ~= "" then table.insert(files, path) end
    end
    return files
end

-- ═══════════════════════════════════════════════════════════════════════════
-- 脚本执行
-- ═══════════════════════════════════════════════════════════════════════════

function M.runScript(scriptName, callback, ...)
    local scriptPath = settings.scripts_dir .. "/" .. scriptName
    if not M.fileExists(scriptPath) then
        M.display("Script", "脚本不存在: " .. scriptName, "error")
        return nil
    end

    local args = { scriptPath, ... }
    local task = hs.task.new("/bin/bash", callback, args)
    task:setWorkingDirectory(settings.scripts_dir)
    task:start()
    return task
end

-- ═══════════════════════════════════════════════════════════════════════════
-- 应用控制
-- ═══════════════════════════════════════════════════════════════════════════

function M.ensureApp(appName)
    -- 不同步等待（usleep 会阻塞 HS 主线程）；未起时只触发启动、返回 nil，
    -- 由 runInApp 的 doAfter(1) 重试兜底——冷启动至少留 1s 缓冲再发键击
    local app = hs.application.find(appName)
    if not app then hs.application.open(appName) end
    return app
end

local RUN_IN_APP_MAX_TRIES = 8
function M.runInApp(appName, command, newTabKeys, _attempt)
    local attempt = _attempt or 1
    local app = M.ensureApp(appName)
    if not app then
        if attempt >= RUN_IN_APP_MAX_TRIES then
            M.display("App", appName .. " 启动失败，命令未执行", "error")
            return
        end
        hs.timer.doAfter(1, function() M.runInApp(appName, command, newTabKeys, attempt + 1) end)
        return
    end

    app:activate()
    hs.timer.doAfter(0.2, function()
        if newTabKeys then
            hs.eventtap.keyStroke(newTabKeys[1], newTabKeys[2])
        end
        hs.timer.doAfter(0.3, function()
            local old = hs.pasteboard.getContents()
            hs.pasteboard.setContents(command)
            hs.timer.doAfter(0.1, function()
                hs.eventtap.keyStroke({ "cmd" }, "v")
                hs.timer.doAfter(0.1, function()
                    hs.eventtap.keyStroke({}, "return")
                    if old then
                        hs.timer.doAfter(0.1, function()
                            hs.pasteboard.setContents(old)
                        end)
                    end
                end)
            end)
        end)
    end)
end

-- ═══════════════════════════════════════════════════════════════════════════
-- AppleScript 执行
-- ═══════════════════════════════════════════════════════════════════════════

function M.applescript(script, successMsg, errorMsg)
    local ok, result = hs.osascript.applescript(script)
    if ok then
        if successMsg then M.display("AppleScript", successMsg, "success") end
        return result
    else
        if errorMsg then M.display("AppleScript", errorMsg, "error") end
        return nil
    end
end

return M

