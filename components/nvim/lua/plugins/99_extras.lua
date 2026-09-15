-- ==========================================
-- 99 · 杂项（CSV / 命令行增强）
-- ==========================================

return {
  -- CSV 彩虹列
  {
    'cameron-wags/rainbow_csv.nvim',
    config = true,
    ft = { 'csv', 'tsv', 'csv_semicolon', 'csv_whitespace', 'csv_pipe', 'rfc_csv', 'rfc_semicolon' },
    cmd = { 'RainbowDelim', 'RainbowDelimSimple', 'RainbowDelimQuoted', 'RainbowMultiDelim' }
  },

  -- cmdline popup 补全
  {
    'gelguy/wilder.nvim',
    event = "CmdlineEnter",
    config = function()
      local wilder = require('wilder')
      wilder.setup { modes = { ':' }, next_key = '<Tab>', previous_key = '<S-Tab>' }
      wilder.set_option('renderer', wilder.popupmenu_renderer(
        wilder.popupmenu_palette_theme({
          highlights = { border = 'Normal' },
          left = { ' ' },
          right = { ' ', wilder.popupmenu_scrollbar() },
          border = 'rounded', max_height = '75%', min_height = 0,
          prompt_position = 'top', reverse = 0
        })
      ))
      wilder.set_option('pipeline', {
        wilder.branch(
          wilder.cmdline_pipeline({ language = 'vim', fuzzy = 1 }),
          wilder.search_pipeline()
        )
      })
    end
  },
}
