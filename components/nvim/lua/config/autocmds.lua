-- ==========================================
-- Neovim 自动命令配置
-- ==========================================

local M = {}

function M.setup()
    -- Markdown 文件启用拼写检查
    vim.api.nvim_create_autocmd({ "BufRead", "BufNewFile" }, { 
        pattern = "*.md", 
        command = "setlocal spell" 
    })

    -- 自动切换到文件所在目录
    vim.api.nvim_create_autocmd("BufEnter", { 
        pattern = "*", 
        callback = function() if require("config.profile").personal then vim.cmd("silent! lcd %:p:h") end end 
    })

    -- 恢复上次光标位置
    vim.api.nvim_create_autocmd("BufReadPost", {
        pattern = "*",
        callback = function()
            local last_pos = vim.fn.line("'\"")
            if last_pos > 1 and last_pos <= vim.fn.line("$") then
                vim.cmd("normal! g'\"")
            end
        end
    })

    -- 终端相关自动命令
    vim.api.nvim_create_autocmd("TermOpen", {
        pattern = "term://*",
        command = "startinsert"
    })

end

return M
