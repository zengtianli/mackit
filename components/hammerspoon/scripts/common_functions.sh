#!/bin/bash

# ===== Shell 脚本通用函数库 =====
# 消费者: finder_compress.sh / finder_paste.sh（仅保留它们实际调用的函数）
# 2026-07-21 瘦身: 删除无消费者的 Python 环境检查/重试/临时目录等函数与
#                  stale 的 useful_scripts 路径常量（老工作区已废）

# ===== 颜色定义 =====
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# ===== 核心显示函数 =====

show_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

show_error() {
    echo -e "${RED}❌ $1${NC}"
}

show_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

show_processing() {
    echo -e "${BLUE}🔄 $1${NC}"
}

show_info() {
    echo -e "${BLUE}ℹ️ $1${NC}"
}

# ===== 错误处理 =====

# 致命错误 - 立即退出
fatal_error() {
    show_error "$1"
    exit 1
}

# ===== 目录操作 =====

safe_cd() {
    local target_dir="$1"
    if cd "$target_dir" 2>/dev/null; then
        return 0
    else
        show_error "无法进入目录: $target_dir"
        return 1
    fi
}

ensure_directory() {
    local dir="$1"
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir" || {
            show_error "无法创建目录: $dir"
            return 1
        }
    fi
    return 0
}

# ===== Finder 集成 =====

# 获取 Finder 当前目录（POSIX 路径）
get_finder_directory() {
    osascript <<'EOF'
tell application "Finder"
    if (count of (selection as list)) > 0 then
        set firstItem to item 1 of (selection as list)
        if class of firstItem is folder then
            POSIX path of (firstItem as alias)
        else
            POSIX path of (container of firstItem as alias)
        end if
    else
        POSIX path of (insertion location as alias)
    end if
end tell
EOF
}

# 获取 Finder 选中文件列表（每行一个 POSIX 路径）
get_finder_selection() {
    osascript <<'EOF'
tell application "Finder"
    set selectedItems to selection
    if (count of selectedItems) = 0 then
        return ""
    end if

    set itemPaths to {}
    repeat with selectedItem in selectedItems
        set end of itemPaths to POSIX path of (selectedItem as alias)
    end repeat

    set AppleScript's text item delimiters to linefeed
    set pathsText to itemPaths as text
    set AppleScript's text item delimiters to ""

    return pathsText
end tell
EOF
}

# 在 Finder 中显示指定文件
reveal_file_in_finder() {
    local file_path="$1"
    osascript <<EOF
tell application "Finder"
    activate
    reveal POSIX file "$file_path" as alias
end tell
EOF
}

# 验证目录存在且可写
validate_finder_directory() {
    local target_dir="$1"

    if [ -z "$target_dir" ]; then
        fatal_error "无法获取Finder当前目录"
    fi

    if [ ! -d "$target_dir" ]; then
        fatal_error "目录不存在: $target_dir"
    fi

    if [ ! -w "$target_dir" ]; then
        fatal_error "目录不可写: $target_dir"
    fi

    return 0
}

# 生成唯一文件名（已存在则加数字后缀）
generate_unique_filename() {
    local base_name="$1"
    local extension="$2"
    local output_dir="$3"

    if [ -z "$base_name" ]; then
        base_name="file_$(date +%Y%m%d_%H%M%S)"
    fi

    local file_path="$output_dir/${base_name}${extension}"

    local counter=1
    while [ -e "$file_path" ]; do
        file_path="$output_dir/${base_name}_${counter}${extension}"
        ((counter++))
    done

    echo "$file_path"
}

# ===== 版本和帮助模板 =====

show_version_template() {
    echo "脚本版本: ${SCRIPT_VERSION:-未知}"
    echo "作者: ${SCRIPT_AUTHOR:-未知}"
    echo "更新日期: ${SCRIPT_UPDATED:-未知}"
}

show_help_header() {
    local script_name="$1"
    local script_desc="$2"
    echo "$script_desc"
    echo ""
    echo "用法: $script_name [选项] [参数]"
    echo ""
    echo "选项:"
}

show_help_footer() {
    echo "    -h, --help       显示此帮助信息"
    echo "    --version        显示版本信息"
    echo ""
}
