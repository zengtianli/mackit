# 固定产品验收

从仓库根执行以下命令，Chapter 会运行 `project.yaml` 中的 `sop.accept`，并合并写入 `perf/delivery-evidence.json`。不要手工补通过记录。

```sh
~/Dev/.venv/bin/python ~/Apps/chapter/engine/app_sop.py accept --app mackit --check functionality --check recovery --check privacy --check native_ui --json
~/Dev/.venv/bin/python -m unittest discover -s tests -v
~/Dev/.venv/bin/python ~/Apps/chapter/engine/app_sop.py run --app mackit --check-only --json
```

| 固定项 | 实际覆盖 | 边界 |
| --- | --- | --- |
| functionality | CLI 预览、安装、状态、幂等、诊断与键表；GUI JSON 预览、编辑、备份及恢复 | 临时 HOME，不安装依赖、不触发实际热键 |
| recovery | 真实文件与目录往返、用户新修改保护、未完成事务、文件操作失败自动回滚与重试 | 中断由持久事务状态模拟，不是物理断电 |
| privacy | 合成私密内容隔离、编辑白名单、路径及软链越界、演示模式软件与服务保护 | 本地流程验证，不是网络抓包；惰性探针替代真实软件安装和服务命令 |
| native_ui | 当前 Swift 源码 + 真实 Python 引擎，五页真实视图离屏渲染，刷新、过滤、草稿、关闭及退出 | 独立测试包，不覆盖装机版；不显示窗口、抢焦点或合成输入 |

脚本共用 `_common.py`，只在临时 HOME 操作；原生候选构建到 `build/accept-native-ui/`。自检截图和日志由脚本写入 `perf/acceptance/`，判定及输入绑定由 Chapter 写入。

装机后可让同一固定脚本使用实际 App 与冻结引擎，并校验版本、bundle ID 和构建回执 SHA256：

```sh
MACKIT_ACCEPT_APP="/Applications/MacKit.app" ~/Dev/.venv/bin/python ~/Apps/chapter/engine/app_sop.py accept --app mackit --check native_ui --json
```

装机图标 `installed_icon` 由 Chapter 内置的固定脚本判定，不需要人工确认：它离屏读取 macOS 实际给已装 App 显示的图标（IconServices，与 Finder、Dock 同源），与 `icon/AppIcon.icns` 逐像素比对；失败时按脚本给出的诊断修图标或重新装机，不手写通过记录。

```sh
~/Dev/.venv/bin/python ~/Apps/chapter/engine/app_sop.py accept --app mackit --check installed_icon --json
```

自检候选不代表新代码已经装机或发布。
