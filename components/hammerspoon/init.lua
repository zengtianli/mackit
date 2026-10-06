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
manager.init()
-- Karabiner 监听按键，经 hs 命令行调用声明过的动作：hs -c 'mackit_run("<module>.<func>")'
mackit_run=manager.run
if settings.enable_shortcuts or settings.wechat then require("modules.apps").init_wechat_hotkey(settings.wechat) end
-- Office 锁文件清理已改由 launchd 作业 com.tianli.office-lock-clean 承担（Cadence 管理，2026-10-05）
if settings.ac_awake then require("modules.system").init_ac_awake() end
require("modules.menubar").init()
