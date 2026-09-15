-- ==========================================
-- 40 · Treesitter（语法高亮 + 上下文 + 代码大纲 aerial）
-- ==========================================

return {
  -- 语法高亮（lazy=false 必须早加载支持高亮即时生效）
  {
    "nvim-treesitter/nvim-treesitter",
    lazy = false,
    build = ":TSUpdate",
    config = function()
      -- 禁用内置的折叠
      vim.opt.foldmethod = "manual"
      vim.opt.foldexpr = ""
      vim.opt.smartindent = false

      require("nvim-treesitter.configs").setup({
        auto_install = false,
        sync_install = false,
        ensure_installed = { "lua", "vim", "vimdoc" },
        highlight = {
          enable = true,
          disable = function(lang, buf)
            local max_filesize = 100 * 1024 -- 100 KB
            local ok, stats = pcall(vim.loop.fs_stat, vim.api.nvim_buf_get_name(buf))
            if ok and stats and stats.size > max_filesize then
              return true
            end
            return false
          end,
          additional_vim_regex_highlighting = false,
        },
        indent = { enable = false },
        incremental_selection = { enable = false }
      })

      vim.g.ts_highlight_lua = false
      vim.g.ts_highlight = false
    end
  },

  -- 上下文吸附顶
  {
    "nvim-treesitter/nvim-treesitter-context",
    event = "BufRead",
    config = function()
      local tscontext = require('treesitter-context')
      tscontext.setup {
        enable = true, max_lines = 0, min_window_height = 0, line_numbers = true,
        multiline_threshold = 20, trim_scope = 'outer', mode = 'cursor',
        separator = nil, zindex = 20, on_attach = nil
      }
      
    end
  },

  -- 代码大纲（支持 markdown 标题结构）
  {
    "stevearc/aerial.nvim",
    event = "BufRead",
    dependencies = { "nvim-treesitter/nvim-treesitter" },
    config = function()
      require("aerial").setup({
        backends = { "treesitter", "lsp", "markdown" },
        layout = { min_width = 30, default_direction = "right" },
        filter_kind = false,
        highlight_on_hover = true,
        show_guides = true,
      })
      
      
      
    end
  },
}
