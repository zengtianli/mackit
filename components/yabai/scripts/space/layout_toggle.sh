#!/usr/bin/env bash
# Toggle 当前 space 的 yabai layout: bsp ↔ float
# 绑定：cmd+shift+ctrl - t (skhd)
# 影响：当前 space 全部 app 窗口（不只 focused app）

set -e

space_id=$(yabai -m query --spaces | jq -r '.[] | select(."has-focus"==true) | .index')
if [ -z "$space_id" ]; then
  echo "[space-layout-toggle] no focused space" >&2
  exit 0
fi

cur=$(yabai -m query --spaces --space "$space_id" | jq -r '.type')
if [ "$cur" = "bsp" ]; then
  target="float"
else
  target="bsp"
fi

yabai -m space "$space_id" --layout "$target"
echo "[space-layout-toggle] space $space_id: $cur → $target"
