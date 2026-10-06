#!/bin/bash
# Music 控制：toggle 播放/暂停，next 下一首。Music 没开时两者都是启动并播放。结果用系统通知显示。
# 由 skhd 调用（Karabiner 只改键，不跑程序）。

case "$1" in
    toggle) running='tell application "Music"
        if player state is playing then
            pause
            set m to "暂停"
        else
            play
            set m to "播放"
        end if
    end tell' ;;
    next) running='tell application "Music" to next track
    set m to "下一首"' ;;
    *) echo "用法: $0 <toggle|next>" >&2; exit 1 ;;
esac

/usr/bin/osascript <<APPLESCRIPT
if application "Music" is running then
    $running
else
    tell application "Music"
        launch
        delay 1.5
        try
            play playlist "Favourite Songs"
        on error
            play
        end try
    end tell
    set m to "启动并播放"
end if
display notification m with title "Music"
APPLESCRIPT
