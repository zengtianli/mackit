-- 系统工具模块
local utils = require("lib.utils")
local settings = require("lib.settings")

local M = {}

-- ═══════════════════════════════════════════════════════════════════════════
-- 系统设置
-- ═══════════════════════════════════════════════════════════════════════════

function M.openSettings()
    local success = hs.application.launchOrFocus("System Settings")
    if not success then
        hs.application.launchOrFocus("System Preferences")
    end
    utils.display("System", "打开系统设置", "success")
end

-- ═══════════════════════════════════════════════════════════════════════════
-- 文件压缩
-- ═══════════════════════════════════════════════════════════════════════════

function M.compress()
    utils.runScript("finder_compress.sh", function(code, _, stderr)
        if code == 0 then
            utils.log("Compress", "压缩完成")
        else
            utils.log("Compress", "压缩失败: " .. (stderr or ""))
        end
    end)
end

-- ═══════════════════════════════════════════════════════════════════════════
-- 剪贴板工具
-- ═══════════════════════════════════════════════════════════════════════════

function M.copy_filenames()
    local files = utils.getSelectedFiles()
    if #files == 0 then return utils.display("Clipboard", "没有选中文件", "error") end

    local names = {}
    for _, path in ipairs(files) do
        table.insert(names, hs.fs.displayName(path))
    end

    hs.pasteboard.setContents(table.concat(names, "\n"))
    utils.display("Clipboard", "已复制 " .. #files .. " 个文件名", "success")
end

-- 复制文件名+内容。二进制格式(docx/doc/xlsx/pptx/pdf)走 scripts/extract_text.py
-- 抽全文（textutil/pandoc/pandas/python-pptx/pdftotext），不再吐乱码字节。
-- 异步 task：pandas/pdftotext 可能耗时，不阻塞 Hammerspoon 主线程。
function M.copy_names_and_content()
    local files = utils.getSelectedFiles()
    if #files == 0 then return utils.display("Clipboard", "没有选中文件", "error") end

    local args = { hs.configdir .. "/scripts/extract_text.py" }
    for _, path in ipairs(files) do table.insert(args, path) end

    utils.display("Clipboard", string.format("抽取 %d 个文件内容…", #files), "info")

    hs.task.new(settings.python_path, function(code, stdout, stderr)
        if stdout and stdout:gsub("%s", "") ~= "" then
            hs.pasteboard.setContents(stdout)
            if code == 0 then
                utils.display("Clipboard", string.format("已复制 %d 个文件名+内容", #files), "success")
            else
                utils.display("Clipboard", "已复制（部分文件无可读文本）", "detail")
            end
        else
            utils.display("Clipboard", "抽取失败: " .. (stderr or "无输出"), "error")
        end
    end, args):start()
end

function M.paste_to_finder()
    -- bash 显式解释执行，不需要 +x 位
    local script_path = hs.configdir .. "/scripts/finder_paste.sh"
    hs.task.new("/bin/bash", function(code, stdout, stderr)
        if code == 0 then
            utils.display("Finder", "已粘贴", "success")
        else
            utils.display("Finder", "粘贴失败: " .. (stderr or stdout or ""), "error")
        end
    end, { script_path }):start()
end

-- ═══════════════════════════════════════════════════════════════════════════
-- Homebrew 维护（在终端中执行）
-- ═══════════════════════════════════════════════════════════════════════════

function M.brew_maintain()
    local script = settings.commands.brew_maintain or "brew update && brew upgrade"
    utils.runInApp(settings.preferred_terminal, script, { "cmd", "n" })
end

-- 全仓 smart-push(2026-06-14 从 raycast git_smart-push 迁入;引擎 git_smart_push.py:
-- GLM 生成 commit message + 批量 commit&push 所有有改动的 repo)。终端跑,可见进度。
function M.git_smart_push()
    local script = settings.commands.git_smart_push
    if not script then return utils.display("Git", "请在 mackit edit local 中配置个人 Git 命令", "info") end
    utils.runInApp(settings.preferred_terminal, script, { "cmd", "n" })
end

-- ═══════════════════════════════════════════════════════════════════════════
-- 文件打印
-- ═══════════════════════════════════════════════════════════════════════════

-- 打印选中文件，按格式分流（2026-06-15 修多选失效）：
--   · PDF → lp 直送系统默认打印机，批量一键全打，不弹窗不点确认（最适合发票/批量票据）。
--     旧实现「open 全部 + 只发一次 ⌘P」对 N 个 PDF 只打前一个、且冷启动 UPDF >6s 超时落空。
--   · 非 PDF（docx/png 等 lp 不认的格式）→ 回退到「默认 app 打开 + 轮询前台 + ⌘P 弹打印窗」，
--     由用户在对话框确认（固定延时对冷启动重型 app 不够，故轮询，6s 兜底）。
function M.file_print()
    local files = utils.getSelectedFiles()
    if #files == 0 then return utils.display("Print", "没有选中文件", "error") end

    local pdfs, others = {}, {}
    for _, path in ipairs(files) do
        if path:lower():match("%.pdf$") then
            pdfs[#pdfs + 1] = path
        else
            others[#others + 1] = path
        end
    end

    -- PDF：逐个 lp 直送默认打印机（lp 自动读系统默认目的地）
    if #pdfs > 0 then
        local failed = 0
        for _, path in ipairs(pdfs) do
            hs.task.new("/usr/bin/lp", function(code)
                if code ~= 0 then
                    failed = failed + 1
                    utils.display("Print", "lp 失败: " .. path:match("[^/]+$"), "error")
                end
            end, { path }):start()
        end
        utils.display("Print", string.format("已直送 %d 个 PDF 到默认打印机", #pdfs), "success")
    end

    -- 非 PDF：保留 open + 弹打印窗 流程
    if #others > 0 then
        local launcher = hs.application.frontmostApplication()
        local launcherName = launcher and launcher:name() or "Finder"
        for _, path in ipairs(others) do
            hs.task.new("/usr/bin/open", nil, { path }):start()
        end
        utils.display("Print", string.format("打开 %d 个文件，待载入后弹打印窗口…", #others), "info")

        local elapsed = 0
        local function trigger()
            local front = hs.application.frontmostApplication()
            local name = front and front:name() or ""
            if name ~= "" and name ~= launcherName then
                hs.timer.doAfter(0.6, function()
                    hs.eventtap.keyStroke({ "cmd" }, "p")
                end)
                return
            end
            elapsed = elapsed + 0.4
            if elapsed < 6 then
                hs.timer.doAfter(0.4, trigger)
            else
                hs.eventtap.keyStroke({ "cmd" }, "p")  -- 超时兜底
            end
        end
        hs.timer.doAfter(0.5, trigger)
    end
end

-- ═══════════════════════════════════════════════════════════════════════════
-- 显示器分辨率切换
-- ═══════════════════════════════════════════════════════════════════════════

local DISPLAYPLACER = "/opt/homebrew/bin/displayplacer"
local DEMO_RES = "1920x1080"

-- 解析 displayplacer list → 每个外接屏一条记录 {id, cur, origin, maxres}
-- 关键：maxres 逐屏独立算（5K 屏→5120x2880，4K 屏→3840x2160），不取全局 max
local function external_displays()
    local out = hs.execute(DISPLAYPLACER .. " list 2>/dev/null")
    if not out or out == "" then return {} end
    local screens, cur = {}, nil
    for line in out:gmatch("[^\n]+") do
        local id = line:match("^Persistent screen id:%s*(%S+)")
        if id then
            cur = { id = id, external = false, maxarea = 0 }
            screens[#screens + 1] = cur
        elseif cur then
            if line:match("^Type:") then
                cur.external = line:match("external") ~= nil
            elseif line:match("^Resolution:") then
                cur.cur = line:match("^Resolution:%s*(%d+x%d+)")
            elseif line:match("^Origin:") then
                cur.origin = line:match("(%(%-?%d+,%-?%d+%))")
            else
                -- mode 行：res:WxH，取本屏面积最大者
                for w, h in line:gmatch("res:(%d+)x(%d+)") do
                    local area = tonumber(w) * tonumber(h)
                    if area > cur.maxarea then
                        cur.maxarea = area
                        cur.maxres = w .. "x" .. h
                    end
                end
            end
        end
    end
    local ext = {}
    for _, s in ipairs(screens) do
        if s.external then ext[#ext + 1] = s end
    end
    return ext
end

-- 1080p 演示 ↔ 各屏自己的最高原生分辨率 轮换
-- 演示态 = 所有外接屏都在 1080；是则各屏各自展开到自己的 max，否则全压回 1080
-- 多屏：每屏独立设各自分辨率（一条 displayplacer 命令带多个 id），不把一个 max 套全屏
function M.display_toggle()
    local ext = external_displays()
    if #ext == 0 then return utils.display("Display", "未检测到外接显示器", "error") end

    local all_demo = true
    for _, s in ipairs(ext) do
        if s.cur ~= DEMO_RES then all_demo = false break end
    end

    local parts, labels = { DISPLAYPLACER }, {}
    for _, s in ipairs(ext) do
        local target = all_demo and (s.maxres or DEMO_RES) or DEMO_RES
        local origin = s.origin and (" origin:" .. s.origin) or ""
        parts[#parts + 1] = string.format(
            '"id:%s res:%s hz:60 color_depth:8 enabled:true scaling:off%s degree:0"',
            s.id, target, origin)
        labels[#labels + 1] = target
    end
    hs.execute(table.concat(parts, " ") .. " 2>/dev/null")
    local mode = all_demo and "最高原生" or "1080p 演示"
    utils.display("Display", mode .. " (" .. table.concat(labels, " · ") .. ")", "success")
end

-- ═══════════════════════════════════════════════════════════════════════════
-- 合盖休眠开关（2026-06-13 从 raycast 迁入；引擎 = mactools/bin/lid_sleep_toggle.sh）
-- 依赖 /etc/sudoers.d/pmset-toggle 的 NOPASSWD（脚本内有重装提示）
-- ═══════════════════════════════════════════════════════════════════════════

function M.lid_sleep_toggle()
    local script = settings.commands.lid_sleep
    if not script then return utils.display("System", "未配置合盖控制脚本", "info") end
    local out, ok = hs.execute(script .. " --brief", true)
    if not ok then
        utils.card({
            title = "切换失败", subtitle = "需 sudoers NOPASSWD（见脚本提示）", kind = "error",
        })
        return
    end

    local kv = {}
    for k, v in (out or ""):gmatch("(%u+)=([^\n]*)") do kv[k] = v end
    local on = kv.STATE == "1"

    utils.card({
        title    = on and "盒盖不睡眠 · ON" or "盒盖睡眠 · OFF",
        subtitle = on and "盖上 lid 全程运行 · 记得插电、别压被子"
                       or "盖上 lid 正常进入睡眠（省电默认）",
        rows = {
            string.format("🔋  %s · %s", kv.SRC or "未知", kv.PCT or "?"),
            string.format("💤  屏幕 %s min · 空闲睡眠 %s", kv.DISPLAYSLEEP or "?", kv.SLEEP or "?"),
        },
        kind     = on and "warn" or "success",
        duration = 4,
    })
end

return M

