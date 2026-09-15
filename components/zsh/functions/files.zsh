# Optional helpers; dependencies are checked when the function is used.
fdf() { 
  # 如果第一个参数包含通配符，自动添加-g选项
  if [[ "$1" == *"*"* ]] || [[ "$1" == *"?"* ]]; then
    fd -g "$@"
  else
    fd "$@"
  fi
}

preview() {
  if command -v bat &> /dev/null; then
    bat --style=numbers --color=always "$1"
  else
    cat "$1"
  fi
}

disk_usage() {
  if command -v dust &> /dev/null; then
    dust -d 1 "${1:-.}"
  elif command -v ncdu &> /dev/null; then
    ncdu "${1:-.}"
  else
    du -sh "${1:-.}"/* | sort -hr
  fi
}

view() {
  local file="$1"
  if [[ -z "$file" ]]; then
    echo "用法: view <文件名>"
    return 1
  fi
  
  if [[ ! -f "$file" ]]; then
    echo "文件不存在: $file"
    return 1
  fi
  
  # 根据文件类型选择查看工具
  case "${file##*.}" in
    json)
      if command -v jq &> /dev/null; then
        jq '.' "$file" | bat -l json
      elif command -v bat &> /dev/null; then
        bat -l json "$file"
      else
        cat "$file"
      fi
      ;;
    yml|yaml)
      if command -v yq &> /dev/null; then
        yq '.' "$file" | bat -l yaml
      elif command -v bat &> /dev/null; then
        bat -l yaml "$file"
      else
        cat "$file"
      fi
      ;;
    *)
      if command -v bat &> /dev/null; then
        bat "$file"
      else
        cat "$file"
      fi
      ;;
  esac
}

lsmart() {
  local dir="${1:-.}"
  
  if command -v eza &> /dev/null; then
    # 如果目录包含Git仓库，显示Git状态
    if [[ -d "$dir/.git" ]] || git -C "$dir" rev-parse --git-dir &>/dev/null; then
      eza -la --git --icons --group-directories-first "$dir"
    else
      eza -la --icons --group-directories-first "$dir"
    fi
  else
    ls -la "$dir"
  fi
}

ff() {
  local action="${1:-view}"
  
  if ! command -v fd &> /dev/null || ! command -v fzf &> /dev/null; then
    echo "需要安装 fd 和 fzf: brew install fd fzf"
    return 1
  fi
  
  local file=$(fd --type f | fzf --preview 'bat --style=numbers --color=always {}' --header="[📁 选择文件进行 $action 操作]")
  
  if [[ -n "$file" ]]; then
    case $action in
      edit|e)
        nvim "$file"
        ;;
      view|v)
        view "$file"
        ;;
      copy|cp)
        if command -v pbcopy &> /dev/null; then
          cat "$file" | pbcopy
          echo "✅ 文件内容已复制到剪贴板: $file"
        else
          echo "❌ macOS剪贴板命令不可用"
        fi
        ;;
      delete|rm)
        echo -n "❓ 确认删除文件 '$file'? [y/N]: "
        read -r confirm
        if [[ "$confirm" =~ ^[Yy]$ ]]; then
          rm "$file"
          echo "✅ 已删除: $file"
        fi
        ;;
      *)
        echo "❌ 未知操作: $action"
        echo "支持的操作: edit, view, copy, delete"
        ;;
    esac
  fi
}

dup() {
  if ! command -v czkawka_cli &> /dev/null; then
    echo "❌ 需要安装 czkawka"
    echo "💡 安装: brew install czkawka"
    return 1
  fi

  local action="${1:-help}"
  shift 2>/dev/null
  local dir="${1:-.}"
  
  case $action in
    find|f)
      echo "🔍 查找重复文件: $dir"
      czkawka_cli dup -d "$dir"
      ;;
    rm|delete)
      echo "🗑️  删除重复文件 (保留最新): $dir"
      czkawka_cli dup -d "$dir" --delete-method AEN
      ;;
    size)
      echo "📊 查找大于1M的重复文件: $dir"
      czkawka_cli dup -d "$dir" -x 1048576
      ;;
    link)
      echo "🔗 用硬链接替换重复文件: $dir"
      czkawka_cli dup -d "$dir" --delete-method Hardlink
      ;;
    help|h|*)
      echo "🔍 dup - 重复文件检测 (czkawka_cli)"
      echo "===================================="
      echo ""
      echo "用法: dup <命令> [目录]"
      echo ""
      echo "命令:"
      echo "  find, f     查找重复文件"
      echo "  rm, delete  删除重复 (保留最新)"
      echo "  size        只找大于1M的重复"
      echo "  link        用硬链接替换重复"
      echo "  help, h     显示帮助"
      echo ""
      echo "示例:"
      echo "  dup f ~/Downloads"
      echo "  dup size ~/Pictures"
      echo "  dup rm ~/Downloads"
      echo ""
      echo "其他命令:"
      echo "  dupimg  查找相似图片"
      echo "  dupvid  查找相似视频"
      echo "  dupe    查找空文件/文件夹"
      echo "  dupbad  查找损坏文件/无效链接"
      ;;
  esac
}

dupimg() {
  if ! command -v czkawka_cli &> /dev/null; then
    echo "❌ 需要安装 czkawka"; echo "💡 brew install czkawka"; return 1
  fi
  echo "🖼️  查找相似图片: ${1:-.}"
  czkawka_cli similar-images -d "${1:-.}"
}

dupvid() {
  if ! command -v czkawka_cli &> /dev/null; then
    echo "❌ 需要安装 czkawka"; echo "💡 brew install czkawka"; return 1
  fi
  echo "🎬 查找相似视频: ${1:-.}"
  czkawka_cli similar-videos -d "${1:-.}"
}

dupe() {
  if ! command -v czkawka_cli &> /dev/null; then
    echo "❌ 需要安装 czkawka"; echo "💡 brew install czkawka"; return 1
  fi
  local dir="${1:-.}"
  echo "📁 空文件夹:"
  czkawka_cli empty-folders -d "$dir"
  echo ""
  echo "📄 空文件:"
  czkawka_cli empty-files -d "$dir"
}

dupbad() {
  if ! command -v czkawka_cli &> /dev/null; then
    echo "❌ 需要安装 czkawka"; echo "💡 brew install czkawka"; return 1
  fi
  local dir="${1:-.}"
  echo "🔗 查找无效符号链接:"
  czkawka_cli invalid-symlinks -d "$dir"
  echo ""
  echo "🗑️  查找损坏文件:"
  czkawka_cli broken-files -d "$dir"
}
