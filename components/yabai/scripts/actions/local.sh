#!/bin/bash
# 运行本机自己的脚本 ~/.config/mackit/bin/<名字>；没有这个脚本就什么也不做。
# 公开配置里不放本机路径，个人动作（如 lid-sleep、brew-maintain、smart-push）都从这里进。

case "$1" in
    ''|*[!A-Za-z0-9_-]*) echo "用法: $0 <脚本名>" >&2; exit 1 ;;
esac
x="$HOME/.config/mackit/bin/$1"
[ -x "$x" ] && exec "$x"
exit 0
