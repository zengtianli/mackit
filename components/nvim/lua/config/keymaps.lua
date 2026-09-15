-- All custom Neovim keys. Actions and plugin configuration never bind keys.
local M = { entries = {} }
local function add(mode,key,action,desc,extra)
  local v=extra or {};v.mode,v.key,v.action,v.desc=mode,key,action,desc
  table.insert(M.entries,v)
end
local function p(mode,key,action,desc) add(mode,key,action,desc,{profile="tianli"}) end
local function plug(name, action) return function()
  require("lazy").load({plugins={name}})
  if type(action)=="string" then vim.cmd(action) else action() end
end end
local function fzf(fn) return function() require("fzf-lua")[fn]() end end
-- Personal muscle memory.
for _,v in ipairs({
 {"S","<cmd>w<cr>","保存"},{"Q","<cmd>q<cr>","退出"},{"U","<C-r>","重做"},
 {"r",function()require("actions.runner").run_code()end,"运行文件"},
 {"R",plug("yazi.nvim","Yazi"),"文件管理器"},
 {"<C-h>",fzf("oldfiles"),"最近文件"},{"<C-w>",fzf("buffers"),"已打开文件"},
 {"<Up>","<cmd>resize +5<cr>","增加高度"},{"<Down>","<cmd>resize -5<cr>","减少高度"},
 {"<Left>","<cmd>vertical resize -5<cr>","减少宽度"},{"<Right>","<cmd>vertical resize +5<cr>","增加宽度"},
 {"srh","<C-w>b<C-w>K","上下布局"},{"srv","<C-w>b<C-w>H","左右布局"},{"\\v","v$h","选择至行尾"}
})do p("n",v[1],v[2],v[3])end
for _,v in ipairs({
 {"; ",":","命令模式"},{"J","15j","下移15行"},{"K","15k","上移15行"},
 {"W","5w","前进5词"},{"B","5b","后退5词"},{"H","0","行首"},{"L","$","行尾"},
 {"<M-j>","J","合并行"},{"`","~","切换大小写"},{"<C-i>","<C-o>","后退跳转"},
 {"<C-o>","<C-i>","前进跳转"},{",.","%","匹配括号"}
})do p({"n","x"},v[1]:gsub(" $",""),v[2],v[3])end
p("o","H","0","操作至行首");p("o","L","$","操作至行尾")
p("x","Y",'"+y',"复制到系统剪贴板")
-- Shared editing, window and numbering keys.
add("n","<leader>w","<cmd>w<cr>","保存文件")
add("n","<leader>q","<cmd>close<cr>","关闭窗口")
add("n","<leader>o","za","切换折叠")
add("n","<leader>sw",function()vim.wo.wrap=not vim.wo.wrap end,"切换自动折行")
add("n","<leader><CR>","<cmd>nohlsearch<cr>","清除搜索高亮")
add("n","<leader>un",function()vim.wo.number=not vim.wo.number end,"切换绝对行号")
add("n","<leader>ur",function()vim.wo.relativenumber=not vim.wo.relativenumber end,"切换相对行号")
for key,cmd in pairs({h="leftabove vsplit",j="belowright split",k="aboveleft split",l="rightbelow vsplit"})do
 p("n","s"..key,"<cmd>"..cmd.."<cr>","分屏 "..key)
 add("n","<leader>s"..key,"<C-w>"..key,"切换窗口 "..key)
end
add("x","<leader>nl",":<C-u>lua require('actions.text').number_lines()<CR>","选中行添加01_、02_编号")
p("n","<leader>rp","<cmd>ReplaceToPrefecture<cr>","县级地名转地级市")
for key,cmd in pairs({rb="RemoveBlankLines",rl="RemoveTrailingSpaces"})do add("n","<leader>"..key,"<cmd>"..cmd.."<cr>",cmd)end
p("n","<leader>ro","<cmd>g/^\\s*#.*$/d<cr>","删除井号注释行")
p("n","<leader>rk","<cmd>%s/\\s\\+//g<cr>","删除全文空白")
p("x","<leader>rk",":s/\\s\\+//g<cr>","删除选中行空白")
p("n","<leader>rv","<cmd>g/^[^a-zA-Z0-9\\u4e00-\\u9fa5\\[\\]\\(\\)\\{\\}*`,.;:]*$/d<cr>","删除无效行")
-- Search: developer keeps native Ctrl-w.
for key,fn in pairs({["<C-p>"]="files",["<C-q>"]="commands",["<leader>fb"]="buffers",
 ["<leader>rs"]="resume",["z="]="spell_suggest",["<leader>d"]="diagnostics_workspace",["<leader>gi"]="git_status"})do
 add("n",key,fzf(fn),"搜索 "..fn)
end
add("n","<C-f>",function()require("fzf-lua").grep({search=""})end,"搜索内容")
add("x","<C-f>",fzf("grep_visual"),"搜索选中文本")
add("n","<leader>e",plug("yazi.nvim","Yazi"),"文件管理器")
add("n","<C-g>",plug("lazygit.nvim","LazyGit"),"LazyGit")
add("n","<leader>pl","<cmd>Lazy<cr>","插件管理")
-- Plugin commands.
for _,v in ipairs({
 {"<leader>v","aerial.nvim","AerialToggle!","代码大纲"},
 {"<leader>mt","markdown-toc.nvim","Mtoc","生成目录"},
 {"<leader>mi","markdown-toc.nvim","Mtoc insert","插入目录"},
 {"<leader>mu","markdown-toc.nvim","Mtoc update","更新目录"},
 {"<leader>mr","markdown-toc.nvim","Mtoc remove","删除目录"},
 {"<leader>tm","vim-table-mode","TableModeToggle","表格模式"},
 {"<leader>tr","vim-table-mode","TableModeRealign","对齐表格"},
 {"<leader>tt","vim-table-mode","Tableize","转换表格"},
 {"<leader>mp","marp-nvim","MarpToggle","Marp预览"},
 {"<leader>ms","marp-nvim","MarpStatus","Marp状态"},
 {"<leader>g-","gitsigns.nvim","Gitsigns prev_hunk","上一处改动"},
 {"<leader>g=","gitsigns.nvim","Gitsigns next_hunk","下一处改动"},
 {"<leader>gb","gitsigns.nvim","Gitsigns blame_line","Git归属"},
 {"<leader>gr","gitsigns.nvim","Gitsigns reset_hunk","撤销当前改动块"},
 {"<leader>l","gitsigns.nvim","Gitsigns preview_hunk","预览改动块"}
})do add("n",v[1],plug(v[2],v[3]),v[4])end
p("n","{",plug("aerial.nvim","AerialPrev"),"上一个符号")
p("n","}",plug("aerial.nvim","AerialNext"),"下一个符号")
add("n","[c",plug("nvim-treesitter-context",function()require("treesitter-context").go_to_context()end),"代码上下文")
for _,key in ipairs({"cn","cu"})do
 add("n","<leader>"..key,plug("Comment.nvim",function()require("Comment.api").toggle.linewise.current()end),"切换行注释")
 add("x","<leader>"..key,plug("Comment.nvim",function()
   vim.api.nvim_feedkeys(vim.api.nvim_replace_termcodes("<Esc>",true,false,true),"nx",false)
   require("Comment.api").toggle.linewise(vim.fn.visualmode())
 end),"切换选区注释")
end
-- sh split conflict resolved: substitute word now se.
for key,fn in pairs({s="operator",ss="line",sI="eol"})do
 p("n",key,plug("substitute.nvim",function()require("substitute")[fn]()end),"替换 "..fn)
end
p("n","se",plug("substitute.nvim",function()require("substitute").operator({motion="e"})end),"替换到词尾")
p("x","s",plug("substitute.nvim",function()require("substitute").visual()end),"替换选区")
for key,cmd in pairs({go="Copilot",ge="Copilot enable",gd="Copilot disable"})do p("n","<leader>"..key,plug("copilot.vim",cmd),cmd)end
p("i","<C-p>","<Plug>(copilot-suggest)","请求AI建议")
p("i","<M-l>","<Plug>(copilot-next)","下一条AI建议（Ctrl-l保留补全）")
p("i","<C-h>","<Plug>(copilot-previous)","上一条AI建议")
add("i","<C-c>",function()return vim.fn["copilot#Accept"]("")end,"接受AI建议",{profile="tianli",expr=true})
p("n",",;",plug("nvim-notify",function()for _,v in ipairs(require("notify").history())do print(vim.inspect(v))end end),"通知历史")
add("n","<leader>c;",plug("nvim-notify",function()require("notify").dismiss()end),"清除通知")
add("n","<leader>ra",function()require("actions.runner").run_code()end,"运行文件")
add("n","<leader>'r",function()
 vim.cmd("noautocmd write")
 local result=vim.fn.system({"npx","--no-install","prisma","format"})
 if vim.v.shell_error==0 then vim.cmd("edit") else vim.notify(result,vim.log.levels.ERROR) end
end,"Prisma 格式化（使用项目已装依赖）",{scope="prisma"})
add("t","<C-n>","<C-\\><C-n>","离开终端输入")
add("t","<C-o>","<C-\\><C-n><C-o>","离开终端并跳转")
-- LSP keys bind only to attached buffers.
for key,fn in pairs({gd="definition",gi="implementation",go="type_definition",gr="references",
 ["<leader>h"]="hover",["<leader>rn"]="rename",["<leader>aw"]="code_action",["<leader>,"]="code_action"})do
 add("n",key,function()vim.lsp.buf[fn]()end,"LSP "..fn,{scope="lsp"})
end
add("n","gD",function()vim.cmd("tab split");vim.lsp.buf.definition()end,"新标签页定义",{scope="lsp"})
add("i","<C-f>",vim.lsp.buf.signature_help,"函数签名",{scope="lsp"})
add("n","<leader>-",function()vim.diagnostic.jump({count=-1})end,"上一个诊断",{scope="lsp"})
add("n","<leader>=",function()vim.diagnostic.jump({count=1})end,"下一个诊断",{scope="lsp"})
-- Preserve the personal letter-coded 1..199-line jumps without 398 repeated lines.
local digits={"o","a","r","s","t","d","h","n","e","i"}
for _,direction in ipairs({{"[","k"},{"'","j"}})do
 for count=1,199 do
  local encoded=tostring(count):gsub("%d",function(d)return digits[tonumber(d)+1]end)
  p({"n","x","s","o"},direction[1]..encoded.."<leader>",count..direction[2],"编码跳行 "..count..direction[2])
 end
end
function M.setup(buffer,scope)
 local profile=require("config.profile").name
 local seen={}
 for _,v in ipairs(M.entries)do
  if (not v.profile or v.profile==profile) and ((buffer and v.scope==(scope or "lsp"))or(not buffer and not v.scope))then
   for _,mode in ipairs(type(v.mode)=="table" and v.mode or {v.mode})do
    local id=mode..":"..v.key -- letter case is significant; control aliases checked by runtime tests
    assert(not seen[id],"Duplicate MacKit key "..id);seen[id]=true
   end
   vim.keymap.set(v.mode,v.key,v.action,{desc=v.desc,silent=true,buffer=buffer,expr=v.expr})
  end
 end
 if not buffer then
  vim.api.nvim_create_autocmd("LspAttach",{group=vim.api.nvim_create_augroup("MacKitKeys",{clear=true}),callback=function(e)M.setup(e.buf)end})
  vim.api.nvim_create_autocmd("FileType",{group="MacKitKeys",pattern="prisma",callback=function(e)M.setup(e.buf,"prisma")end})
 end
end

M.lazy={{cmd="install",key="i"},{cmd="update",key="u"},{cmd="sync",key="s"},{cmd="clean",key="cl"},{cmd="check",key="ch"},{cmd="log",key="l"},{cmd="restore",key="rs"},{cmd="profile",key="p"}}


function M.completion(cmp, moveCursorBeforeComma, has_words_before)
 return cmp.mapping.preset.insert({
      ['<C-l>'] = cmp.mapping.complete(),
      ['<c-f>'] = cmp.mapping({
        i = function(fallback)
          cmp.close()
          fallback()
        end
      }),
      ['<CR>'] = cmp.mapping({
        i = function(fallback)
          if cmp.visible() and cmp.get_active_entry() then
            cmp.confirm({ behavior = cmp.ConfirmBehavior.Replace, select = false })
          else
            fallback()
          end
        end
      }),
      ["<Tab>"] = cmp.mapping({
        i = function(fallback)
          if cmp.visible() then
            cmp.select_next_item({ behavior = cmp.SelectBehavior.Insert })
            moveCursorBeforeComma()
          elseif has_words_before() then
            cmp.complete()
            moveCursorBeforeComma()
          else
            fallback()
          end
        end,
      }),
      ["<S-Tab>"] = cmp.mapping({
        i = function(fallback)
          if cmp.visible() then
            cmp.select_prev_item({ behavior = cmp.SelectBehavior.Insert })
            moveCursorBeforeComma()
          else
            fallback()
          end
        end,
      }),
    })
end

M.picker = {
          builtin = {
            ["<c-f>"] = "toggle-fullscreen", ["<c-r>"] = "toggle-preview-wrap",
            ["<c-p>"] = "toggle-preview", ["<c-y>"] = "preview-page-down",
            ["<c-l>"] = "preview-page-up", ["<S-left>"] = "preview-page-reset"
          },
          fzf = {
            ["esc"] = "abort", ["ctrl-h"] = "unix-line-discard", ["ctrl-k"] = "half-page-down",
            ["ctrl-b"] = "half-page-up", ["ctrl-n"] = "beginning-of-line", ["ctrl-a"] = "end-of-line",
            ["alt-a"] = "toggle-all", ["f3"] = "toggle-preview-wrap", ["f4"] = "toggle-preview",
            ["shift-down"] = "preview-page-down", ["shift-up"] = "preview-page-up",
            ["ctrl-e"] = "down", ["ctrl-u"] = "up"
          }
        }

M.multicursor = { "<C-n>", "<C-Down>", "<C-Up>" }

M.yazi = {
        show_help = '<f1>', open_file_in_vertical_split = '<c-v>',
        open_file_in_horizontal_split = '<c-x>', open_file_in_tab = '<c-t>',
        grep_in_directory = '<c-f>', replace_in_directory = '<c-r>',
        cycle_open_buffers = '<tab>', copy_relative_path_to_selected_files = '<c-y>',
        send_to_quickfix_list = '<c-q>'
      }

return M
