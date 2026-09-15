-- ==========================================
-- 60 · Git 工作流（gitsigns + lazygit）
-- ==========================================

return {
  -- gutter 标记 + hunk 操作
  {
    "lewis6991/gitsigns.nvim",
    event = "BufRead",
    config = function()
      require('gitsigns').setup({
        signs = {
          add = { text = '▎' }, change = { text = '░' }, delete = { text = '_' },
          topdelete = { text = '▔' }, changedelete = { text = '▒' }, untracked = { text = '┆' }
        }
      })
      
      
      
      
      
    end
  },

  -- lazygit TUI 浮窗
  {
    "kdheepak/lazygit.nvim",
    cmd = { "LazyGit" },
    config = function()
      vim.g.lazygit_floating_window_scaling_factor = 1.0
      vim.g.lazygit_floating_window_winblend = 0
      vim.g.lazygit_use_neovim_remote = true
      
    end
  },
}
