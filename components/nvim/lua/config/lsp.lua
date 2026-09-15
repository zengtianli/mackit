-- ==========================================
-- LSP 配置（nvim 0.11+ 原生 vim.lsp.config + vim.lsp.enable）
-- 轮 3 重构（2026-05-09）：去 lsp-zero v3 / 升 mason v2 / server config 搬到 ./lsp/<name>.lua runtime path
-- ==========================================

local M = {}
local F = {}
local documentation_window_open = false

-- 文档/签名浮窗自动展开
F.configureDocAndSignature = function()
	vim.lsp.handlers["textDocument/signatureHelp"] = vim.lsp.with(
		vim.lsp.handlers.signature_help, {
			focusable = false,
			border = "rounded",
			zindex = 60,
		}
	)
	local group = vim.api.nvim_create_augroup("lsp_diagnostics_hold", { clear = true })
	vim.api.nvim_create_autocmd({ "CursorHold" }, {
		pattern = "*",
		callback = function()
			if not documentation_window_open then
				vim.diagnostic.open_float(0, {
					scope = "cursor",
					focusable = false,
					zindex = 10,
					close_events = {
						"CursorMoved", "CursorMovedI", "BufHidden", "InsertCharPre",
						"InsertEnter", "WinLeave", "ModeChanged"
					},
				})
			end
		end,
		group = group,
	})
end

-- 文档浮窗带 500ms 防抖
local documentation_window_open_index = 0
local function show_documentation()
	documentation_window_open_index = documentation_window_open_index + 1
	local current_index = documentation_window_open_index
	documentation_window_open = true
	vim.defer_fn(function()
		if current_index == documentation_window_open_index then
			documentation_window_open = false
		end
	end, 500)
	vim.lsp.buf.hover()
end

-- LSP attach 时绑 keymap（保用户 muscle memory）
F.configureKeybinds = function()
	vim.api.nvim_create_autocmd('LspAttach', {
		desc = 'LSP actions',
		callback = function(event)
			local opts = { buffer = event.buf, noremap = true, nowait = true }
			
			
			
			
			
			
			
			
			
			
			
			

			-- ts_ls 关闭格式化（用 biome / prettier 走 LSP format）
			local client = vim.lsp.get_client_by_id(event.data.client_id)
			if client and client.name == "ts_ls" and vim.bo[event.buf].filetype ~= "javascript" then
				client.server_capabilities.documentFormattingProvider = false
				client.server_capabilities.documentRangeFormattingProvider = false
			end
			-- 关 semantic tokens（用户原 lsp-zero on_attach 行为保留）
			if client then
				client.server_capabilities.semanticTokensProvider = nil
			end
		end
	})
end

-- 启用的 LSP server 列表（runtime path: nvim/lsp/<name>.lua）
local SERVERS = {
	'lua_ls', 'jsonls', 'html', 'pyright', 'tailwindcss', 'ts_ls', 'biome',
	'cssls', 'taplo', 'ansiblels', 'terraformls', 'prismals', 'texlab', 'yamlls', 'gopls'
}

-- mason 装的 binary 列表（mason 包名 ≠ lspconfig server 名，单列）
local MASON_PACKAGES = {
	"lua-language-server", "json-lsp", "html-lsp", "pyright", "tailwindcss-language-server",
	"typescript-language-server", "biome", "css-lsp", "taplo", "ansible-language-server",
	"terraform-ls", "prisma-language-server", "texlab", "yaml-language-server", "gopls"
}

-- LSP 主 spec
M = {
	{
		'neovim/nvim-lspconfig',
		event = { "BufReadPre", "BufNewFile" },
		dependencies = {
			{ 'williamboman/mason.nvim', build = ":MasonUpdate" },
			{ 'williamboman/mason-lspconfig.nvim' },
			{ 'hrsh7th/cmp-nvim-lsp' },
			{ 'j-hui/fidget.nvim' },
			{ 'folke/lazydev.nvim', ft = "lua" },
		},
		config = function()
			-- Mason 仅做 binary 安装
			require('mason').setup({})
			require('mason-lspconfig').setup({
				ensure_installed = {}, -- 走 vim.lsp.enable 不依赖 mason-lspconfig 自动 enable
				automatic_enable = false,
			})

			-- 全局 capabilities（cmp_nvim_lsp + folding）— 给所有 server 共享
			local capabilities = vim.tbl_deep_extend(
				'force',
				vim.lsp.protocol.make_client_capabilities(),
				require('cmp_nvim_lsp').default_capabilities(),
				{ textDocument = { foldingRange = { dynamicRegistration = false, lineFoldingOnly = true } } }
			)
			vim.lsp.config('*', { capabilities = capabilities })

			-- 启用 server（自动从 nvim/lsp/<name>.lua 读 config）
			vim.lsp.enable(SERVERS)

			-- 文档/签名 + keymap
			F.configureDocAndSignature()
			F.configureKeybinds()

			-- diagnostic 配置
			vim.diagnostic.config({
				severity_sort = true, underline = true, signs = true,
				virtual_text = false, update_in_insert = false, float = true
			})

			-- 折叠支持
			vim.opt.foldmethod = "expr"
			vim.opt.foldexpr = "v:lua.vim.lsp.foldexpr()"
			vim.opt.foldenable = false

			-- fidget LSP 进度条 + lazydev
			require("fidget").setup({})
			require("lazydev").setup({})

			-- 自动格式化（保用户原有行为）
			vim.api.nvim_create_autocmd({ "BufWritePre" }, {
				pattern = { "*.tf", "*.tfvars", "*.lua" },
				callback = function() vim.lsp.buf.format() end,
			})
			vim.api.nvim_create_autocmd({ "BufWritePost" }, {
				pattern = { "*.hcl" },
				callback = function()
					local bufnr = vim.api.nvim_get_current_buf()
					local filename = vim.api.nvim_buf_get_name(bufnr)
					vim.fn.system(string.format("packer fmt %s", vim.fn.shellescape(filename)))
					vim.cmd("edit!")
				end,
			})

			-- format on save by ft（保留用户原 ft 白名单）
			local format_on_save_filetypes = {
				json = false, lua = true, html = true, css = true,
				javascript = true, typescript = true, typescriptreact = true,
				c = true, cpp = true, objc = true, objcpp = true,
				dockerfile = true, terraform = false, tex = true, toml = true, prisma = true
			}
			vim.api.nvim_create_autocmd("BufWritePre", {
				pattern = "*",
				callback = function()
					if format_on_save_filetypes[vim.bo.filetype] then
						local lineno = vim.api.nvim_win_get_cursor(0)
						vim.lsp.buf.format({ async = false })
						pcall(vim.api.nvim_win_set_cursor, 0, lineno)
					end
				end,
			})
		end
	},
}

return M
