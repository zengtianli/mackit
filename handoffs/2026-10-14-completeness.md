# MacKit · macOS 增量完整度 2026-10-14

开工：2026-10-14 20:44 +0800；截止：21:14。任务来源 Chapter，claims 身份 `70916 / chapter-task:1ae38327f41b43648acce7bb90d4f251`，由派出者释放。

固定输入：Apps PRD v1.0，SHA256 `254a5836124471dd2fd5f62073e8554fc75a7ab5d3408ed6c8fd4058bfa0ca8f`。只处理配置导入字段/类型、录制焦点清理、共享更新选项与 GUI/CLI、忙时安装保护。四份 shared 副本只通过 vendor 分发，总部原版只读。其他项目、真实配置、键表和后台保留。

责任路径：`macos/Sources/AppLifecycle*.swift`、`AppConfiguration.swift`、`Lifecycle.swift`、`WindowPage.swift`、`AppModel.swift` 的忙碌/偏好保存状态、必要 `UISelfTest.swift`、`mackit/cli.py` 帮助、`tests/test_lifecycle_cli.py`、`project.yaml` 的两条 update options GUI/CLI 映射、双语 README、指定 audit/handoff。构建与验证输出在 `local/completeness-20261014/` 和原 `build/`。默认自动行为关闭，不安装/公证/发布/推送。

完成谓词：适用缺项关闭、必要隔离真实 CLI/离屏验证通过、原构建产物存在且绑定本轮源码与 shared 实际输入。**已全部满足；仅本地源码/构建完成，未安装或发行。**

## 已交结果

- 代码提交：`4c990b2320727c50866d4b66cac9063cd0384aa3`；后续收尾提交仅更新本 audit/handoff，不改变冻结代码。
- 构建：`/Users/tianli/Apps/mackit/build/local/app/MacKit.app`，0.3.6 (2026101401)。当前 `/Applications/MacKit.app` 仍为 0.3.6 (2026100901)，版本/主程序未改变。
- 回执：`/Users/tianli/Apps/mackit/build/accept/completeness-20261014.json`。由原 `app_sop.py build-receipt` 围绕真实原构建与签名写出，source dirty=false；原 `verify_build_receipt` 回读通过。
- source SHA256：`cbc30370898d438f8f52fff549cab5eabdc449e76f874f109071c8003aad4f66`。
- 主程序 SHA256：`a4f7e78a371ba39614c36c9f1aa7af5c3a30ceb8e1e7f2693a45eceb7681f989`。
- 原构建命令：`APP_LIFECYCLE_VENDOR=/nonexistent MACKIT_BUILD_NUMBER=2026101401 bash scripts/build-app.sh --local`；先 vendor 分发并 check，构建时不再拉取改变冻结输入。四份 shared 实际字节与总部匹配，收尾再次 check 通过。
- 快签：沿原 `login_run.py` 在 Air 登录会话签名；唯一 job `mackit-complete20261014`，输入/返回 ZIP 均校验 SHA，所有 Mach-O 与 App 带 Developer ID、runtime、时间戳，`codesign --verify --deep --strict` 与 signed grade 通过。证据 `local/completeness-20261014/grade.json`、`sign-input.zip`、`signed.zip`、`signed.sha256`、`sign-login.sh`；未提交公证、未安装到 Air。

## 验证与真实边界

20 项 `test_agent_cli.py` 逻辑回归、15 项 `test_lifecycle_cli.py` 真实隔离回归均通过；后者包括十二种非法导入、完整往返、更新选项默认关闭/确认/dry-run、窗口跟随、忙时安装拒绝、一次性假 App 的正常替换，以及冻结引擎在自身被替换后仍能返回 JSON。所有更新选项写入使用一次性 bundle/domain，不能仅设置支持目录。

冻结包的重标识私有副本通过 52 项原离屏自检，产出 9 张图，配置/更新明暗实际已看。快捷键录制用私有隐藏 NSWindow 的生命周期通知验证清理，不合成或发送输入；实际窗口从未显示、不抢焦点、不进 Dock。更新测试只读取隔离本地发行记录，不联网下载包；设置图显示的是隔离测试源。

`local/completeness-20261014/result.json` 收束证据，`lifecycle-final.log` / `agent-cli-tests.log` / `ui-result.json` 留原件。生产偏好、真实配置、components 与原安装包共 177 个文件/链接构建前后完全一致，见 `owner-before.json` / `owner-after.json`。未碰键表、Hammerspoon、Karabiner、skhd、登录项或他人验收产物。

本轮早期失败的真原因：相同 bundle ID 不能作为 `UserDefaults(suiteName:)`，已改自身域使用 hostDefaults；升级副本要绑定其自己的测试域；原生测试夹具必须带 profiles，不能依赖编译时相对源码路径。最终修复均由真实二进制复测通过，没有跳过失败。

## 单独 install 任务的接续

已有冻结包和来源回执，可供原安装器使用；本会话没有运行下列安装命令。接手者先回读包/回执哈希与 claims，再按该独立任务授权执行：

```sh
cd /Users/tianli/Apps/mackit && /Users/tianli/Dev/.venv/bin/python scripts/install-app.py --local --source build/local/app/MacKit.app --receipt build/accept/completeness-20261014.json --output local/completeness-20261014/install-receipt.json
```

本轮没有剩余必要失败；装机、运行回读、公开发行/私有更新与性能重新测量均未执行，不冒充完成。外部共享原版和其他产品只读。保留原三个未跟踪 perf 产物。Chapter claims 未释放，由派出者收尾。

## 独立装机任务 · 2026-10-14 21:14 +0800 开工

Chapter 本轮身份 `7320 / chapter-task:95fba6abdc6f446692ea20909b44910d`；安装已明确授权，claims 使用派出者身份检查，不另开、不释放。责任仅为原安装器的 `/Applications/MacKit.app` 替换、原 `build/` 暂存/旧版备份、私有安装证据及同一 audit/handoff；未修改源码或原冻结包。装前 Git 无 tracked/staged 差异，原三个未跟踪 perf 产物保留，固定图标验收仅由 Chapter 写它自己的证据。

装前再次调用原 `verify_build_receipt` 核当前源码/图标/主程序，source SHA256 与上文冻结输入一致，Developer ID 深度严格签名通过；20 项逻辑、15 项真实隔离 CLI、52 项离屏检查的前轮真实通过结果未失配。Mini 当时没有 MacKit 运行进程，旧版为 0.3.6 (2026100901)。本轮没有重编、重签、公证、发布、推送、更新渠道或安装到其他设备。

已执行上文原 `scripts/install-app.py --local` 命令一次，输出 `local/completeness-20261014/install-receipt.json`；安装器的 `launched:false` 表示该脚本本身不启动，之后本轮另用 `/usr/bin/open -g -j /Applications/MacKit.app` 隐藏启动正常 App 路径（没有测试替身/演示 HOME）。实际运行 PID `11540`，可执行路径 `/Applications/MacKit.app/Contents/MacOS/MacKit`；系统 API 读回 hidden=true、active=false、屏上窗口数 0。原先无实例，故本次为安装后后台启动，没有终止其他后台。

装后 App 与实际冻结 CLI `status --json` 均读回 0.3.6 (2026101401)，bundle ID 保持 `cyou.tianli.mackit`；143 个包内文件/链接逐项与候选包字节一致，主程序 SHA256 仍为上文值。已装包原 build-receipt 再验证通过；Developer ID、Team `B9LJH93LA4`、runtime、21:04:55 签名时间戳以及 deep/strict 验证通过。`~/.local/bin/mackit` 原链接未变。

装前/装后 179 项配置、键表、相关服务 plist、命令链接与生产偏好摘要最终完全一致；当前 Profile `tianli`、14 个组件选择、配置源与事务集合保持一致，更新自动检查/下载/安装均读回 false。隐藏启动曾新增系统的 `NSWindow Frame main` 与 `NSSplitView Subview Frames main, SidebarNavigationSplitView`；用装前 SHA256 证明原域为空后，仅删除这两项新布局记录，完整偏好摘要恢复一致，没有改用户选择。证据 `install-owner-before.json` / `install-owner-after.json`、`install-window-metadata.json`、`install-status-before.json` / `install-status-after.json`、`install-readback.json`、`install-runtime.json`、`install-signature.log`、`install-update-options.json`，均在私有 `local/completeness-20261014/`。

原旧版保存在 `build/installed-backup/20261014-211812/MacKit.app`，0.3.6 (2026100901)，其签名验证仍通过，可回溯。固定命令 `app_sop.py accept --app mackit --check installed_icon --json` 返回 passed，原证据 `perf/acceptance/run-64gzrspk/installed_icon.json`；macOS 27.2.0 系统图标离屏读回，无手写验收通过。

本次安装完成谓词已满足，无剩余必要失败；只本机 Developer ID 快装，尚未公证或公开发行。原源码整改轮的“未安装”记录描述其历史范围，以本节实际装机回读为当前状态。
