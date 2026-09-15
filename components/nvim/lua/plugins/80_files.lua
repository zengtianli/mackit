-- ==========================================
-- 80 · 文件管理（yazi 浮窗）
-- ==========================================

return {
  {
    "mikavilpas/yazi.nvim",
    event = "VeryLazy",
    cmd = { "Yazi" },
    opts = {
      floating_window_scaling_factor = 1, yazi_floating_window_border = "none",
      open_for_directories = true, open_multiple_tabs = true,
      keymaps = require("config.keymaps").yazi
    }
  },
}
