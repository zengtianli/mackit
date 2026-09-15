-- ==========================================
-- 统一文件类型配置
-- ==========================================

local M = {}

function M.setup()
  -- ==========================================
  -- 通用设置
  -- ==========================================
  
  -- 基础语言的缩进设置（2空格）
  local basic_indent_langs = { 'c', 'java', 'graphml', 'racket', 'text' }
  for _, lang in ipairs(basic_indent_langs) do
    vim.api.nvim_create_autocmd("FileType", {
      pattern = lang,
      callback = function()
        vim.opt_local.shiftwidth = 2
        vim.opt_local.softtabstop = 2
        vim.opt_local.expandtab = true
        vim.opt_local.smarttab = true
      end
    })
  end

  -- 4空格缩进的语言
  local wide_indent_langs = { 'cs', 'swift' }
  for _, lang in ipairs(wide_indent_langs) do
    vim.api.nvim_create_autocmd("FileType", {
      pattern = lang,
      callback = function()
        vim.opt_local.shiftwidth = 4
        vim.opt_local.softtabstop = 4
        vim.opt_local.expandtab = true
        vim.opt_local.smarttab = true
      end
    })
  end

  -- ==========================================
  -- 特定语言配置
  -- ==========================================

  -- Racket 配置
  vim.api.nvim_create_autocmd("FileType", {
    pattern = "racket",
    callback = function()
      vim.g.AutoPairs = {
        ['('] = ')', ['['] = ']', ['{'] = '}', ['"'] = '"',
        ["`"] = "`", ['```'] = '```', ['"""'] = '"""', ["'''"] = "'''"
      }
    end
  })



  -- Markdown 配置
  vim.api.nvim_create_autocmd("FileType", {
    pattern = "markdown",
    callback = function()
      -- 基础设置
      vim.opt_local.shiftwidth = 2
      vim.opt_local.softtabstop = 2
      vim.opt_local.expandtab = true
      vim.opt_local.smarttab = true
    end
  })

end

return M
