#!/bin/bash
# 把剪贴板文字包成 Markdown 代码块粘贴出去，一秒后把原来的文字放回剪贴板。
# 顺序固定：读剪贴板 → 写入包好的文字 → 等手松开修饰键 → 发 ⌘V → 通知 → 还原。
# 由 skhd 调用（Karabiner 只改键，不跑程序）。

export LC_ALL=en_US.UTF-8
lock="${TMPDIR:-/tmp}/mackit-code-fence.lock"
# 上一次被强行结束会留下锁，超过一分钟的锁视为作废。
/usr/bin/find "$lock" -maxdepth 0 -mmin +1 -exec /bin/rmdir {} \; 2>/dev/null
# 按住不放或连按两下不能把文字包两层。
/bin/mkdir "$lock" 2>/dev/null || exit 0
trap '/bin/rmdir "$lock"' EXIT

notify() {
    /usr/bin/osascript -e 'on run argv' -e 'display notification (item 1 of argv) with title "剪贴板"' -e 'end run' -- "$1"
}

old=$(/usr/bin/pbpaste; printf x)
old=${old%x}
if [ -z "$old" ]; then
    notify "里面没有文字，没有粘贴"
    exit 0
fi
printf '```\n%s\n```' "$old" | /usr/bin/pbcopy

# skhd 触发时手还按着 ⇧⌘。这时发 ⌘V，系统收到的是 ⇧⌘V，又落回这条快捷键上，什么也贴不出来；
# 所以先等修饰键全部松开（最多 3 秒），再让 System Events 发 ⌘V。
if /usr/bin/osascript -l JavaScript >/dev/null 2>&1 <<'JXA'
ObjC.import("AppKit");
var held = 0x1E0000;  // shift | control | option | command
for (var waited = 0; ($.NSEvent.modifierFlags & held) && waited < 3; waited += 0.02) delay(0.02);
if ($.NSEvent.modifierFlags & held) throw new Error("修饰键一直按着");
Application("System Events").keystroke("v", {using: "command down"});
JXA
then
    notify "已粘贴为代码块"
    /bin/sleep 1
    printf %s "$old" | /usr/bin/pbcopy
else
    notify "已包成代码块，按 ⌘V 粘贴。要自动粘贴：系统设置›隐私与安全性里，辅助功能和自动化都允许 skhd"
fi
