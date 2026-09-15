-- Yabai 窗口管理模块
local utils = require("lib.utils")

local M = {}

local function yabai(args)
    local cmd = "/opt/homebrew/bin/yabai " .. args
    local output, ok = hs.execute(cmd)
    return output, ok
end

function M.toggle_mouse()
    local output = hs.execute("/opt/homebrew/bin/yabai -m config mouse_follows_focus")
    local current = output and output:match("%w+") or "off"
    if current == "off" then
        yabai("-m config mouse_follows_focus on")
        utils.display("Yabai", "Mouse Follow: ON", "success")
    else
        yabai("-m config mouse_follows_focus off")
        utils.display("Yabai", "Mouse Follow: OFF", "success")
    end
end

function M.toggle_yabai()
    local _, ok = hs.execute("pgrep -x yabai")
    if ok then
        hs.execute("/opt/homebrew/bin/yabai --stop-service")
        utils.display("Yabai", "已停止", "success")
    else
        hs.execute("/opt/homebrew/bin/yabai --start-service")
        utils.display("Yabai", "已启动", "success")
    end
end

function M.toggle_space_layout()
    local yabai_bin = "/opt/homebrew/bin/yabai"
    local jq = "/usr/bin/jq"
    local cur = hs.execute(yabai_bin .. " -m query --spaces --space | " .. jq .. " -r '.type'")
    cur = (cur or ""):gsub("%s+", "")
    local target = (cur == "bsp") and "float" or "bsp"
    hs.execute(yabai_bin .. " -m space --layout " .. target)
    if target == "bsp" then
        local floating = hs.execute(yabai_bin .. " -m query --windows --space | " .. jq .. " -r '.[] | select(.\"is-floating\"==true) | .id'")
        for win_id in (floating or ""):gmatch("%S+") do
            hs.execute(yabai_bin .. " -m window " .. win_id .. " --toggle float")
        end
    end
    utils.display("Yabai", cur .. " → " .. target, "success")
end

return M
