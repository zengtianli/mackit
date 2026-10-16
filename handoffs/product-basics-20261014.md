# MacKit 基本产品功能登记与验收 · 2026-10-14

本轮仅处理设置界面、快捷键、iCloud、检查更新的 Chapter 底座接入。claims 沿派出者 `71924 / chapter-task:accd36a86c61426fae80cfb8c35830f1`，不另开、不释放。写入为本 handoff、`project.yaml` 的 product_basics 登记、`scripts/accept/product_basics.py` 与原验收输出；共享 Chapter/生命周期源码只读。

输入为当前已装 MacKit 0.3.6 (2026101401)，原冻结回执 `build/accept/completeness-20261014.json`；实际回读后确定，不把历史交接当现状。复用已装二进制的重标识私有副本、真实冻结 CLI、原进程内离屏自检与隔离跟随回归，不编译、不安装、不发布、不推送、不动真实偏好或 iCloud。

完成条件：四项均有绑定当前已装包/源码/政策的 JSON 原件和严格布尔 checks；经 `chapter sop accept --app mackit --check product_basics --json` 核验。隔离文件同步与苹果跨设备服务传输分开陈述；发现编译能力缺失时仅登记原因与下一步。

开工 Git 无 tracked 或 staged 差异；保留已有 `perf/acceptance/`、`perf/delivery-evidence.json`、`perf/install-receipt-0.3.6.json` 未跟踪内容与生产后台。最终已完成本轮登记和实际验收；原件留在产品本机证据目录，不夹带进源码提交。

## 最终回读 · 2026-10-14 22:38 +0800

- 原命令 `chapter sop accept --app mackit --check product_basics --json` 返回 `ok:true / status:passed`；正式记录 `perf/acceptance/run-gf7nzqpn/product_basics.json`。随后 `chapter basics --app mackit --json` 返回 fresh、all_passed=true、problems=[]，四项均 implemented/passed，非登记 presence 通过。
- `project.yaml` 新增四项真实 entry/readback、验收输入和唯一固定脚本命令。现有功能源码不改；`inputs` 覆盖本脚本、被复用的真实 assembled lifecycle 回归及冻结来源回执。
- 已装输入为 0.3.6 (2026101401)，bundle ID `cyou.tianli.mackit`，主程序 SHA256 `a4f7e78a371ba39614c36c9f1aa7af5c3a30ceb8e1e7f2693a45eceb7681f989`，source SHA256 `cbc30370898d438f8f52fff549cab5eabdc449e76f874f109071c8003aad4f66`，源提交 `4c990b2320727c50866d4b66cac9063cd0384aa3`。回执全 source.files 与当前源逐项匹配，已装包 codesign deep/strict 通过；原件另绑定政策 spec_digest、回执/本脚本/回归脚本 SHA256。
- 最终 99 个严格布尔 checks：85 个实测细项、14 个固定政策场景汇总。设置 29、快捷键 20、iCloud 29、更新 21，全部 true；汇总在原件 `scenario_assertions` 中列出实际依赖的细项，不能独立填常量通过。

四项原件位于 `perf/acceptance/product-basics-4cad60063858430b9d26334ad12a8730/{settings,shortcuts,icloud,updates}.json`。各原件含独立 checks、实际 CLI argv/退出码/JSON 响应、安装/源码身份与上游日志 SHA；`product_basics.detail.json` 引用原件相对路径和完整 SHA256，Chapter 严格核验后写入 `perf/delivery-evidence.json`，未手改交付证据。

| 项目 | 本轮实际路径 | 结果与范围 |
| --- | --- | --- |
| 设置 | 已装二进制私有副本的真实原生设置窗、CLI select/export/import、运行窗口跟随 | 52 项原离屏自检、9 张截图；实际配置/更新明暗界面；保存后新进程读回，坏 profile 导入不改变原配置，正确导入被 App 适配层读取，窗口关闭/草稿放弃路径通过 |
| 快捷键 | 真实快捷键搜索/冲突提示/录制焦点清理；冻结 CLI window hotkey add/remove | 私有 --home 持久化动作、重复拒绝、关闭/恢复、新进程读回，实际 skhd 动作命令生成；没有向真实桌面派发输入，也不声称物理送键通过 |
| iCloud | 共享 AppConfiguration 的文件传输、真实开关与 App/CLI 跟随 | 写入/接收远端变化、同字段冲突本地优先与独立字段合并、坏云 JSON 拒绝/恢复、不可用保留本地、关闭保留双方数据通过；全部使用注入的本机 cloud fixture，没有访问本人 iCloud，也没有验证苹果服务器/跨设备传输 |
| 更新 | 真实原生版本/按钮目标、冻结 CLI update check/options/install --dry-run | 本地发行源最新/获取入口、缺失/坏发行记录/恢复、选项默认关闭与持久化、坏间隔拒绝、忙碌/未保存保护和数据保留通过；更新资产只作带真实 digest/size 的本地测试记录，不下载、不安装 |

`ui.json`、`ui.log`、`ui/` 和 `assembled-follow.log` 保留上游原件。私有副本只改一次性 bundle ID、LSUIElement 与 ad-hoc 签名，未编译或替换已装包；自身程序为原安装版代码。真实 NSApplication/设置窗采用 prohibited activation，首尾断言 active=false、屏上窗口数 0，不合成键盘事件、不打开真实菜单。171 项生产配置、components 键表、相关真实配置、生产偏好与已装主程序摘要验收前后完全一致，见 `owner-before.json` / `owner-after.json`；一次性偏好域由测试清理，原生产进程和服务不重启。

前两次正式失败原件已保留：`run-42ne6zxn` 中验收脚本错误使用参考产品的 `sync now`，MacKit 实际只提供 on/off，已改为真实开关触发同步；`run-hn1llvg2` 中 85 个细项均通过但缺 Chapter 的固定场景键，已用细项布尔汇总补齐，再实际重跑通过。未放松 Chapter 校验器、未把命令 presence 当功能验收，也未修改共享代码。

完成谓词已满足。当前没有发现需要修改编译源码的实际能力缺陷；苹果跨设备传输不属于本轮隔离验收结论。本轮只本地提交 `project.yaml`、`scripts/accept/product_basics.py` 与本 handoff，不构建、安装、公证、发布或推送，不处理其他旧 SOP。复验入口：`cd /Users/tianli/Apps/mackit && chapter sop accept --app mackit --check product_basics --json`。Chapter claim 保留给派出者释放。

## 2026-10-16 第二轮接续（当前尚未通过）

Oct14 的通过结论只属于上文原包/原输入。当前 VERSION 为 0.3.7，而现装仍为 0.3.6 (2026101401)，canonical `perf/build-receipt.json` 仍为 0.3.6 (636)；新失败原件 `perf/acceptance/product-basics-c533c74536ca42d0893747f121652187/` 在 installed/source/receipt 身份守卫退出，未执行四项 fixture，不能据此声称四项功能实际失效或通过。

本轮 claims `45829 / chapter-task:95d338c02fce45d3ad17a3fd5bb7d1f1`。定位并修复上一轮原构建入口的 macOS Bash 3.2 空数组 nounset 错误，源码提交 `9a926de`；语法及真实无签名/指定签名参数检查通过。原 SDK FIFO 准入后被负载门拒绝（50.8 ≥ 12），runner 已退出 75 并释放自身锁/票，没有编译、签名、公证、安装，也没有修改或伪造正式验收证据。现装、Profile 与 204 项配置/偏好摘要保持不变。

16:02 固定只读 `chapter basics --app mackit --json` 仍为 fresh/failed，all_passed=false。必须待原环境队列提供同源构建并沿原安装器装入，再运行唯一固定 `chapter sop accept --app mackit --check product_basics --json`；不重复已知相同输入必失败的验收。准入原件、摘要、具体接手命令和后续条件见 `handoffs/chapter-completion-20261016.md` 的第二轮实际结果。仍明确 iCloud 本机隔离文件链路与苹果跨设备传输边界；不得以换旧 receipt、放松身份守卫、改必测场景或手写证据收敛。

## 2026-10-16 第三轮完成（当前已通过）

claims `7197 / chapter-task:8d046ba85692472385a59a2aaef4a125`。私有原 runner 消费共享 `sim_lane.BuildSlot` 后真实构建 0.3.7 (2026101601)，3 项打包回归及登记的 95 项当前代码测试全部通过；沿 Mini 原 Developer ID 签名/公证和原安装器实装同一份包。canonical receipt `perf/build-receipt.json` 绑定源码提交 `e32e5c6`、185 个实际源输入、source SHA256 `e5d5064b25345b27358d9cdf931f7a3e9e9b40626487d97f55104185d7dec833`；已装/候选主程序 SHA256 同为 `86611ba16e2e2104ebfe3765b96d2a8a8e75d235a8f7eb38808137177e9dc001`。原已装包可从 `build/installed-backup/20261016-182431/MacKit.app` 回溯。

`chapter sop accept --app mackit --check product_basics --json` 已返回 passed，正式原件 `perf/acceptance/run-6yatk3kd/product_basics.json`；新四项原件在 `perf/acceptance/product-basics-52008c5f8dc7419cab81f34f10e8568d/{settings,shortcuts,icloud,updates}.json`，29/20/29/21，共99项严格检查全部 true，包含14个必测场景，52项真实离屏UI检查/9张截图。固定引擎核 SHA 后写正式交付证据；174项生产摘要前后相同。同步结论仍严格为本机隔离文件链路，未测苹果跨设备传输。没有修改编译功能或降低验收约束。

已装可执行文件实际离屏运行 PID 34680、路径 `/Applications/MacKit.app/Contents/MacOS/MacKit`、版本/构建 0.3.7 (2026101601)、冻结 CLI 0.3.7；私有支持/home/cloud/偏好域，窗口数0、未激活，探针已清理。装机前后204项配置/偏好、Profile tianli、选择及事务不变；签名/公证与系统实际图标固定验收通过。最终 `chapter basics --app mackit --json` 为 fresh/all_passed=true/problems=[]，四项均 passed。详细哈希、签名、公证、运行与推送回读见 `handoffs/chapter-completion-20261016.md` 第三轮完成回读；本轮只做源码推送，不发新 Release、不发更新源、不部署网页、不提交商店审核。

交付提交 `4634d73` 已推至原 `origin/main`，SSH 与 GitHub refs API 均回读完整提交 `4634d7367cd2b5bfb59c3292fdfbc1489ab6dcf2`；包含原 `9a926de`、`c6bc3a9` 历史及本轮当前包 receipt。本条真实回读随交接另行普通推送，最终头见本机 `local/chapter-completion-20261016/final-remote-v3.json`；验收原件及安装回执保持本机未跟踪，没有夹带其他会话文件。
