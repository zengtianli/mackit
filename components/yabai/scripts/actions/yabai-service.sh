#!/bin/bash
# 启停 yabai 服务，结果用系统通知显示。只动 yabai：skhd 要一直在，快捷键才有人接。
# 由 skhd 调用（Karabiner 只改键，不跑程序）。

yabai=$(PATH=/opt/homebrew/bin:/usr/local/bin:$PATH command -v yabai) || exit 0
if /usr/bin/pgrep -qx yabai; then
    "$yabai" --stop-service
    m="yabai 已停止"
else
    "$yabai" --start-service
    m="yabai 已启动"
fi
/usr/bin/osascript -e "display notification \"$m\" with title \"窗口平铺\""
