local root=arg[1]
local tmp=arg[2]
package.path=root.."/components/hammerspoon/?.lua;"..package.path
local state={hotkeys={}}
local settings={enable_shortcuts=false,overrides_path=tmp.."/overrides.json",preferred_terminal="Ghostty",preferred_ide="Code",python_path="python3"}
package.loaded["lib.settings"]=settings
package.loaded["lib.utils"]={log=function()end,display=function()end}
-- No hs.hotkey / hs.eventtap in this stub: Karabiner listens to the keys, so any attempt to bind one fails here.
local scheduled=0
hs={json={encode=function(t)state=t;return "{}" end,decode=function()return state end},
 timer={doAfter=function()scheduled=scheduled+1 end},
 application={frontmostApplication=function()return {bundleID=function()return "com.apple.Terminal" end}end}}
local keys=require("keymaps")
local declared={keys.wechat}
for _,hk in ipairs(keys)do table.insert(declared,hk)end
for _,hk in ipairs(declared)do
 if hk.module~="_hotkey_manager" then
  local name="modules."..hk.module
  package.loaded[name]=package.loaded[name] or {}
  package.loaded[name][hk.func]=function()error("Actions must not be executed by these tests")end
 end
end
local manager=require("lib.hotkey_manager")
assert(manager.init()==0,"developer must not register global keys")
assert(manager.run(manager.action_id(keys[1]))==false,"a disabled action must not run")
local menu=dofile(root.."/components/hammerspoon/modules/menubar.lua")
menu.toggle(keys[1])
assert(manager.is_enabled(state.hotkeys[manager.hotkey_id(keys[1])]),"explicit enable must override default off")
assert(manager.init()==1)
menu.toggle(keys[1])
assert(manager.init()==0)
settings.enable_shortcuts=true
assert(manager.init()==#keys-1,"personal preset keeps keys except explicit disabled")
assert(manager.run(manager.action_id(keys[1]))==false,"an explicitly disabled action must not run")
assert(manager.run("os.execute")==false and manager.run("system.undeclared")==false,"only declared actions run")
local finder,global
for _,hk in ipairs(keys)do
 if hk~=keys[1] and hk.scope=="finder" then finder=finder or hk elseif hk.scope~="finder" then global=global or hk end
end
assert(manager.run(manager.action_id(finder))==false,"Finder actions need Finder in front")
assert(scheduled==0 and manager.run(manager.action_id(global))==true and scheduled==1,"a declared action is scheduled once")
assert(not manager.is_runnable(manager.action_id(keys.wechat)),"the WeChat key follows its own switch")
settings.wechat=true;manager.init()
assert(manager.is_runnable(manager.action_id(keys.wechat)))
local items=menu.build_menu()
assert(#items>5)
print("Hammerspoon preset / toggle / dispatch / menu ownership: OK (no physical events)")
