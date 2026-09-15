# Widgets only; all bindings belong to keymaps.zsh.
_mackit_file() {
 local picked
 picked=$(fd --type f --hidden --exclude .git | fzf) || return
 [[ -n "$picked" ]] || return
 BUFFER="nvim -- ${(q)picked}"; zle accept-line
}
_mackit_dir() {
 local picked
 picked=$(fd --type d --hidden --exclude .git | fzf) || return
 [[ -n "$picked" ]] && builtin cd -- "$picked"
 zle reset-prompt
}
_mackit_grep() {
 local selected file
 selected=$(rg --line-number --no-heading --color=never --smart-case "${LBUFFER:-.}" | fzf) || return
 file="${selected%%:*}"
 [[ -n "$file" ]] || return
 BUFFER="nvim -- ${(q)file}"; zle accept-line
}
_mackit_git() { zle -I; command lazygit; zle reset-prompt; }
_mackit_finder() { command open .; zle reset-prompt; }
for name in file dir grep git finder; do zle -N "_mackit_$name"; done
fif() {
 local file
 [[ -n "$1" ]] || { print 'Usage: fif pattern'; return 2; }
 file=$(rg -l -- "$1" | fzf) || return
 [[ -n "$file" ]] && nvim -- "$file"
}

