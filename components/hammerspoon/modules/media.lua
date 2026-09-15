-- 媒体控制模块
local utils = require("lib.utils")

local M = {}

function M.togglePlayback()
    -- 用 hs.application.find 替代 pgrep，单次 osascript 完成判断+切换，
    -- 避免 shell 脚本里多次 fork osascript 导致按键延迟（原方案 ~1s 卡顿）
    if not hs.application.find("Music") then
        hs.application.launchOrFocus("Music")
        hs.timer.doAfter(1.5, function()
            hs.osascript.applescript([[
                tell application "Music"
                    try
                        play playlist "Favourite Songs"
                    on error
                        play
                    end try
                end tell
            ]])
        end)
        utils.display("Music", "启动并播放", "success")
        return
    end
    hs.osascript.applescript([[
        tell application "Music"
            if player state is playing then
                pause
            else
                play
            end if
        end tell
    ]])
    utils.display("Music", "播放/暂停", "success")
end

function M.nextTrack()
    if not hs.application.find("Music") then return M.togglePlayback() end
    hs.osascript.applescript('tell application "Music" to next track')
    utils.display("Music", "下一首", "success")
end

function M.previousTrack()
    if not hs.application.find("Music") then return M.togglePlayback() end
    hs.osascript.applescript('tell application "Music" to previous track')
    utils.display("Music", "上一首", "success")
end

function M.systemPlayPause()
    hs.eventtap.event.newSystemKeyEvent("PLAY", true):post()
    hs.eventtap.event.newSystemKeyEvent("PLAY", false):post()
    utils.display("System", "媒体播放/暂停", "success")
end

return M
