local M = {}
local path = (vim.env.XDG_CONFIG_HOME or (vim.env.HOME .. "/.config")) .. "/mackit/profile.json"
local ok, data = pcall(vim.fn.readfile, path)
local parsed = ok and vim.json.decode(table.concat(data, "\n")) or {}
M.name = vim.env.MACKIT_PROFILE or parsed.profile or "developer"
M.personal = M.name == "tianli"
return M

