-- ==========================================
-- 20 · 编辑增强（Comment / surround / visual-multi / illuminate / substitute / autopairs）
-- ==========================================

return {
  -- 注释
  {
    "numToStr/Comment.nvim",
    event = "BufRead",
    config = function()
      require('Comment').setup({
        padding = true,
        sticky = true,
        ignore = '^$',
        toggler = { line = 'gcc', block = 'gbc' },
        opleader = { line = 'gc', block = 'gb' },
        mappings = { basic = true, extra = true }
      })
      -- 保持原有快捷键
      
      
      
      
    end
  },

  -- 包围编辑
  {
    "kylechui/nvim-surround",
    version = "*",
    event = "VeryLazy",
    config = function() require("nvim-surround").setup({}) end
  },

  -- 多光标
  {
    "mg979/vim-visual-multi",
    keys = require("config.keymaps").multicursor
  },

  -- 同名词高亮
  {
    "RRethy/vim-illuminate",
    event = "VeryLazy",
    config = function()
      require('illuminate').configure({ providers = { 'regex' } })
      vim.cmd("hi IlluminatedWordText guibg=#393E4D gui=none")
    end
  },

  -- 替换增强
  {
    "gbprod/substitute.nvim",
    event = "VeryLazy",
    config = function()
      local substitute = require("substitute")
      substitute.setup({ highlight_substituted_text = { enabled = true, timer = 200 } })
      
      
      
      
      
      
    end
  },

  -- 自动配对
  {
    "windwp/nvim-autopairs",
    event = "InsertEnter",
    config = function() require("nvim-autopairs").setup({}) end
  },
}
