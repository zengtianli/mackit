-- eventtap 守护器：注册即托管，防三类静默失效（抽象自 rcmd.lua 2026-07-21 抗失效重构）
--   ① 回调超时 → macOS 以 kCGEventTapDisabledByTimeout 禁用 tap：30s watchdog 查 isEnabled 自动拉起
--   ② 安全输入(密码框)禁用后无人恢复：同 watchdog 覆盖
--   ③ 睡眠唤醒/屏幕解锁后 tap 坏死：caffeinate watcher 对全部 tap 停/启一轮
-- 用法: tap_guard.register("rcmd", tap) — register 内部 start，模块不必再自建 watchdog
-- 诊断: hs -c 'print(hs.inspect(require("lib.tap_guard").status()))'

local M = {}

local taps = {}
local watchdog = nil
local wake_watcher = nil

local function ensure_guards()
    if not watchdog then
        -- 第 3 参 continueOnError=true：守护自身不能因一次回调出错就静默死掉
        watchdog = hs.timer.new(30, function()
            for name, tap in pairs(taps) do
                if not tap:isEnabled() then
                    tap:start()
                    print(string.format("[tap_guard] %s 曾被系统禁用，已自动重启", name))
                end
            end
        end, true)
        watchdog:start()
    end
    if not wake_watcher then
        wake_watcher = hs.caffeinate.watcher.new(function(evt)
            if evt == hs.caffeinate.watcher.systemDidWake
                or evt == hs.caffeinate.watcher.screensDidUnlock then
                for _, tap in pairs(taps) do
                    tap:stop()
                    tap:start()
                end
            end
        end)
        wake_watcher:start()
    end
end

function M.register(name, tap)
    taps[name] = tap
    tap:start()
    ensure_guards()
    return tap
end

-- 注销并停掉某个 tap（否则 cleanup 后 watchdog 30s 内会把它拉活）
function M.unregister(name)
    local tap = taps[name]
    if tap then
        tap:stop()
        taps[name] = nil
    end
end

function M.status()
    local s = { watchdog_running = (watchdog and watchdog:running()) or false }
    for name, tap in pairs(taps) do
        s[name] = tap:isEnabled()
    end
    return s
end

function M.cleanup()
    for _, tap in pairs(taps) do tap:stop() end
    taps = {}
    if watchdog then watchdog:stop(); watchdog = nil end
    if wake_watcher then wake_watcher:stop(); wake_watcher = nil end
end

return M
