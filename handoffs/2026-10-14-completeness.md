# MacKit · macOS 增量完整度 2026-10-14

开工：2026-10-14 20:44 +0800；截止：21:14。任务来源 Chapter，claims 身份 `70916 / chapter-task:1ae38327f41b43648acce7bb90d4f251`，由派出者释放。

固定输入：Apps PRD v1.0，SHA256 `254a5836124471dd2fd5f62073e8554fc75a7ab5d3408ed6c8fd4058bfa0ca8f`。只处理配置导入字段/类型、录制焦点清理、共享更新选项与 GUI/CLI、忙时安装保护。四份 shared 副本只通过 vendor 分发，总部原版只读。其他项目、真实配置、键表和后台保留。

责任路径：`macos/Sources/AppLifecycle*.swift`、`AppConfiguration.swift`、`Lifecycle.swift`、`WindowPage.swift`、必要 `UISelfTest.swift`、`mackit/cli.py` 帮助、`tests/test_lifecycle_cli.py`、双语 README、指定 audit/handoff。构建与验证输出在 `local/completeness-20261014/` 和原 `build/`。默认自动行为关闭，不安装/公证/发布/推送。

完成谓词：适用缺项关闭、必要隔离真实 CLI/离屏验证通过、原构建产物存在且绑定本轮源码与 shared 实际输入。当前阶段：已核 PRD，已同步 shared 原版，正在补产品 adapter 与隔离回归。装机仍为用户给定旧版，本轮不改变。
