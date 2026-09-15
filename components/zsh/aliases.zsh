# Familiar command names with explicit sources.
alias rl='source ~/.zshrc'
alias lg=lazygit
alias ra=yazi
smart_vim() { (( $# )) && mkdir -p -- "$(dirname -- "$1")"; nvim "$@"; }
alias vim=smart_vim
(( $+commands[eza] )) && {
 alias ll='eza -l --icons --group-directories-first'
 alias la='eza -la --icons --group-directories-first'
 alias lt='eza -T -L 2 --icons'
 alias lsg='eza -l --git --icons'
}
config() { "$MACKIT_ROOT/bin/mackit" edit "$@"; }
unalias cfg 2>/dev/null
function cfg { cd "$MACKIT_ROOT"; }
