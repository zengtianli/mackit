-- MacKit Hammerspoon entry.
require("hs.ipc")
local settings=require("lib.settings")
local manager=require("lib.hotkey_manager")
local function reload(files)
 for _,file in ipairs(files)do
  if file:match("%.lua$") or file:match("hotkey_overrides%.json$") then manager.cleanup();hs.reload();return end
 end
end
ConfigWatcher=hs.pathwatcher.new(hs.fs.pathToAbsolute(hs.configdir),reload):start()
LocalWatcher=hs.pathwatcher.new(settings.local_dir,reload):start()
if settings.hyper then require("modules.keymap").init_hyper() end
if settings.vim_nav then require("modules.keymap").init_vim_nav() end
if settings.rcmd then require("modules.rcmd").init() end
manager.init()
if settings.wechat then require("modules.apps").init_wechat_hotkey() end
if settings.commands.office_cleanup then require("modules.office_cleanup").init() end
require("modules.menubar").init()
