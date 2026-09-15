-- ==========================================
-- 70 · 搜索 / picker（fzf-lua 主，nvim-hlslens 高亮 *# 当前匹配位置）
-- ==========================================

return {
  -- fzf-lua 主 picker（替代已删的 telescope，承接所有 picker keymap）
  {
    "theniceboy/fzf-lua",
    -- lazy=false 启动加载：因为承接全局 normal mode picker keymap（<c-p>/<c-h>/<c-w>/z=/: 等），
    -- 这些键必须开机即可用，不能等 keys 触发
    lazy = false,
    config = function()
      local fzf = require('fzf-lua')
      local m = { noremap = true }
      -- 主 grep（原始 fzf-lua keymap）
      
      
      -- 从 telescope 迁移过来的 8 个 keymap
                   -- 找文件
                -- 最近文件
                 -- buffer 列表
                -- 命令面板（原 commander.nvim 替代）
             -- 恢复上次 picker
              -- 拼写建议
                                                       -- 诊断列表
         -- git 状态
      fzf.setup({
        global_resume = true, global_resume_query = true,
        winopts = {
          height = 1, width = 1, preview = { layout = 'vertical', scrollbar = 'float' },
          fullscreen = true, vertical = 'down:45%', horizontal = 'right:60%', hidden = 'nohidden'
        },
        keymap = require("config.keymaps").picker,
        previewers = {
          head = { cmd = "head", args = nil },
          git_diff = { cmd_deleted = "git diff --color HEAD --", cmd_modified = "git diff --color HEAD", cmd_untracked = "git diff --color --no-index /dev/null" },
          man = { cmd = "man -c %s | col -bx" },
          builtin = { syntax = true, syntax_limit_l = 0, syntax_limit_b = 1024 * 1024, jump_to_line = true, title = false }
        },
        files = {
          prompt = 'Files❯ ', multiprocess = true, git_icons = true, file_icons = true, color_icons = true,
          find_opts = [[-type f -not -path '*/\.git/*' -printf '%P\n']],
          rg_opts = "--color=never --files --hidden --follow -g '!.git'",
          fd_opts = "--color=never --type f --hidden --follow --exclude .git"
        },
        buffers = { prompt = 'Buffers❯ ', file_icons = true, color_icons = true, sort_lastused = true },
        grep = { rg_opts = "--color=always --line-number --column --smart-case --ignore-file=.fzfignore", previewer = "builtin", jump_to_line = true }
      })
    end
  },

  -- 高亮搜索匹配位置（*/#/g*/g# 触发）
  {
    "kevinhwang91/nvim-hlslens",
    enabled = true,
    event = "VeryLazy",
    config = function() require("scrollbar.handlers.search").setup() end
  },
}
