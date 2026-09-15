-- MacKit lifecycle: options, actions, plugins, keys, local overrides.
vim.loader.enable()
vim.opt.rtp:prepend(vim.fn.fnamemodify(debug.getinfo(1, "S").source:sub(2), ":p:h"))
vim.g.mapleader = " "
require("config.options").setup()
require("config.autocmds").setup()
require("config.terminal").setup()
require("config.ftplugin").setup()
require("actions.text").setup()
require("actions.markdown").setup()
if vim.env.MACKIT_NO_PLUGINS ~= "1" then
 local ok,err=pcall(require,"config.plugins")
 if not ok then vim.notify("MacKit: 插件尚未就绪；检查网络后运行 :Lazy sync。\n"..tostring(err),vim.log.levels.ERROR) end
end
require("config.keymaps").setup()
local local_file = (vim.env.XDG_CONFIG_HOME or (vim.env.HOME .. "/.config")) .. "/mackit/local.lua"
if vim.fn.filereadable(local_file) == 1 then dofile(local_file) end
