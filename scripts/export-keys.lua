local root=arg[1]
package.path=root.."/components/nvim/lua/?.lua;"..root.."/components/nvim/lua/?/init.lua;"..package.path
local keys=require("config.keymaps")
local rows={}
local function add(component,mode,key,desc,source,profile)
 table.insert(rows,{component=component,mode=mode,key=key,description=desc,source=source,profile=profile})
end
for _,v in ipairs(keys.entries)do
 local mode=type(v.mode)=="table" and table.concat(v.mode,",") or v.mode
 add("nvim",v.scope and mode.."/"..v.scope or mode,v.key,v.desc,"components/nvim/lua/config/keymaps.lua",v.profile)
end
for _,v in ipairs(keys.lazy)do add("nvim","lazy-popup","<Space>"..v.key,v.cmd,"components/nvim/lua/config/keymaps.lua")end
for context,binds in pairs(keys.picker)do for key,action in pairs(binds)do
 add("nvim","fzf/"..context,key,action,"components/nvim/lua/config/keymaps.lua")
end end
for _,key in ipairs(keys.multicursor)do add("nvim","n/plugin",key,"多光标插件默认","components/nvim/lua/config/keymaps.lua")end
for action,key in pairs(keys.yazi)do add("nvim","yazi-popup",key,action,"components/nvim/lua/config/keymaps.lua")end
local cmp={mapping=setmetatable({complete=function()return true end,preset={insert=function(t)return t end}},{__call=function(_,t)return t end})}
for key in pairs(keys.completion(cmp,function()end,function()end))do add("nvim","completion",key,"补全菜单","components/nvim/lua/config/keymaps.lua")end
-- Hammerspoon listens to no keys: Karabiner owns them (see the karabiner rows in build-handbook.py).
-- Only the right-⌘ app table stays here, as the import source for Initials.
local hskeys=dofile(root.."/components/hammerspoon/keymaps.lua")
for key,app in pairs(hskeys.right_command)do add("hammerspoon","global","right-cmd+"..key,"切换 "..app,"components/hammerspoon/keymaps.lua","tianli")end
vim.fn.writefile({vim.json.encode(rows)},arg[2])
