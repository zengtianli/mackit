-- ==========================================
-- 50 · Markdown 工作流（用户写作主场景，4 件套）
-- ==========================================

return {
  -- 浏览器实时预览
  {
    "iamcco/markdown-preview.nvim",
    cmd = { "MarkdownPreviewToggle", "MarkdownPreview", "MarkdownPreviewStop" },
    ft = { "markdown" },
    build = "cd app && npx --yes yarn install && npx --yes yarn add msgpack-lite",
    config = function()
      -- 修复 Node.js v25 的 localStorage 问题
      vim.fn.setenv('NODE_OPTIONS', '--no-experimental-webstorage')

      vim.g.mkdp_auto_start = 0
      vim.g.mkdp_auto_close = 1
      vim.g.mkdp_refresh_slow = 0
      vim.g.mkdp_command_for_global = 0
      vim.g.mkdp_open_to_the_world = 0
      vim.g.mkdp_open_ip = ''
      vim.g.mkdp_browser = ''
      vim.g.mkdp_echo_preview_url = 0
      vim.g.mkdp_browserfunc = ''
      vim.g.mkdp_preview_options = {
        mkit = {}, katex = {}, uml = {}, maid = {},
        disable_sync_scroll = 0, sync_scroll_type = 'middle',
        hide_yaml_meta = 1, sequence_diagrams = {}, flowchart_diagrams = {}
      }
      vim.g.mkdp_markdown_css = ''
      vim.g.mkdp_highlight_css = ''
      vim.g.mkdp_port = ''
      vim.g.mkdp_page_title = '「${name}」'
    end
  },

  -- TOC 生成 / 更新
  {
    "hedyhli/markdown-toc.nvim",
    ft = "markdown",
    cmd = { "Mtoc" },
    config = function()
      require('mtoc').setup({
        headings = { before_toc = false },
        fences = { enabled = true, start_text = "mtoc-start", end_text = "mtoc-end" },
        auto_update = true,
        toc_list = { markers = '*', cycle_markers = false },
      })
      
      
      
      
    end
  },

  -- Marp 幻灯片
  {
    "mpas/marp-nvim",
    ft = { "markdown" },
    config = function()
      require("marp").setup({
        port = 8080,
        wait_for_response_timeout = 10,
        wait_for_response_delay = 1,
      })
    end
  },

  -- 表格模式
  {
    "dhruvasagar/vim-table-mode",
    ft = { "markdown" },
    config = function()
      vim.g.table_mode_corner = '|'
      vim.g.table_mode_corner_corner = '+'
      vim.g.table_mode_header_fillchar = '='
      vim.g.table_mode_align_char = ':'
      vim.g.table_mode_delimiter = '|'
      vim.g.table_mode_fillchar = '-'

      
      
      
    end
  },
}
