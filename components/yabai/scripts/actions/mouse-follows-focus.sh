#!/bin/bash
# 鼠标跟焦开关（yabai 的 mouse_follows_focus），结果用系统通知显示。
# 由 skhd 调用（Karabiner 只改键，不跑程序）。

yabai=$(PATH=/opt/homebrew/bin:/usr/local/bin:$PATH command -v yabai) || exit 0
if [ "$("$yabai" -m config mouse_follows_focus)" = on ]; then
    "$yabai" -m config mouse_follows_focus off
    m="鼠标跟焦 已关"
else
    "$yabai" -m config mouse_follows_focus on
    m="鼠标跟焦 已开"
fi
/usr/bin/osascript -e "display notification \"$m\" with title \"窗口平铺\""
