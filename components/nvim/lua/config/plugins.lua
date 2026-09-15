-- ==========================================
-- 插件入口（按 R1 echasnovski 数字前缀模式拆分到 lua/plugins/）
-- ==========================================
-- 每个 lua/plugins/<NN>_<topic>.lua return 一个 spec table
-- 加载顺序由数字前缀决定：10 ui → 20 editor → 30 lsp → 40 treesitter
--                       → 50 markdown → 60 git → 70 search → 80 files
--                       → 85 completion → 90 ai → 99 extras

-- 初始化 lazy.nvim 插件管理器
local function setup_lazy()
  local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
  if not vim.loop.fs_stat(lazypath) then
    local output=vim.fn.system({
      "git", "clone", "--depth=1", "--filter=blob:none",
      "https://github.com/folke/lazy.nvim.git",
      "--branch=stable", lazypath,
    })
    if vim.v.shell_error ~= 0 then
      vim.notify("MacKit: lazy.nvim 下载失败；请检查 GitHub 网络后重启。原生编辑与键位仍可使用。\n"..output,vim.log.levels.ERROR)
      return false
    end
  end
  vim.opt.rtp:prepend(lazypath)

  -- 配置 lazy 命令快捷键
  local lazy_cmd = require("lazy.view.config").commands
  local lazy_keys = require("config.keymaps").lazy
  for _, v in ipairs(lazy_keys) do
    lazy_cmd[v.cmd].key = "<SPC>" .. v.key
    lazy_cmd[v.cmd].key_plugin = "<leader>" .. v.key
  end
  return true
end

if not setup_lazy() then return end

-- 用 lazy import 协议自动扫 lua/plugins/ 下所有数字前缀文件
require("lazy").setup({ { import = "plugins" } }, { concurrency=4, git={timeout=120}, performance = { rtp = { reset = false } } })
