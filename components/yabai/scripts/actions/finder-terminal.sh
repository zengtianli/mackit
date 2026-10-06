#!/bin/bash
# Finder 在前台时，在当前目录打开 Ghostty：选中文件夹用它，选中文件用它所在的目录，都没选用当前窗口的目录。
# 其他 App 在前台时什么也不做。由 skhd 调用（Karabiner 只改键，不跑程序）。

case "$(/usr/bin/lsappinfo info -only bundleid "$(/usr/bin/lsappinfo front)")" in
    *'"com.apple.finder"'*) ;;
    *) exit 0 ;;
esac

dir=$(/usr/bin/osascript <<'APPLESCRIPT'
tell application "Finder"
    if (count of (selection as list)) > 0 then
        set f to item 1 of (selection as list)
        if class of f is folder then
            POSIX path of (f as alias)
        else
            POSIX path of (container of f as alias)
        end if
    else
        POSIX path of (insertion location as alias)
    end if
end tell
APPLESCRIPT
) || exit 1

/usr/bin/open -a Ghostty "$dir" || exit 1
/usr/bin/osascript -e 'on run argv' -e 'display notification ("已打开 " & item 1 of argv) with title "终端"' -e 'end run' -- "$(/usr/bin/basename "$dir")"
