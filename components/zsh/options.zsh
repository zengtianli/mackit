# Paths are deduplicated; no package installation at interactive startup.
typeset -U path PATH
path=("$HOME/.local/bin" /opt/homebrew/bin /usr/local/bin $path)
export EDITOR=nvim
export VISUAL=nvim
HISTFILE="$HOME/.zsh_history"
HISTSIZE=50000
SAVEHIST=50000
setopt APPEND_HISTORY SHARE_HISTORY HIST_IGNORE_ALL_DUPS AUTO_CD
bindkey -v
KEYTIMEOUT=10

