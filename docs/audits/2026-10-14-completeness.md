# MacKit macOS 完整度增量审计 · 2026-10-14

仅核 Apps PRD v1.0 的本轮四组要求。PRD SHA256：`254a5836124471dd2fd5f62073e8554fc75a7ab5d3408ed6c8fd4058bfa0ca8f`。安装与发行不属于本轮。

| 编号/适用性 | 实际问题与依据 | 最终行为/责任源 | 验证与状态 |
| --- | --- | --- | --- |
| S03/S10 适用 | 原配置 adapter 仅允许字段名，错 profile、组件类型/名称可传入；PRD 要求完整校验后应用 | `Lifecycle.makeConfiguration` 使用 bundled profiles 原声明逐字段校验；更新选项先 typed decode、范围与字段校验；错误无部分写入 | 已实现；隔离 import 回归待跑 |
| K04 适用 | 原 KeyRecorder 仅 onDisappear 停止；窗口失焦时 local monitor 仍存在 | `KeyRecordingSession` 只在本 App 当前可见 key window 和录制控件焦点生效，窗口失焦/关闭、App 失活、控件失焦均清理 | 已实现；私有隐藏窗口通知清理自检待跑；不合成输入 |
| U02/U03/U06 + GUI/CLI 适用 | 旧 shared 副本未有更新选项；支持目录不能隔离 updater 的 UserDefaults | vendor 同步总部四份源；窗口和 `update options` 共用更新器，自动行为默认关闭，已有选择保留；隔离 updater 要专用测试 bundle/domain | 已实现；真实 CLI 与设置明暗离屏待跑 |
| U07 适用 | 旧产品未接共享忙碌保护 | GUI 检查 busy/未保存文件/窗口草稿；真实 App 记录 PID + busy，CLI 同一记录拒绝安装且保留当前包；shared 原安装器不复制 | 已实现；隔离忙时拒绝、正常替换回归待跑 |

不适用范围：本轮不新增系统全局键、不更改登录项或运行服务，不处理其他平台和旧 SOP 欠项。冻结构建、真实输入/哈希、测试结果完成后写交接，不以已构建冒充已安装/发行。
