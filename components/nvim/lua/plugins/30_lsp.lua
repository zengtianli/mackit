-- ==========================================
-- 30 · LSP（lsp-zero v3 + mason + lazydev，配置在 config/lsp.lua）
-- 轮 3 计划：去 lsp-zero，迁原生 vim.lsp.config + mason v2
-- ==========================================

return {
  require("config.lsp")[1],
}
