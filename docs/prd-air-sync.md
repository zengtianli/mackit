# PRD · Air 追平交给 MacKit 底座

版本 0.1（草案）· 2026-10-17 · 状态：只写需求，未实施、未接触 Air。

来源：本人 2026-10-17 “air 都先不管；air 同步这些 mackit 可以做，你写好 prd 到 mackit 这个底座 或者 mac pair 的目录里生成 prd”。

标注：**[事实]** 本文写作时在 Mini 上读到的；**[推测]** 没有实证的判断；**[待定]** 需本人拍板。

## 1. 目标与非目标

目标

- Air 开机或唤醒后自己追平 Mini：自有 App、Homebrew/第三方软件、MacKit 管的 dotfiles/配置。全程 Air 自己拉，Mini 不推装。
- 汇报前在 Air 上跑一条命令（暂名 `mackit air ready`），一屏看完：各项是否追平、差在哪、AI CLI 登录状态、汇报材料是否到位。
- 把现有分散的能力接到一个入口，不再建第二套同步。

非目标

- 不让 Mini 远程安装或签名 Air 上的东西；不把 Air 落后算成 Mini 的交付失败（HARNESS 第 1、6 节）。
- 不替 Air 自动登录 Claude/Codex，也不解锁钥匙串；只显示状态。
- 不管账号额度、订阅余额。
- 不做双机任务派发、Syncthing 配对、网络打洞。这些原样留在 mac-pair / macmini。
- 不同步机器私有项：权限（TCC）、登录态、本机 `local/` 覆盖、业务数据。

## 2. 范围

| 项 | 本 PRD 管什么 | 不管什么 |
|---|---|---|
| 自有 App 版本 | Air 是否等于更新源最新版；更新源是否落后于 Mini 装机版 | 构建、签名、公证本身（归各产品与 app 技能） |
| Homebrew / 第三方软件 | Air 是否跑过当天的 brew 升级，Cadence software 报的差异 | 选型、破解/激活类软件 |
| dotfiles / 配置 | MacKit 组件在 Air 上的版本、`mackit doctor` 结果 | 本机私有覆盖 `local/` |
| AI CLI 登录 | Claude / Codex 在 Air 本机会话里是否已登录，只读展示 | 自动登录、额度 |
| 汇报材料 | 本人指定的汇报目录在 Air 上是否已同步到最新 | 材料内容 |

## 3. 现有能力与 owner（不建第二套）

| 能力 | 原 owner / 入口 | 现状 | MacKit 的处理 |
|---|---|---|---|
| 自有 App 自更新 | `~/Dev/tools/dev/lib/tools/macos/bin/always_latest.py` → `own_apps_update.py`，launchd `com.tianli.always-latest` 每天 05:00 | [事实] Mini plist 为每天 05:00；只认 `~/.local/bin` 指向 App 内命令、且更新源有目录的 App；不降级 | **改接**：增加“唤醒/开机后触发”入口时调用它，不复制逻辑 |
| 自有 App 更新源 | `~/Dev/tools/dev/lib/tools/macapp/publish_private_update.py`，iCloud `TianliApps/Updates/<bundle id>/<渠道>/release.json` | [事实] Cadence Mini 装机 1.5.17 (63)，更新源 `default` 为 1.5.13 (59)；Air 据本人所述为 1.5.11。快装不发更新源，所以 Air 最多追到更新源 | **只读**：`ready` 报出“更新源落后于 Mini”，提醒在 Mini 发源；发源仍归 Mini 的产品流程 |
| 双机软件差异与安装 | Cadence `cadence software`（`engine/automation_software.py`）+ macmini 固定软件安装 owner | [事实] 有观测 TTL 与过期显示未知；10-16 交接记有 `software-source-*-mini` 连续失败（JSONDecodeError），归 Cadence 会话 | **只读消费** `cadence software status --json` 摘要；不另写对比器 |
| 文件同步 | Syncthing 两机实例（mac-pair 管配对与 `.stignore`） | [事实] 七个共享根已配对实测 | **只读**：汇报材料就绪判断读 Syncthing 官方 REST 的目录完成度，不另建同步 |
| 派活、Git 指针、双机回执 | `~/mac-pair`（`pair.py`）、cc-home `skills/macmini` | 已在用，Air 侧非日常主路径 | 不动 |
| dotfiles / 配置 | MacKit 本身（`mackit status/doctor/apply`） | [事实] MacKit 本身无 iCloud 更新源，Air 拉不到新版（10-16 交接） | **承担**：补 MacKit 自己的更新源发布，Air 才能自更新 MacKit |
| 双机审计 | `own_apps_audit.py`（会 SSH 对端） | 只在本人选双机核验时用 | 不作为 `ready` 的依赖；`ready` 只读本机 |

MacKit 应承担：Air 侧的一个触发入口 + 一个只读就绪报告（`mackit air status/ready`），以及 MacKit 自身的更新源。

改接：唤醒触发调用原 `own_apps_update.py` 与 brew 维护；差异读 Cadence；同步读 Syncthing。

退役：无现成可退。实施后若出现任何为 Air 单写的同步脚本（含 mac-pair 旧任务里的一次性补装脚本），按 workspace 规则归档，不保留并行路径。[推测] 当前没有这类常驻脚本，实施时再核。

## 4. 用户故事

1. 本人汇报前打开 Air，Air 唤醒后数分钟内自行跑一轮追平（brew、自有 App、MacKit 配置），不需要开终端。
2. 本人或 Air 上的 Agent 运行 `mackit air ready`，一屏看到：
   - 自有 App：N 个已是更新源最新；M 个更新源本身落后 Mini（标明“去 Mini 发源”）；沙盒 App 需在窗口选目录的列出来。
   - 软件：最近一次 brew 升级时间与结果。
   - 配置：`mackit doctor` 摘要。
   - AI CLI：Claude、Codex 各自“已登录 / 未登录 / 钥匙串锁定 / 未知”，灰或黄显示，不报警。
   - 汇报材料：指定目录同步完成度、最近修改时间。
3. 某项没追平时，报告给出下一步原命令（例如 `own_apps_update.py` 手动跑法），不自动重试成死循环。

## 5. 核心原则（沿 HARNESS）

- **不存自动失败状态，每次现场判断**：`ready` 每次重新读版本、签名、登录、同步完成度；不写“上次失败”“冷却”“已知坏”这类会拦住下次的持久状态。日志只作记录，读取时不当事实。
- **Mini 只发更新源不推装**：MacKit 不经 SSH 向 Air 安装；Air 的追平全由 Air 本机触发。
- **分布式并行只为真实资源互斥**：brew、自有 App 更新、配置检查可并行；只有同一 App 的替换、brew 自己的锁这类真实资源互斥。不建全局串行队列。
- **账号额度不操心**：登录状态只显示，不查额度，不因未登录发 Bark 或系统通知。
- **状态色**：好绿、中黄、差红、未知灰；登录未知或钥匙串锁定用灰/黄，不用红。
- **热更新**：报告里的文字、状态词、汇报目录清单放数据文件（沿 MacKit `data/` + `~/.config/mackit/` 覆盖的现有做法），不写死在代码里。
- **界面与命令同源**：若 App 加“Air 就绪”页，同轮给 `--json` 命令并登记 `sop.agent_cli`。

## 6. 验收标准

- 自有 App：对每个有更新源的 App，Air 本机回读 `CFBundleShortVersionString`、`CFBundleVersion`、`codesign` TeamID 与可执行文件 SHA256，与 `release.json` 记录一致才算追平；与 Mini 装机版的差另列为“更新源落后”。
- Homebrew：`brew outdated` 为空或只剩已知顺延项（always_latest 自身规则）。
- 配置：`mackit doctor` 无错误。
- 登录：`ready` 对 Claude/Codex 给出四态之一，任何一态都不触发通知；从 SSH 会话与本机 GUI 会话读到的结果分别标出来源。
- 汇报材料：Syncthing REST 报目录 100% 且无 pending；读取失败显示未知，不显示已同步。
- `ready` 只读：跑前跑后 Air 上 `/Applications`、偏好域、配置文件哈希不变（隔离 `--home` 测试中核对）。
- 唤醒触发：Air 唤醒后一轮追平只启动一次（同一唤醒不重复），关闭 MacKit App 不影响。

## 7. 分期里程碑

| 期 | 内容 | 完成判据 |
|---|---|---|
| M0 | 本 PRD 确认；本人决定第 9 节问题 | 本人回复 |
| M1 | MacKit 自己发 iCloud 更新源，Air 能经 `own_apps_update.py` 拉到 MacKit | Air 上 MacKit 版本等于更新源（Air 回来后本机回读） |
| M2 | `mackit air status/ready --json`（只读），先在 Mini 隔离环境测 | 单元测试 + 隔离 `--home` 只读核对 |
| M3 | 唤醒/开机触发：调用原 always_latest 链 | Air 合盖再开一次，回执显示一轮追平 |
| M4 | 汇报材料目录与登录四态；可选 App 页 | `ready` 一屏显示五项 |
| 并行（不归 MacKit） | Mini 侧把待分发的自有 App 正式公证并发源（如 Cadence 1.5.17） | 更新源 = Mini 装机版 |

## 8. 风险

- [事实] Air 最多追到更新源；Mini 快装不发源时 Air 永远落后。根因在发布节奏，MacKit 只能显示，不能修。
- [推测] Air 上 Claude/Codex 经 SSH 显示未登录，是 SSH 会话访问不到登录钥匙串所致，GUI 本机会话里可能正常。未在 Air 本机核实。`ready` 要分别标来源，避免误报。
- [事实] Cadence 软件同步的对端源任务有连续失败记录；`ready` 读它时遇到错误显示未知，不阻塞其他项。
- [推测] 唤醒后立即跑 brew 可能撞上汇报现场的网络（手机热点）与电量；需要电量/网络门。
- 沙盒 App 必须本人在窗口选一次更新目录，自动化无法代替。

## 9. 开放问题（需本人决定）

1. 唤醒触发是否要：每次唤醒都追平，还是只在距上次成功超过 N 小时才跑？是否允许在电池/热点下跑？
2. 汇报材料目录清单：哪些目录算“汇报要用的”，由本人给一份初始清单，还是按最近 7 天 Mini 上修改过的 Work 交付目录自动推？
3. 入口放 MacKit App 新页，还是只要 CLI（`mackit air ready`）？
4. Mini 装机后是否默认同轮发更新源（快装除外，正式构建才发）——这影响 Air 能否追平，但属于各产品发布规则，不归 MacKit。
