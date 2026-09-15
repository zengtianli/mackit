# The final keyboard layer runs after Atuin/Zim; no ordering accidents.
# format: bindkey -M MODE KEY WIDGET # human description
export FZF_DEFAULT_OPTS="${FZF_DEFAULT_OPTS:-} --bind=ctrl-f:top,change:top,ctrl-j:down,ctrl-k:up"
bindkey -M viins '^P' _mackit_file # 找文件并用 nvim 打开
bindkey -M viins '^T' _mackit_dir # 找目录并进入
bindkey -M viins '^F' _mackit_grep # 按内容找文件
bindkey -M viins '^G' _mackit_git # LazyGit
bindkey -M viins '^O' _mackit_finder # Finder 打开当前目录
if [[ -n "$widgets[atuin-search-viins]" ]]; then
 bindkey -M viins '^R' atuin-search-viins # Atuin 历史搜索
else
 bindkey -M viins '^R' history-incremental-search-backward # 内置历史搜索（未安装 Atuin）
fi
bindkey -M viins '^U' vi-kill-line # 删除至行首
# New users get common line-editing keys; personal preset retains original viins behavior.
if [[ "$MACKIT_PROFILE" == developer ]]; then
 bindkey -M viins '^A' beginning-of-line # 命令行首
 bindkey -M viins '^E' end-of-line # 命令行尾
fi
