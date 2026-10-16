# MacKit · Chapter 固定缺项收尾 2026-10-16

开工 2026-10-16 12:51 +0800。claims 沿 Chapter `856 / chapter-task:031c1290dcc74a2481c8c393ade34935`，不另开同范围声明，不释放派出者声明。

有限步骤：1) 修日志中失败的帮助契约测试并执行原测试入口；2) 只读核原发行、已装包和来源回执，确定新版本身份后沿原构建锁/入口、Mini 签名公证、原安装器和 GitHub Release；3) 只修 facts 卡片的共享渲染重复前缀，沿原站点生成器与 Chapter/Lintel ship 发布并回读；4) Chapter 整体只读重检收尾。先用约 10 分钟定位与预检；发行构建、签名、公证及网页发布按原入口阶段结果接续，不盲重试。

责任为本仓失败测试、必要版本/站点构建源码、原发行和构建/装机回执及本 handoff；现有 `components` 键表、用户 Profile/数据/偏好、登录项、服务和后台保留。共享 Chapter、Lintel、Portal、configs 与系统签名实现只读消费。九项已通过验收复用；性能 input-binding 由 Chapter 原调度择机采样，不在本轮重复测量。未获 App Store/Mac App Store 送审授权，不提交审核。

开工 tracked/staged 工作树干净，仅原 `perf/acceptance/`、`perf/delivery-evidence.json`、`perf/install-receipt-0.3.6.json` 未跟踪；不夹带原验收产物。当前唯一测试失败为 help 从“读命令”改为“查询命令”后，Karabiner 断言未跟进；修正断言不改产品行为、不放松错误码与数据保护测试。

完成谓词：登记测试通过；当前公开发行包绑定本轮实际源码、正式签名公证和 GitHub 读回；本机安装同包并回读原 build-receipt；网站卡片与共享实测数据一致、Lintel 检查发布回读通过。尚在执行，不预填完成。

## 第二轮 · product_basics 定向接续

2026-10-16 15:56 +0800 接续，仅关闭本轮固定的 product_basics 失败项；claims 为 `45829 / chapter-task:95d338c02fce45d3ad17a3fd5bb7d1f1`。责任块为原构建脚本的实际阻塞、同源构建/装机回执、必要隔离验收及本交接；共享模块只读。原 functionality/recovery/privacy 通过项复用，性能由原队列接续，不展开推广页和发行旧项。预计在本轮 30 分钟内完成；锁/环境连续 5 分钟无进展则留原件交还原队列。

原件回读：`perf/acceptance/product-basics-c533c74536ca42d0893747f121652187/` 的 34 项失败发生于安装/源码/receipt 身份守卫，未执行功能 fixture。已装为 0.3.6 (2026101401)，当前 VERSION 为 0.3.7，canonical receipt 仍为 0.3.6 (636)。上一轮原构建实际在 `scripts/build-app.sh` 的空 `SIGN_ARGS` 数组展开失败（macOS Bash 3.2、nounset），没有新 receipt，没有安装。旧进程已结束，现装保留。

本轮先将 PyInstaller 参数数组改为始终非空，保留可选签名参数和原入口；验证后经原 SDK FIFO/锁构建当前源、实际 assembled 回归、Mini Developer ID 签名与公证，再由原安装器保留配置安装，最后固定 product_basics 验收。仅在真实结果返回后填写完成，不以换旧 receipt 或放松身份校验获得通过。

### 第二轮实际结果 · 2026-10-16 16:03 +0800

源码修复已提交 `9a926debaabf89f43c29b5733ebec421a046d685`，仅原构建脚本和本轮交接；`/bin/bash -n` 通过，实际 macOS Bash 的 nounset 参数回归覆盖 ad-hoc 与带空格 Developer ID 身份，两者均通过，路径参数空格保留。脚本 SHA256 为 `4b7e72d1cb64fdc8174094302bdd25413b9c680e129fff53d2d68ca11df5d236`。业务源未改；上一轮 95 项逻辑/真实 CLI 测试通过证据继续保留，不重复无变化业务测试。

原 SDK FIFO 排队后拿到锁，随后原采样门拒绝：`负载 50.8 ≥ 12; foreign builds=[]; memory pressure=1`。本轮没有启动 swiftc/PyInstaller，没有新候选包/receipt，没有签名、公证或装机，也没有重新执行已知输入不匹配的固定验收。原 runner 以 75 退出、已释放自己持有的锁和票，没有遗留后台构建；不动其他人的锁或任务。准入原件 `local/chapter-completion-20261016/build-result-v2.json`，SHA256 `3b69039c9050c1be19ed92393eae2649545eb51fc100b4c0b575b63bb5e124eb`；对应 stderr 在 `build-runner-v2.log`。

16:02 的 `chapter basics --app mackit --json` 回读为 fresh、all_passed=false、status=failed，四项登记均 implemented、problems=[]；正式结果仍是原 34 项身份守卫失败，没有冒充四项功能已复验。只读回执 `local/chapter-completion-20261016/basics-readback-v2.json`（SHA256 `ab4efc4418ff7b93bff6aad339edf061dacfd4caeb670dca7157972a55000c6c`）。正式 delivery-evidence 及旧验收原件不手改、不提交。

装前/收尾摘要比对 `install-state-before.json` / `install-state-after.json`：204 项配置/偏好无变化，Profile `tianli`，selection/transactions 均相同，前后 running=[]；现装保留 0.3.6 (2026101401)，主程序 SHA256 `a4f7e78a371ba39614c36c9f1aa7af5c3a30ceb8e1e7f2693a45eceb7681f989`。之前的基线另存 `install-baseline-previous/`，没有覆盖丢弃。

本轮未达到 product_basics 完成谓词，剩余仅是本项的同源包构建/装机和正式验收，交回 Chapter 原环境队列自动接续；不追加旧网页、公开发行和性能欠项为本轮条件。原队列在负载满足并取得下一轮 claims 后，从仓库执行：

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/tianli/Dev/.venv/bin/python local/chapter-completion-20261016/release-build.py
```

此私有原 runner 沿原 SDK FIFO/锁、4 分钟准入等待、冻结共享副本，实际执行原 `build-app.sh`、3 项 AssembledBundleTests、Mini 原 `distribution_grade.py sign/check --stage signed`，成功才由 app_sop 生成 canonical build receipt。若再遇同一环境失败，不循环、不改闸，交回原调度。成功后按顺序复核 receipt/source/候选包，调用原 `distribution_grade.py notarize build/app/MacKit.app --timeout 5m --json`；公证超时只用原 submission-id 接续；重新保存装前基线后执行 `python3 scripts/install-app.py --source build/app/MacKit.app --receipt perf/build-receipt.json --output perf/install-receipt-0.3.7.json`，不得启动上屏 App。核安装哈希/签名/配置未变后运行 `chapter sop accept --app mackit --check product_basics --json` 和 `chapter basics --app mackit --json`，由固定引擎写正式原件；99 项真实检查及四项 fresh/passed 才能关单。无需发布 GitHub、网页、更新源或 App Store 审核。

## 第三轮 · 并行构建准入与实装验收

2026-10-16 18:15 +0800 接续，claims `7197 / chapter-task:8d046ba85692472385a59a2aaef4a125`。只续当前同源包构建、原安装器与 product_basics，完成后推送本仓本轮提交并回读远端；共享 devtools、Chapter 只读。当前 tracked/staged 干净，保留原三类未跟踪证据。`origin/main` 本地跟踪已包含 `9a926de`、`c6bc3a9`，推送前仍核真实远端，不改历史。

已读取 devtools 新版真实接口：`with sim_lane.BuildSlot(label, wait=240)` 使用共享并行构建槽，内存压力低于 4 可准入，等待安静窗口的测量仍优先；不再自包 `lock_chain/acquire(None)`、load/foreign_builds 或 pressure>1 门。私有原 runner 按此接入，原构建、候选回归、签名与 app_sop receipt 事务不变。完成标准仍为实际同源安装、运行/CLI/签名/配置回读、固定验收四项 passed，预计本轮 30 分钟内完成；不公然发行、不送审、不扩大源码公开范围。
