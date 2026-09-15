-- ==========================================
-- 10 · UI 界面（主题 + statusline + tabline + scrollbar + notify + 视觉装饰）
-- ==========================================

return {
  -- 主题（lazy=false + priority=1000：必须最先加载）
  {
    "theniceboy/nvim-deus",
    lazy = false,
    priority = 1000,
    config = function()
      vim.cmd([[colorscheme deus]])
    end,
  },

  -- 状态栏
  {
    "nvim-lualine/lualine.nvim",
    event = "VeryLazy",
    config = function()
      require('lualine').setup {
        options = {
          icons_enabled = true,
          theme = 'auto',
          component_separators = { left = '', right = '' },
          section_separators = { left = '', right = '' },
          disabled_filetypes = { statusline = {}, winbar = {} },
          ignore_focus = {},
          always_divide_middle = true,
          globalstatus = true,
          refresh = { statusline = 1000, tabline = 1000, winbar = 1000 }
        },
        sections = {
          lualine_a = { 'filename' },
          lualine_b = { 'branch', 'diff', 'diagnostics' },
          lualine_c = {},
          lualine_x = {},
          lualine_y = { 'filesize', 'fileformat', 'filetype' },
          lualine_z = { 'location' }
        },
        inactive_sections = {
          lualine_a = {}, lualine_b = {}, lualine_c = { 'filename' },
          lualine_x = { 'location' }, lualine_y = {}, lualine_z = {}
        },
        tabline = {}, winbar = {}, inactive_winbar = {}, extensions = {}
      }
    end
  },

  -- 标签栏
  {
    'akinsho/bufferline.nvim',
    event = "VeryLazy",
    opts = {
      options = {
        mode = "tabs",
        diagnostics = "nvim_lsp",
        diagnostics_indicator = function(count, level, diagnostics_dict, context)
          local icon = level:match("error") and " " or " "
          return " " .. icon .. count
        end,
        indicator = { icon = '▎', style = "icon" },
        show_buffer_close_icons = false,
        show_close_icon = false,
        enforce_regular_tabs = true,
        show_duplicate_prefix = false,
        tab_size = 16,
        padding = 0,
        separator_style = "thick",
      }
    }
  },

  -- 滚动条（内嵌 git colors / search / gitsigns handler）
  {
    "petertriho/nvim-scrollbar",
    event = "VeryLazy",
    dependencies = { "kevinhwang91/nvim-hlslens", "lewis6991/gitsigns.nvim" },
    config = function()
      local group = vim.api.nvim_create_augroup("scrollbar_set_git_colors", {})
      vim.api.nvim_create_autocmd("BufEnter", {
        pattern = "*",
        callback = function()
          vim.cmd([[
hi! ScrollbarGitAdd guifg=#8CC85F
hi! ScrollbarGitAddHandle guifg=#A0CF5D
hi! ScrollbarGitChange guifg=#E6B450
hi! ScrollbarGitChangeHandle guifg=#F0C454
hi! ScrollbarGitDelete guifg=#F87070
hi! ScrollbarGitDeleteHandle guifg=#FF7B7B ]])
        end,
        group = group,
      })
      require("scrollbar.handlers.search").setup({})
      require("scrollbar.handlers.gitsigns").setup()
      require("scrollbar").setup({
        show = true,
        handle = { text = " ", color = "#928374", hide_if_all_visible = true },
        marks = { Search = { color = "yellow" }, Misc = { color = "purple" } },
        handlers = { cursor = false, diagnostic = true, gitsigns = true, handle = true, search = true }
      })
    end,
  },

  -- 通知系统
  {
    "rcarriga/nvim-notify",
    event = "VeryLazy",
    config = function()
      local notify = require("notify")
      vim.notify = function(msg, ...)
        if string.match(msg, "error drawing label for") then return end
        require("notify")(msg, ...)
      end
      notify.setup({
        on_open = function(win) vim.api.nvim_win_set_config(win, { border = "none" }) end,
        background_colour = "#202020", fps = 60, level = 2, minimum_width = 50,
        render = "compact", stages = "fade_in_slide_out", timeout = 3000, top_down = true
      })
      local opts = { noremap = true, silent = true }
      -- 通知历史走 notify.history()（telescope 已删）
      
      
    end
  },

  -- 缩进/chunk 视觉装饰（init→config 修启动 eager 反模式）
  {
    "shellRaining/hlchunk.nvim",
    event = "BufRead",
    config = function()
      vim.api.nvim_create_autocmd({ "CursorMoved", "CursorMovedI" }, { pattern = "*", command = "EnableHL" })
      require('hlchunk').setup({
        chunk = { enable = true, use_treesitter = true, style = { { fg = "#806d9c" } } },
        indent = { chars = { "│", "¦", "┆", "┊" }, use_treesitter = false },
        blank = { enable = false },
        line_num = { use_treesitter = true }
      })
    end
  },
}
