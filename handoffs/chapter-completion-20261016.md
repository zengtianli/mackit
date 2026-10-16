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
