-- Defaults are portable. Personal commands live in ~/.config/mackit/hammerspoon.lua.
local base = (os.getenv("XDG_CONFIG_HOME") or (os.getenv("HOME") .. "/.config")) .. "/mackit"
local profile = hs.json.read(base .. "/profile.json") or {}
local M = {profile=profile.profile or "developer", config_dir=hs.configdir,
 scripts_dir=hs.configdir .. "/scripts", preferred_terminal="Ghostty", preferred_ide="Visual Studio Code",
 python_path=hs.fs.attributes("/opt/homebrew/bin/python3") and "/opt/homebrew/bin/python3" or "/usr/local/bin/python3",
 overrides_path=base .. "/hotkey_overrides.json", local_dir=base, commands={}}
M.enable_shortcuts = M.profile == "tianli"
M.hyper, M.vim_nav, M.rcmd, M.wechat = M.enable_shortcuts, M.enable_shortcuts, M.enable_shortcuts, M.enable_shortcuts
local custom=base .. "/hammerspoon.lua"
if hs.fs.attributes(custom) then
 local ok, values=pcall(dofile,custom)
 if ok and type(values)=="table" then for key,value in pairs(values)do M[key]=value end end
end
local overrides=hs.json.read(M.overrides_path) or {}
for key,value in pairs(overrides.features or {}) do
 if key=="hyper" or key=="vim_nav" or key=="rcmd" or key=="wechat" then M[key]=value end
end
return M
