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

已读取 devtools 新版真实接口：`with sim_lane.BuildSlot(label, wait=240)` 使用共享并行构建槽，内存压力低于 4 可准入，等待安静窗口的测量仍优先；不再自包 `lock_chain/acquire(None)`、load/foreign_builds 或 pressure>1 门。私有原 runner 按此接入，原构建、候选回归、签名与 app_sop receipt 事务不变。完成标准仍为实际同源安装、运行/CLI/签名/配置回读、固定验收四项 passed，预计本轮 30 分钟内完成；不公开发行、不送审、不扩大源码公开范围。

### 第三轮完成回读 · 2026-10-16 18:30 +0800

本轮 product_basics 已关闭。共享 BuildSlot 在测量任务结束后准入 slot-1，实际编译成功；旧 Bash 空数组错误未再出现。当前包 0.3.7 (2026101601)，bundle ID `cyou.tianli.mackit`，主程序 SHA256 `86611ba16e2e2104ebfe3765b96d2a8a8e75d235a8f7eb38808137177e9dc001`，图标 SHA256 `b9fc6599fa7699befc9d53bf281afd66d5f44966a3eb05afb97e70f5b1f8d840`。原 app_sop 实际构建事务写 `perf/build-receipt.json`（SHA256 `6e73b2b1ef3e0f2618d14d01b75fd733c66fdfb037279e9a687e929b45903717`），绑定干净源码提交 `e32e5c6f5abef336e3a51cd77d5523ef85b00e37`、185 个输入文件、source SHA256 `e5d5064b25345b27358d9cdf931f7a3e9e9b40626487d97f55104185d7dec833`。打包候选的 3 项 AssembledBundleTests 通过；随后登记命令 95 项测试全部通过、零跳过、input_stable=true，日志 `~/Library/Logs/app-sop/mackit-test-20261016-182042.log`，登记结果为 18:23 当前代码通过。未在构建/测试期间修改编译输入。

Mini 原 `distribution_grade.py sign/check` 为 Developer ID Application: tianli Zeng (B9LJH93LA4)，主程序、冻结 CLI 与 libpython 均有 runtime/timestamp；公证 UUID `650f49c6-9d4e-47e6-a85d-51fd6ae54c8b` 返回 Accepted，已装订，spctl=Notarized Developer ID。公证后主程序及全部 185 个源输入哈希再次匹配。原件为 `local/chapter-completion-20261016/{build-result-v3.json,sign.json,signed-grade.json,notarized-v3.json,current-tests-v3.json}`。

原 `scripts/install-app.py --source build/app/MacKit.app --receipt perf/build-receipt.json --output perf/install-receipt-0.3.7.json` 已安装同一份包，旧版完整保留在 `build/installed-backup/20261016-182431/MacKit.app`。实际已装程序离屏运行探针 PID 34680，路径 `/Applications/MacKit.app/Contents/MacOS/MacKit`，App 0.3.7 (2026101601)、冻结 CLI 0.3.7、主程序与候选/receipt 哈希一致，安装后签名/公证检查通过。探针使用现有 `--lifecycle-follow-probe`、私有 --home/支持目录/cloud fixture/一次性 UserDefaults 域，policy_prohibited=true、active=false、windows_on_screen=0，读回后终止自有探针并清理测试偏好域，恢复原来无 GUI 进程状态，没有上屏或合成输入。运行回读 `local/chapter-completion-20261016/round3/running-readback.json`，SHA256 `28815a75c422799b89179f720047a52728fcd1e94e422e5ec0b8900c071b378c`。装前/后 204 项配置/偏好摘要完全一致，Profile `tianli`、selection、transactions 不变，键位、服务、登录项与权限不改。

唯一固定命令 `chapter sop accept --app mackit --check product_basics --json` 返回 ok=true/status=passed，正式记录 `perf/acceptance/run-6yatk3kd/product_basics.json`；四项原件位于 `perf/acceptance/product-basics-52008c5f8dc7419cab81f34f10e8568d/`，settings 29、shortcuts 20、icloud 29、updates 21，共 99 项严格布尔全部 true（含14项政策场景），原件 SHA 与 detail 引用逐一相符。复用了真实冻结 CLI、52 项进程内 UI 自检/9 张离屏截图和运行窗口跟随回归；174 项生产摘要验收前后相同。iCloud 仍只声明本机隔离文件传输、冲突/损坏/不可用恢复，不声称验证苹果跨设备传输。Chapter 自己写入 `perf/delivery-evidence.json`，未手写或放松证据。

安装影响的固定 `installed_icon` 也已通过，原件 `perf/acceptance/run-90w714_d/installed_icon.json`。最终 `chapter basics --app mackit --json` 回读 fresh、all_passed=true、四项 passed、problems=[]，保存在 `local/chapter-completion-20261016/basics-final-v3.json`。完成后仅本轮 receipt 和交接进入提交；原验收目录、旧未跟踪证据及本轮安装/验收原件保留本机，不夹带发布。

推送准入：实际远端 main 在推前为 `c6bc3a98df5ac0f89eeb6f5747d59ac71ca33532`，已包含 `9a926de`、`c6bc3a9`，不重造旧提交。GitHub Actions workflows=0，仓内无 `.github/workflows`、`ci_scripts`、Xcode Cloud 工作流，GitHub Pages 查询 404；本项目站点部署需显式原 Lintel gate/deploy 入口，本次不执行。原 pre-push 只有 Git LFS 链，提交保留原 hooks，以 `GIT_FOLLOW_LOCAL_ONLY=1` 关闭本次双机跟随。将核对 `git log --stat @{u}..HEAD` 后普通推送本仓完成提交；不会触发 App Store 送审、GitHub Release、App 更新源或 Lintel 网页发布，不 force。远端最终 HEAD 以本轮 push/ls-remote 回执为准。

18:32 推送完成：交付提交 `4634d7367cd2b5bfb59c3292fdfbc1489ab6dcf2` 和准入说明 `e32e5c6` 已普通推到 `origin/main`；SSH `git ls-remote` 与 GitHub refs API 回读均为该完整 SHA，`9a926de`、`c6bc3a9` 均为其祖先。回执 `local/chapter-completion-20261016/{push-review-v3.txt,push-v3.log,remote-head-v3.txt,github-head-v3.txt}`。随后仅追加本条真实回读并推送交接；最终远端头核验保存为同目录 `final-remote-v3.json`，不改编译源或已验包，不重跑无变化验收。本轮目标已完成，无待用户决定或本产品阻塞；此前旧轮推广页/公开发版与调度性能项仍沿各自原队列，不冒充本轮完成。
