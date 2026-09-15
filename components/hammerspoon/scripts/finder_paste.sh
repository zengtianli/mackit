#!/bin/bash

# paste_to_finder.sh - 独立的Finder粘贴工具
# 版本: 1.1.0
# 作者: tianli

# 引入通用函数库
source "$(dirname "${BASH_SOURCE[0]}")/common_functions.sh"

# 脚本信息
readonly SCRIPT_VERSION="1.1.0"
readonly SCRIPT_AUTHOR="tianli"
readonly SCRIPT_UPDATED="2024-12"

# 显示版本信息
show_version() {
    echo "Finder粘贴工具 v${SCRIPT_VERSION}"
    echo "作者: ${SCRIPT_AUTHOR}"
}

# 显示帮助信息
show_help() {
    show_help_header "$0" "Finder粘贴工具 - 智能粘贴到Finder目录"
    echo "    --use-commands   使用命令行方式（而非AppleScript）"
    show_help_footer
    
    echo "参数:"
    echo "    目标目录         要粘贴到的目录（可选，默认使用Finder当前目录）"
    echo ""
    echo "示例:"
    echo "    $0                           # 粘贴到Finder当前位置"
    echo "    $0 ~/Desktop                 # 粘贴到桌面"
    echo "    $0 \"$HOME/Documents\" # 粘贴到指定目录"
    echo ""
    echo "功能:"
    echo "    - 自动检测Finder当前目录"
    echo "    - 支持文件、文本等各种剪贴板内容"
    echo "    - 智能错误处理"
}

# 执行粘贴操作（方案A：使用系统命令）
paste_with_commands() {
    local target_dir="$1"

    # 2026-06-01 用 NSPasteboard readObjectsForClasses:{NSURL} 正确读取真·Finder 文件拷贝
    # （旧 `pbpaste | grep file://` 对真实文件拷贝返回空 → 静默失败；移植自 raycast folder_paste.sh）
    local file_paths
    file_paths=$(osascript -e '
use framework "AppKit"
set pb to current application'"'"'s NSPasteboard'"'"'s generalPasteboard()
set fileURLs to pb'"'"'s readObjectsForClasses:{current application'"'"'s NSURL} options:(missing value)
if fileURLs is missing value or (count of fileURLs) = 0 then
    return "NO_FILES"
end if
set paths to {}
repeat with u in fileURLs
    set end of paths to (u'"'"'s |path|()) as text
end repeat
set AppleScript'"'"'s text item delimiters to linefeed
return paths as text
' 2>/dev/null)

    if [ "$file_paths" != "NO_FILES" ] && [ -n "$file_paths" ]; then
        # 剪贴板包含文件 → 确定性 cp -R（不依赖 Finder 焦点）
        show_processing "检测到文件，正在粘贴..."
        while IFS= read -r file_path; do
            [ -z "$file_path" ] && continue
            if [ -e "$file_path" ]; then
                cp -R "$file_path" "$target_dir/"
                show_success "已复制: $(basename "$file_path")"
            fi
        done <<< "$file_paths"
    else
        # 剪贴板包含文本或其他内容，创建文件
        local clipboard_content=$(pbpaste)
        if [ -n "$clipboard_content" ]; then
            # 创建临时文件名
            local timestamp=$(date +%Y%m%d_%H%M%S)
            local temp_file=$(generate_unique_filename "pasted_text_$timestamp" ".txt" "$target_dir")
            
            echo "$clipboard_content" > "$temp_file"
            show_success "已创建文本文件: $(basename "$temp_file")"
        else
            show_warning "剪贴板为空"
            return 1
        fi
    fi
}

# 执行粘贴操作（方案B：简化的AppleScript）
paste_with_applescript() {
    local target_dir="$1"
    
    show_processing "正在粘贴到 $(basename "$target_dir")..."
    
    # 更简单的AppleScript方案
    osascript <<EOF
tell application "Finder"
    activate
    set targetFolder to POSIX file "$target_dir" as alias
    open targetFolder
    delay 0.8
end tell

-- 直接发送粘贴命令
tell application "System Events"
    delay 0.5
    keystroke "v" using command down
end tell
EOF
    
    if [ $? -eq 0 ]; then
        show_success "粘贴完成"
        return 0
    else
        show_error "粘贴失败"
        return 1
    fi
}

# 主函数
main() {
    local target_dir=""
    # 2026-06-01 默认改 false：走确定性 cp -R（不依赖 Finder 前台焦点），
    # 取代原 AppleScript 模拟 ⌘V（焦点不对会静默失败）。--use-applescript 可显式回退旧行为。
    local use_applescript=false

    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            --version)
                show_version
                exit 0
                ;;
            --use-commands)
                use_applescript=false
                shift
                ;;
            --use-applescript)
                use_applescript=true
                shift
                ;;
            -*)
                show_error "未知选项: $1"
                show_help
                exit 1
                ;;
            *)
                target_dir="$1"
                shift
                ;;
        esac
    done
    
    # 确定目标目录
    if [ -z "$target_dir" ]; then
        target_dir=$(get_finder_directory)
        show_info "目标目录: $(basename "$target_dir")"
    fi
    
    # 验证目标目录
    validate_finder_directory "$target_dir"
    
    # 执行粘贴
    if [ "$use_applescript" = true ]; then
        paste_with_applescript "$target_dir"
    else
        paste_with_commands "$target_dir"
    fi
}

# 运行主程序
main "$@" 