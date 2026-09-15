#!/bin/bash

source "$(dirname "${BASH_SOURCE[0]}")/common_functions.sh"

readonly SCRIPT_VERSION="1.1.0"
readonly SCRIPT_AUTHOR="tianli"
readonly SCRIPT_UPDATED="2024-12-01"

show_version() {
    show_version_template
}

show_help() {
    show_help_header "$0" "智能ZIP压缩工具"
    echo "    -o, --output     输出文件名（不含扩展名）"
    echo "    -d, --output-dir 输出目录"
    echo "    --exclude-ds     排除 .DS_Store 文件"
    show_help_footer
    echo "模式: 1. 指定文件/文件夹: $0 file1 dir1"
    echo "      2. Finder中选中文件: $0"
}

validate_input_files() {
    local validated_files=()
    for item in "$@"; do
        local expanded_path
        expanded_path=$(eval echo "$item")
        if [ -e "$expanded_path" ]; then
            validated_files+=("$(realpath "$expanded_path")")
        else
            show_warning "文件不存在: $item"
        fi
    done
    if [ ${#validated_files[@]} -eq 0 ]; then
        fatal_error "没有找到有效的文件或文件夹"
    fi
    printf '%s\n' "${validated_files[@]}"
}

determine_output_directory() {
    local first_file="$1"
    local specified_dir="$2"

    if [ -n "$specified_dir" ]; then
        local expanded_dir
        expanded_dir=$(eval echo "$specified_dir")
        ensure_directory "$expanded_dir"
        realpath "$expanded_dir"
        return
    fi

    if [ -z "$first_file" ]; then
        pwd
        return
    fi
    
    dirname "$(realpath "$first_file")"
}

compress_files() {
    local files_list="$1"
    local output_file="$2"
    local exclude_ds="$3"
    
    show_processing "正在压缩文件为 ZIP 格式"
    
    local output_dir
    output_dir=$(dirname "$output_file")
    local archive_name
    archive_name=$(basename "$output_file")
    
    local original_dir
    original_dir=$(pwd)
    safe_cd "$output_dir" || return 1
    
    local files_to_compress=()
    while IFS= read -r line; do
        files_to_compress+=("$(basename "$line")")
    done <<< "$files_list"

    show_info "项目数量: ${#files_to_compress[@]}"

    local zip_options="-r"
    [ "$exclude_ds" = true ] && zip_options="-r -x *.DS_Store"

    if zip $zip_options "$archive_name" "${files_to_compress[@]}" >/dev/null 2>&1; then
        show_success "ZIP压缩完成: $archive_name"
        safe_cd "$original_dir"
        return 0
    else
        show_error "ZIP压缩失败"
        safe_cd "$original_dir"
        return 1
    fi
}

main() {
    local output_name=""
    local output_dir_specified=""
    local exclude_ds=false
    local input_files=()
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help) show_help; exit 0 ;;
            --version) show_version; exit 0 ;;
            -o|--output) output_name="$2"; shift 2 ;;
            -d|--output-dir) output_dir_specified="$2"; shift 2 ;;
            --exclude-ds) exclude_ds=true; shift ;;
            -*) show_error "未知选项: $1"; show_help; exit 1 ;;
            *) input_files+=("$1"); shift ;;
        esac
    done
    
    local selected_files
    local use_finder_mode=false
    
    if [ ${#input_files[@]} -gt 0 ]; then
        show_info "命令行模式: 处理 ${#input_files[@]} 个输入项"
        selected_files=$(validate_input_files "${input_files[@]}")
    else
        show_info "Finder模式: 获取选中文件"
        use_finder_mode=true
        selected_files=$(get_finder_selection)
        if [ -z "$selected_files" ]; then
            fatal_error "Finder中没有选中任何文件"
        fi
    fi
    
    local first_file
    first_file=$(echo "$selected_files" | head -1)
    
    local output_dir
    if [ "$use_finder_mode" = true ]; then
        output_dir=$(dirname "$first_file")
        validate_finder_directory "$output_dir" || exit 1
    else
        output_dir=$(determine_output_directory "$first_file" "$output_dir_specified")
    fi
    show_info "输出目录: $output_dir"
    
    if [ -z "$output_name" ]; then
        output_name=$(basename "$first_file")
        [ ${#input_files[@]} -gt 1 ] && output_name="archive_$(date +%Y%m%d)"
        [ -d "$first_file" ] && output_name=$(basename "$first_file")
    fi
    
    local output_file
    output_file=$(generate_unique_filename "$output_name" ".zip" "$output_dir")
    show_info "输出文件: $(basename "$output_file")"
    
    if compress_files "$selected_files" "$output_file" "$exclude_ds"; then
        [ "$use_finder_mode" = true ] && reveal_file_in_finder "$output_file"
        show_success "压缩完成"
    fi
}

main "$@" 