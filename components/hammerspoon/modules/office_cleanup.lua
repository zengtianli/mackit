-- Office 残留锁文件自动清理
-- 监听 Microsoft Office / LibreOffice 退出;当最后一个 Office 应用关闭后,
-- 调用 office_lock_clean.py 清理残留 ~$ 锁文件(脚本自身二次把关进程状态)。
-- 对应需求:「明确关闭我所有的 office 后,残留的统统删掉,自动处理」。
local settings = require("lib.settings")

local M = {}

-- 视为 "Office" 的应用名(hs.application.watcher 上报的 appName)
local OFFICE_APPS = {
    ["Microsoft Word"] = true,
    ["Microsoft Excel"] = true,
    ["Microsoft PowerPoint"] = true,
    ["Microsoft OneNote"] = true,
    ["LibreOffice"] = true,
    ["soffice"] = true,
}

local CLEAN_SCRIPT = settings.commands.office_cleanup

local office_watcher = nil
local debounce_timer = nil

-- 实际跑清理脚本(--json),按结果弹通知
local function run_cleanup()
    hs.task.new(settings.python_path, function(code, stdout, _stderr)
        local ok, res = pcall(hs.json.decode, stdout or "")
        if not ok or not res then return end
        if res.status == "cleaned" and res.count and res.count > 0 then
            hs.notify.new({
                title = "🧹 Office 清理",
                informativeText = string.format("已清理 %d 个残留 ~$ 锁文件(废纸篓可恢复)", res.count),
                withdrawAfter = 6,
            }):send()
        end
        -- status == aborted (还有 Office 在跑) / count==0 → 静默,不打扰
    end, { CLEAN_SCRIPT, "--json" }):start()
end

function M.init()
    office_watcher = hs.application.watcher.new(function(appName, eventType, _app)
        if eventType == hs.application.watcher.terminated and OFFICE_APPS[appName] then
            -- 退出后稍等:让 OS 回收进程 + Office 自己有机会删干净锁文件,
            -- 脚本只清真正残留的。多个 Office 连续退出时合并为一次。
            if debounce_timer then debounce_timer:stop() end
            debounce_timer = hs.timer.doAfter(3, run_cleanup)
        end
    end)
    office_watcher:start()
end

return M
