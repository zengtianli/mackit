#!/bin/sh
# 复现 App 的一次引擎调用（与 EngineClient.swift 相同：stdin 送 JSON，stdout 回 JSON）。
# 用法：perf/engine-call.sh <mackit 引擎路径> [action]；默认 snapshot（App 启动时读取配置状态，只读）。
# 默认用已装的 MacKit.app；0.3.4 及更早装机名为 Tianli MacKit.app。
APP=/Applications/MacKit.app; [ -d "$APP" ] || APP="/Applications/Tianli MacKit.app"
ENGINE="${1:-$APP/Contents/Resources/core/bin/mackit}"
printf '{"action":"%s"}' "${2:-snapshot}" | "$ENGINE" --home "$HOME" gui
