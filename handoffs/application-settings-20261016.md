# 应用设置 · 2026-10-16

用户已批准在 MacKit 实现应用语言 GUI、搜索、Office 批量中文、设置状态与恢复，以及同源 CLI。当前会话 `01a1443b-10db-7c13-a046-65aba5e16296` 负责本轮。仅本机快装交付，不扩大到公开发行、网页部署或旧性能欠项。

原工程已有 Chapter 任务完成了 0.3.7 (2026101601) 的构建装机与固定验收，源码头 `4c47622`。其 daemon 暂时仍持有声明，因此开发先在临时隔离副本进行；合回原版前必须重新取得原版最小路径声明并核对差异。唯一长期原版仍为 `/Users/tianli/Apps/mackit`。

完成条件：真实安装应用可读；隔离 HOME 下通过语言写入、删除键跟随系统、批量完整预检/回滚、陈旧设置保护、恢复；生产 SwiftUI 页面离屏渲染与动作自检；冻结 CLI 包含新模块，签名本机快装后回读版本、同源输入及新命令。所有写测试只落隔离目录，不修改本人其他软件偏好。

本轮预算：三个有限阶段（共享引擎与命令、GUI 与隔离验收、构建装机与回读），约 45 分钟；锁等待保留事实，不覆盖他人声明。尚未完成，不预填通过证据。

## 隔离开发结果

新增共享 `application_settings.py`、`apps list/language set/office/restore` 命令、第六页「应用设置」（⌘6）、Office 批量入口、按软件自带语言生成的选择框与恢复。仅写 AppleLanguages，保留原多语言数组；写前整批验证、digest 防陈旧写入、失败回滚、准备中/恢复失败的记录可以接续恢复。读列表不创建状态。`--home` 以实际账号 HOME 判隔离，不被测试环境改写 HOME 误导；隔离应用/Info/Resources/偏好/状态路径均检查链接逃逸。

说明与语言名称保留在 `data/application-settings.json`，可由用户目录的同名配置按键覆盖，读取时更新，损坏回落内置值。

专项测试 10 项通过；首次完整回归 104 项，101 通过、3 项因未装配包跳过（后续须验证真实冻结包）。当前 Swift 源编译成功，生产 AppModel + 源码引擎在一次性 HOME 中完成 Office 批量修改、跟随系统、恢复原值等动作，42 项自检及 6 页离屏渲染通过。`never_visible_or_key=true`，没有界面激活或合成输入。图与原件在临时副本 `local/application-settings-20261016/`；应用设置页已目视检查，侧栏选中行的离屏黑块是原工程已记录的合成限制，不据此宣称实屏选择样式已测。

生产只读列表已识别 Mini 上三个 Office 的自带中文与本会话先前已保存的 `zh-Hans-CN`。标准化为 `zh-Hans` 展示，保存相同语言为 no-op，保留原数组；目前未通过本轮代码修改本人实际 Office 偏好。

首个本机包 0.3.7 (2026101602) 已由原 BuildSlot 与 app_sop.build_receipt 实际生成，source commit `f37b1bb`、dirty=false；Developer ID 签名通过，冻结命令可只读识别本机三个 Office。真实冻结 UI 的 42 项/6 页通过，MacKit 本人偏好导出前后逐字节一致。包的三项 AssembledBundleTests 通过。随后完整测试曾错误把签过名的 bundle 内二进制当作 `MACKIT_NATIVE` 裸程序夹具使用，复制进不同测试 bundle 后被系统以信号 9 结束，导致 LifecycleCommandTests 失败；这与原交接已记录的签名复制限制相符。正确入口是 `MACKIT_NATIVE=build/native/MacKit`（原构建保留的裸程序）加 `MACKIT_APP=<真实装配包>`，不得放松检查。

按既有 GUI/CLI 同源要求，补上应用设置页对恢复目录的事件监听；命令保存或恢复后，已开的页面自动重读，无轮询，不将通知里的旧值写回。对应生产离屏自检会实际从外部引擎调用改变/恢复语言并等待页面跟随。此项改变了 Swift 输入，须用后续新包重新验收，不沿用首包结论冒充。

## 原版合入与本机交付

已核原模型 PID 7197 退出、原 transcript 最终 chapter_end=0、Chapter 对任务 `8d046ba85692472385a59a2aaef4a125` 的 outcome=done，且只在 session_boundary 等待。经原 handoff_guard RPC 精确清理这一条已完成任务遗留的 `Apps/mackit` 租约；未结束 daemon、未取消其他队列任务。证据 `local/application-settings-20261016/completed-lease-cleanup.json`。随后本会话取得原版的明确文件/输出目录声明，以 fast-forward 合入 `f37b1bb`、`8803988`，原来的四类未跟踪 perf 证据保持原位。

隔离副本缺少 10 张被忽略的生成 iconset 图片，声明输入为 178 项，原版为 188 项；共用文件逐项相同。为保证 canonical receipt 与原工程完全对应，原版再次通过现有 BuildSlot + build-app.sh --local + app_sop.build_receipt 实际构建，没有修改旧包的来源记录。原版实际输入 source SHA256 `7ea5e3a855da8518645b1966b40b8af698aa1a16e8c58d7da6e5ece5a1d1d97d`，源码提交 `8803988d8cd32050832c3a236403f294c40fcbd6`，dirty=false、188 项输入。

最终本机包 0.3.7 (2026101602)，主程序 SHA256 `800969744a5c372e6a2db3ae00cf720a4b6139dc5c75af83a3cd5ea5b35936b9`。Developer ID 签名与严格验证通过。经原 `scripts/install-app.py --local` 安装至 `/Applications/MacKit.app`，旧版保留在 `build/installed-backup/20261016-185819/MacKit.app`。实际构建回执 `build/accept/application-languages.json`，安装成功与源码/实物核对后，将同一份真实回执原样保存在 `perf/build-receipt.json`；旧 canonical 的备份为本轮 local 目录里的 `previous-build-receipt.json`。

验证结果：

- 正确裸程序 + 装配包的完整回归：105 项全部通过、零跳过，原件 `local/application-settings-20261016/verified-tests.log`。
- 最终安装版实际离屏自检：44 项全部通过、6 页截图，包括应用查找、Office 批量修改、跟随系统、恢复及外部命令保存/恢复后页面自动跟随。`never_visible_or_key=true`；未启动普通窗口、未产生输入事件。原件 `installed-ui-summary.json`、`frozen-ui/stdout.json` 与 `frozen-ui/native-ui-applications.png`。
- 最终安装版另外执行原三项 AssembledBundleTests，3 项全部通过（48.049 秒）；原件 `installed-package-tests.log`。使用实际 `/Applications/MacKit.app` 的命令及隔离包/偏好域，不替换本人正在使用的设置。
- 最终安装版冻结命令已读回版本 2026101602、三个真实 Office 的简体中文设置；所有写入/批量/no-op/跟随系统/多级恢复动作只在一次性 HOME 中实测。安装与测试前后，66 项 MacKit 配置文件/链接、MacKit 偏好及三个 Office 的完整偏好导出摘要一致。原件 `installed-verification.json`、`state-before.json`、`state-after.json`。
- 本轮未改终端配置、按键、服务、登录项、系统语言或实际 Office 偏好。软件语言只作用于应用自带的界面翻译；仍需对应应用重新打开才加载。iCloud 与其他产品旧缺项不在本轮追加范围。

源码同步沿 2026-10-08 已有本人授权（Chapter 现场回读 granted=true、scope 含 push、revoked_at=null），仅向现有自有仓正常推送本轮代码与交接；不新设公开仓、不 force、不发布新 Release/更新包、不部署网页、不送审。远端最终 SHA 与收尾状态以本轮 local 回执为准。
