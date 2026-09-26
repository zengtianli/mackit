#!/bin/sh
# 复现 App 的一次引擎调用（与 EngineClient.swift 相同：stdin 送 JSON，stdout 回 JSON）。
# 用法：perf/engine-call.sh <mackit 引擎路径> [action]；默认 snapshot（App 启动时读取配置状态，只读）。
ENGINE="${1:-/Applications/Tianli MacKit.app/Contents/Resources/core/bin/mackit}"
printf '{"action":"%s"}' "${2:-snapshot}" | "$ENGINE" --home "$HOME" gui
