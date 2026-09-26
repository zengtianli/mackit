#!/bin/sh
# 只在系统安静（1 分钟负载 < 阈值）时跑 hyperfine，避免把别的进程的占用算进来；记录采样时负载。
# 用法：perf/quiet-bench.sh <输出json> <命令...>
OUT="$1"; shift; LIMIT="${QUIET_LOAD:-8}"
for _ in $(seq 120); do
  LOAD=$(sysctl -n vm.loadavg | awk '{print $2}')
  if awk "BEGIN{exit !($LOAD < $LIMIT)}"; then
    echo "load1=$LOAD"; hyperfine -N --warmup 3 --runs 30 --export-json "$OUT" "$*" | grep -E "Time|Range"
    echo "load1_after=$(sysctl -n vm.loadavg | awk '{print $2}')"; exit 0
  fi
  sleep 5
done
echo "系统 10 分钟内未安静下来，未测"; exit 1
