-- ==========================================
-- 90 · AI 助手（轮 4 会扩为 4 件套：copilot.lua + codecompanion + claudecode + mcphub）
-- ==========================================

return {
  -- copilot ghost text 补全（轮 4 计划升级为 zbirenbaum/copilot.lua）
  -- lazy=false 启动加载：因为 <c-h>/<c-l>/<c-p> insert mode 必须立即可用，
  -- event=InsertEnter 会在第一次进 insert 时有 ms 级闪失效窗口
  {
    "github/copilot.vim",
    enabled = require("config.profile").name == "tianli",
    lazy = false,
    config = function()
      vim.g.copilot_enabled = true
      vim.g.copilot_no_tab_map = true
      
      
      
      
      
      
      vim.cmd([[let g:copilot_filetypes = { 'TelescopePrompt': v:false }]])
    end
  },
}
