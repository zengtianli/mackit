-- Explicit user-triggered runners. Paths remain separate from shell syntax.
local M = {}
function M.run_code()
 local kind=vim.bo.filetype
 vim.cmd("write")
 local file=vim.api.nvim_buf_get_name(0)
 local quote=vim.fn.shellescape
 local stem=vim.fn.fnamemodify(file,":r")
 local output=stem..".mackit-run"
 local command
 if kind=="markdown" then vim.cmd("MarkdownPreview");return
 elseif kind=="html" then vim.fn.jobstart({"open",file});return
 elseif kind=="python" then command={"python3",file}
 elseif kind=="javascript" then command={"node",file}
 elseif kind=="sh" then command={"bash",file}
 elseif kind=="racket" then command={"racket",file}
 elseif kind=="go" then command={"go","run","."}
 elseif kind=="c" or kind=="cpp" then
  command=(kind=="c" and "cc " or "clang++ -std=c++11 -Wall ")..quote(file).." -o "..quote(output).." && "..quote(output)
 elseif kind=="cs" then command="mcs "..quote(file).." -out:"..quote(output..".exe").." && mono "..quote(output..".exe")
 elseif kind=="java" then command="javac "..quote(file).." && java -cp "..quote(vim.fn.fnamemodify(file,":h")).." "..quote(vim.fn.fnamemodify(file,":t:r"))
 else vim.notify("未支持的文件类型: "..kind,vim.log.levels.WARN);return end
 vim.cmd("botright 12new")
 vim.fn.jobstart(command,{term=true,cwd=vim.fn.fnamemodify(file,":h")})
end
return M
