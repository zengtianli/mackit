local root=arg[1]
local tmp=arg[2]
package.path=root.."/components/hammerspoon/?.lua;"..package.path
local state={hotkeys={}}
local settings={enable_shortcuts=false,overrides_path=tmp.."/overrides.json",preferred_terminal="Ghostty",preferred_ide="Code",python_path="python3"}
package.loaded["lib.settings"]=settings
package.loaded["lib.utils"]={log=function()end,display=function()end}
hs={json={encode=function(t)state=t;return "{}" end,decode=function()return state end},
 hotkey={bind=function()return {} end,new=function()return {enable=function()end,disable=function()end} end},
 application={frontmostApplication=function()return {name=function()return "Terminal" end}end,watcher={activated=1,deactivated=2,new=function()return {start=function()end,stop=function()end}end}}}
local keys=require("keymaps")
for _,hk in ipairs(keys)do
 if hk.module~="_hotkey_manager" then
  local name="modules."..hk.module
  package.loaded[name]=package.loaded[name] or {}
  package.loaded[name][hk.func]=function()error("Actions must not be executed by these tests")end
 end
end
local manager=require("lib.hotkey_manager")
assert(manager.init()==0,"developer must not register global keys")
local menu=dofile(root.."/components/hammerspoon/modules/menubar.lua")
menu.toggle(keys[1])
assert(manager.is_enabled(state.hotkeys[manager.hotkey_id(keys[1])]),"explicit enable must override default off")
assert(manager.init()==1)
menu.toggle(keys[1])
assert(manager.init()==0)
settings.enable_shortcuts=true
assert(manager.init()==#keys-1,"personal preset keeps keys except explicit disabled")
local items=menu.build_menu()
assert(#items>5)
print("Hammerspoon preset / toggle / menu ownership: OK (no physical events)")
