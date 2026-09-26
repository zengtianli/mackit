#!/usr/bin/env python3
"""被动测 GUI 启动：open -g -j 后台启动（不抢焦点），轮询进程表，
记录 App 进程出现、首个引擎子进程（读取配置状态）出现与退出的时刻。不合成任何输入。"""
import subprocess, sys, time
app = sys.argv[1] if len(sys.argv) > 1 else "/Applications/Tianli MacKit.app"
exe = app + "/Contents/MacOS/MacKit"; eng = app + "/Contents/Resources/core/bin/mackit"
def pids(pat):
    return subprocess.run(["pgrep", "-f", pat], capture_output=True, text=True).stdout.split()
t0 = time.perf_counter(); subprocess.run(["open", "-g", "-j", app], check=True)
marks = {}
while time.perf_counter() - t0 < 20:
    t = (time.perf_counter() - t0) * 1000
    if "app" not in marks and pids(exe): marks["app"] = t
    e = pids(eng)
    if e and "engine_start" not in marks: marks["engine_start"] = t
    if "engine_start" in marks and not e: marks["engine_done"] = t; break
    time.sleep(0.005)
print({k: round(v) for k, v in marks.items()})
