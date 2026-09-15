-- 菜单栏控制中心：常驻 ⌨ 图标 → 下拉列全部快捷键（分组 + 勾选）
-- 点一条 = 切该快捷键启停（写 hotkey_overrides.json，pathwatcher 自动热加载）
--
-- 轻量：无 timer / 无轮询；菜单按函数惰性构建，仅点开时读一次 override 状态。
-- 唯一常驻成本 = 一个菜单栏项（进程内，约 +1MB，不开新进程）。
-- 复用 hotkey_manager.hotkey_id / hotkey_display，保证写的 id 与绑定端一致。

local utils = require("lib.utils")
local hkm   = require("lib.hotkey_manager")

local M = {}
local bar = nil

local OVERRIDES_PATH = require("lib.settings").overrides_path

-- ─── overrides 读写 ──────────────────────────────────────────
local function read_overrides()
    local f = io.open(OVERRIDES_PATH, "r")
    if not f then return { hotkeys = {} } end
    local content = f:read("*all"); f:close()
    local ok, data = pcall(hs.json.decode, content or "")
    if not ok or type(data) ~= "table" then return { hotkeys = {} } end
    data.hotkeys = data.hotkeys or {}
    return data
end

local function write_overrides(data)
    data._comment = data._comment
        or "启停状态。id = <scope>:<mods>:<key>，例: global:cmd+ctrl+shift:1"
    -- 不写时间戳：本文件进 git，时间戳会让每次 toggle 都产生 diff 噪音
    data._updated_at = nil
    local f = io.open(OVERRIDES_PATH, "w")
    if not f then utils.display("控制中心", "写入 overrides 失败", "error"); return false end
    f:write(hs.json.encode(data, true) .. "\n") -- 尾换行与 git 版本对齐，免 toggle 一次就出 diff
    f:close()
    return true
end

-- 切某条启停：缺省/true 视为启用。关 → 写 {enabled=false}；开 → 删 override 回归默认。
-- 写文件即触发 init.lua 的 pathwatcher → hs.reload()，菜单与绑定一并重建（不在此显式 reload，避免双重）。
function M.toggle(hk)
    local id   = hkm.hotkey_id(hk)
    local data = read_overrides()
    local cur  = data.hotkeys[id]
    local enabled_now = hkm.is_enabled(cur)
    if enabled_now then
        data.hotkeys[id] = { enabled = false }
    else
        data.hotkeys[id] = { enabled = true }
    end
    if write_overrides(data) then
        utils.display("快捷键",
            (enabled_now and "已停用 · " or "已启用 · ") .. hk.desc,
            enabled_now and "warn" or "success")
    end
end

-- ─── 菜单构建（每次点开实时读状态）────────────────────────────
function M.build_menu()
    local hotkeys   = require("keymaps")
    local settings  = require("lib.settings")
    local overrides = read_overrides().hotkeys

    local groups = { finder = {}, global = {} }
    for _, hk in ipairs(hotkeys) do
        -- 未知 scope 兜底进 global，不因新 scope 崩菜单
        table.insert(groups[hk.scope or "global"] or groups.global, hk)
    end

    local disabled = 0
    for _, hk in ipairs(hotkeys) do
        if not hkm.is_enabled(overrides[hkm.hotkey_id(hk)]) then disabled = disabled + 1 end
    end

    local items = {}
    table.insert(items, { title = string.format("Hammerspoon · %d 条快捷键%s",
        #hotkeys, disabled > 0 and ("（停用 " .. disabled .. "）") or ""), disabled = true })
    table.insert(items, { title = "-" })

    local function add_group(key, header)
        local g = groups[key]
        if #g == 0 then return end
        table.insert(items, { title = header, disabled = true })
        for _, hk in ipairs(g) do
            local ov = overrides[hkm.hotkey_id(hk)]
            table.insert(items, {
                title   = string.format("%s   %s", hkm.hotkey_display(hk), hk.desc),
                checked = hkm.is_enabled(ov),
                fn      = function() M.toggle(hk) end,
            })
        end
        table.insert(items, { title = "-" })
    end

    add_group("finder", "Finder 专用")
    add_group("global", "全局")

    local features={}
    for _,feature in ipairs({{"hyper","右 Option → Hyper"},{"vim_nav","Ctrl+HJKL 导航（终端除外）"},{"rcmd","右 Command 切换应用"},{"wechat","微信启动快捷键"}}) do
        local name,label=feature[1],feature[2]
        table.insert(features,{title=label,checked=settings[name],fn=function()
            local data=read_overrides()
            data.features=data.features or {}
            data.features[name]=not settings[name]
            write_overrides(data)
        end})
    end
    table.insert(items,{title="键盘规则",menu=features})

    table.insert(items, { title = "设置", menu = {
        { title = "终端    " .. settings.preferred_terminal, disabled = true },
        { title = "IDE     " .. settings.preferred_ide, disabled = true },
        { title = "Python  " .. settings.python_path, disabled = true },
        { title = "-" },
        { title = "编辑本机设置…", fn = function()
            local path = settings.local_dir .. "/hammerspoon.lua"
            if not hs.fs.attributes(path) then local f=io.open(path,"w");if f then f:write("return {}\n");f:close() end end
            hs.execute("/usr/bin/open -a '" .. settings.preferred_ide .. "' '"
                .. path .. "'")
        end },
    } })
    table.insert(items, { title = "显示帮助卡   ⌘⌃⇧H", fn = function() hkm.show_help() end })
    table.insert(items, { title = "重新加载配置", fn = function() hs.reload() end })

    return items
end

function M.init()
    if bar then bar:delete() end
    bar = hs.menubar.new()
    if not bar then return end
    bar:setTitle("⌨")
    bar:setTooltip("Hammerspoon 快捷键控制中心")
    bar:setMenu(M.build_menu)   -- 传函数：点开时惰性构建，反映当前 override
end

return M
