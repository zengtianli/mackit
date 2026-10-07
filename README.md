# MacKit · 配置助手

菜单“配置与更新…”提供可选的 iCloud 配置同步及导出、导入，记住预设和组件选择。便携选择独立保存在 `~/.config/mackit/portable-preferences.json`；安装回执、来源路径、权限、私有覆盖和服务状态不迁移。新电脑恢复选择后，仍可先预览，再按原流程安装配置。菜单“检查更新…”按需查询 MacKit 正式发行版本。

[English](README_EN.md) · [产品主页](https://mackit.tianli.cyou) · [快捷键手册](https://mackit.tianli.cyou/keys.html)

把 Mac 的终端、编辑器与桌面快捷键整理成一套找得到、改得明白、能恢复的配置。

**原生 macOS App + CLI；自带运行环境，关闭 App 后不常驻。** 管理 zsh、Neovim、Hammerspoon、Ghostty、tmux、Yazi、Karabiner、yabai/skhd；每个组件的自定义快捷键集中在自己的 keymaps 文件。

从 v0.3.5 起，App 名为 **MacKit**（显示名 MacKit · 配置助手），每一页都有对应命令（`status`、`prepare`、`plan`/`apply`、`deps`、`keys`、`file`、`window`、`restore`、`link`），供 Agent 与脚本调用（见[命令行：给 Agent 与脚本](#命令行给-agent-与脚本)）；配置内容、快捷键与安装语义保持原状，从旧版升级见下文。

## 下载 App（推荐）

[下载 MacKit 0.3.6 · Apple Silicon DMG](https://github.com/zengtianli/mackit/releases/download/v0.3.6/MacKit-0.3.6-arm64.dmg) · [官网与演示](https://mackit.tianli.cyou/)

需要 macOS 14+、Apple Silicon（M 系列）。App 内置运行环境，无需先安装 Python 或 Git。使用 Developer ID 签名并经 Apple 公证。

本地验收构建为 0.3.6 (636)，公开下载仍为 0.3.6 (0.3.6)。下列下载大小取公开 DMG，运行指标以实测所列构建为准。

<!-- lightweight:start -->
## 资源占用

| 安装包 | 空闲内存 | 空闲 CPU | 冷启动到首屏就绪 |
|---|---|---|---|
| **12.1 MB**（装好后 24.2 MB） | **48.2 MB** | **0%** | **571 ms** |

原生 SwiftUI；配置引擎仅在操作时启动并退出，没有轮询或定时任务。随包附带 Python 标准库运行环境；剥离符号并移除运行不需要的开发文件。

<sub>v0.3.6 (636) · Mac16,12 / Apple M4 / macOS 27.2 · 当前装机GUI只读加载本机配置快照并离屏绘制首屏；不保存偏好或更改系统配置。下载大小取现有0.3.6公开DMG，运行数据属于明确标记的本地验收构建。 · 2026-10-05。数字来自所列设备实测，版本更新后重新测量。内存口径为 phys_footprint；CPU 为 60 秒采样窗内 CPU 时间 ÷ 墙钟；大小按十进制 MB。原始数据见 [perf/lightweight.json](perf/lightweight.json)。</sub>
<!-- lightweight:end -->

1. 下载并打开 DMG，把 **MacKit** 拖到 **Applications / 应用程序**。
2. 从应用程序打开 App，在“安装配置”选择预设与组件，点击“预览配置变化”。
3. 点击“安装缺失软件与依赖”；缺少 Homebrew 时，点“安装 Homebrew”并在系统安装器完成授权。
4. 点击“备份并安装配置”，完成后重新打开终端和相关应用。

App 提供快捷键搜索、配置文件编辑（保存前备份）、依赖检查与按记录恢复；「窗口」页（⌘5）把 yabai 设置做成带说明的表单，skhd 快捷键可点按录制、自动标出与其他工具的冲突，应用规则可视化添加，保存时重新生成 yabairc / skhdrc 并备份，可选择立即在运行中的 yabai/skhd 生效。已有 MacKit 安装会接管原配置源；首次安装将配置放在 `~/.local/share/mackit`。管理员密码只在系统安装器输入；辅助功能等权限按系统与各应用提示自行确认。yabai/skhd 仍需按官方说明手动安装；装好后可在「窗口」页启动或停止。

从 0.3.3 起 `mackit` 命令随 App 提供：从 App 安装配置后，`~/.local/bin/mackit` 指向 App 内的命令，随 App 一起更新，并继续使用安装时记录的配置源（`edit`、`keys`、`doctor`、`update` 用法不变）。已有安装可重新在 App 中安装，或运行 `"/Applications/MacKit.app/Contents/Resources/core/bin/mackit" link` 切换；`mackit restore <记录>` 可恢复原来的链接。源码目录用 `./install.sh` 安装仍保持原有链接方式。

App 现名 **MacKit**（显示名 MacKit · 配置助手，bundle ID `cyou.tianli.mackit` 不变）；0.3.4 及更早版本安装名为 Tianli MacKit。从旧版升级：把新 App 拖入应用程序后运行一次 `"/Applications/MacKit.app/Contents/Resources/core/bin/mackit" link`，再把旧的 Tianli MacKit 移到废纸篓；`mackit doctor` 会指出仍指向旧 App 的失效链接。

App 快捷键：⌘1–5 切页、⌘F 搜索、⌘R 刷新、⌘S 保存、⌘Return 预览。App 当前提供 arm64 安装包，Intel 用户可使用下方 CLI。

[App 操作与恢复说明](docs/macos-app.md) · [构建 App](docs/build-app.md)

## 从源码安装命令行

需要 macOS、Python 3.11+、Git；Neovim 配置需要 0.11+。先安装你选择的应用。缺 Python 时用 `brew install python`；依赖清单由 `mackit deps` 输出。

```sh
git clone https://github.com/zengtianli/mackit.git ~/.local/share/mackit
cd ~/.local/share/mackit
./bin/mackit deps
./install.sh
./install.sh --apply
```

第一条 install 只预览，第二条备份并安装。也可按需选组件：

```sh
./install.sh --apply --components zsh,nvim,tmux
```

重新打开终端：

```sh
config nvim                 # 打开 nvim 主配置
config zsh                  # 打开 zsh 主配置
mackit edit nvim-keys        # 所有自定义 nvim 键位
mackit edit number           # 行号、缩进、显示选项
mackit keys 编号             # 找到“选中多行 → 空格 n l”
mackit doctor               # 检查安装来源、依赖及声明冲突（含 keys.d 登记的 app 与 Keyboard Maestro）
mackit restore              # 恢复最近一次安装前的配置
```

自建或第三方 app 可把快捷键写成 `~/.config/mackit/keys.d/<app>.json`（`[{"component","mode":"global|app:<名称>","key","description"}]`），`mackit keys` 会一并列出，`mackit doctor` 会报告两处抢同一全局键、或 app 内快捷键被全局键先截走。已启用的 Keyboard Maestro 快捷键宏会被只读读入。

编号效果：`01_第一行`、`02_第二行`。配置绑定与文本处理实现在不同文件，查看按键不用再翻功能代码。

## 命令行：给 Agent 与脚本

App 里能看到、能做的事都有对应命令（界面给人用，命令给 Agent 用）。两者调用同一套引擎：`mackit/cli.py` 负责计划、安装与恢复，`mackit/gui.py` 与 `mackit/window.py` 是 App 各页的业务层，命令复用同样的校验、摘要锁、备份和安装记录，不另写一套。读命令加 `--json` 输出带 `"ok"` 的稳定对象，不写任何状态；失败时退出码非 0，`--json` 输出 `{"ok": false, "error": …}`。

```sh
mackit status --json                          # 预设、配置源、App/配置源版本与构建号（app.appBuild）、安装记录、mackit 链接状态
mackit prepare --json                         # 与 App「预览」相同：准备配置源（已就绪则不动），之后才能读写配置文件、改窗口设置
mackit plan --json                            # 预览变化，附 token
mackit select --components zsh,nvim --json     # 记住「安装配置」页的预设与组件勾选（不安装）；status 的 app.selected 读回
mackit apply --token <token>                  # 预览后目标未变才安装；一次可恢复的安装记录（token 不符时什么都不创建）
                                              # 含 karabiner 时结果带 karabiner：文件比 Karabiner 上次读入更新时才让它重读，并从它的日志确认
mackit doctor --json                          # 来源、依赖、命令链接、快捷键冲突；有问题退出 1
mackit deps --json                            # 每个 formula/cask 是否已装；--check 缺了退出 1
mackit deps --install                         # 只 brew install 缺的（仅真实 HOME；进度在 stderr，可随时用 deps --json 查询）
mackit keys 编号 --json                       # 快捷键目录 {ok, count, rows}（含 keys.d 与 Keyboard Maestro）
mackit keys --conflicts-with ctrl+alt+h --json   # 与「窗口」页、doctor 同一套规则的全局键冲突提示
mackit file list --json                       # 「配置文件」页的全部入口，含 local / local-keys / hs-local
mackit file read nvim-keys --json             # 内容 + sha256 摘要
mackit file write nvim-keys --digest <摘要> --from new.lua   # 摘要不符拒绝写入；旧文件进 editor-backups
mackit window status --json                   # yabai/skhd 状态、运行值、已保存设置/规则/快捷键、可选动作、摘要
mackit window set window_gap=8 layout=bsp     # 校验后重新生成 yabairc，先备份；--apply 同时让运行中的 yabai/skhd 生效
mackit window hotkey add --key ctrl+alt+h --action focus-west   # 或 --command '<单行命令>'；已占用加 --replace
mackit window hotkey remove --key ctrl+alt+h
mackit window rule add --app "System Settings" --manage off
mackit window save --digest <摘要> --from window.json           # 整体替换，格式同 window status --json 的 window
mackit window service stop skhd               # 启停 yabai / skhd（仅真实 HOME）
mackit karabiner status --json                # Karabiner 是否在运行、规则源文件与摘要、规则数、当前生效的那一代、最近一次重读、生效文件改动后是否已读入（loaded.current）
mackit karabiner rule list --json             # 每条规则：序号、开关、说明、起始键；rule show --index 4 看全文
mackit karabiner rule add --from rule.json --apply   # 加一条键到键规则（带 shell_command 的拒绝）；--apply 接着生成并让 Karabiner 重读
mackit karabiner rule disable --index 4       # enable / disable / remove 按 --index 或 --description；改前副本进 editor-backups
mackit karabiner reload --json                # 日志显示已读入当前文件就什么都不动（already_current，退出 0）；否则让它重读并确认，没确认退出 1（仅真实 HOME）
mackit restore <记录> --json                  # 恢复最近一次安装记录
mackit link                                   # 把 ~/.local/bin/mackit 指向当前 App 内的命令（有记录，可 restore）
mackit config status --json                   # 「配置与更新…」窗口：iCloud 开关、开关下面那句同步状态、可迁移的配置项（预设与组件选择）、App 是否在运行（只读）
mackit config export -o selection.json        # 导出配置：与窗口「导出配置…」同一份文件（--force 覆盖；-o - 输出到标准输出）
mackit config import selection.json --yes     # 导入配置：先备份原配置再覆盖；只记住选择，不安装
mackit config sync on --yes                   # 拨动「使用 iCloud 记住配置」（off 关闭；--dry-run 只看会不会变）；config status 读回
mackit update check --json                    # 检查更新：当前版本与构建号、正式发行的最新版本、有没有新版、怎么升级（只读，联网读发行记录）
mackit update install --dry-run --json        # 升级到新版会做什么（只读）；去掉 --dry-run 换成 --yes 才执行：验证发行包与签名、替换 MacKit.app，update check 读回
```

`--home <目录>`（不是你自己的主目录时）就是沙盒：不安装软件、不启停服务、不对运行中的 yabai/skhd 生效，也不写目录以外的文件。无论用 App 内命令还是源码目录的 `bin/mackit`，配置源都与 App 一样准备在 `<目录>/.local/share/mackit`：`plan` 只报告、不创建，`prepare` 或 `apply` 才从内置副本创建，所以窗口与配置文件的写入只落在沙盒里。沙盒若记录了目录外的配置源（0.3.5 以前的源码命令会这样），该来源只读，写入会被拒绝，换一个新目录即可。

不带 `--home` 时命令作用于本机真实配置：配置源是安装时记录的目录。从 git 仓库安装（`./install.sh`）时它就是仓库本身，`mackit window …`、`mackit file write` 会改仓库里的文件，与 App 保存的效果相同。

退出码：0 成功（查无结果也算）；1 操作失败或被拒绝（摘要过期、校验不过、`karabiner reload` 未确认、doctor 或 deps --check 发现问题）；2 用法错误，此时加 `--json` 也输出 `{"ok": false, "error": "usage: …"}`。`apply` 与 `--apply` 只要安装本身成功就退出 0，Karabiner 的情况看结果里的 `karabiner`：`reloaded` 为真是日志里有比这次改动更新的读入记录；`reason` 为 `already_current` 是日志显示生效文件改动后已经读入过，不该再有新记录；`not_confirmed` 且 `expected` 为真是文件比上次读入新、已让它重读却没等到记录，`expected` 为 null 是日志里没有更早的读入记录可比。`karabiner` 与 `select` 两组命令的失败输出是 `{"ok": false, "error": {"code": "…", "message": "…"}}`，其余命令的 `error` 仍是一句话。读命令、写命令、输出形状与只在窗口里做的事列在 `mackit --help` 末尾。

`config …`、`update check` 与 `update install` 是 App「配置与更新…」窗口里的几项。它们属于 App 本身（偏好域、版本、发行渠道、装着的那个 App），由 App 的可执行文件应答，`mackit` 只原样转交，所以要用 App 内的命令（`~/.local/bin/mackit`）；源码目录的 `bin/mackit` 会回答 `app_missing`。命令与窗口读写同一份设置：命令拨了开关或导入了选择，开着的窗口自己跟随。它们不开窗口、不抢焦点。`config status` 的 `sync_status` 是开关下面那句同步状态：App 在运行时是它此刻显示的那句（`from` 为 `app`、`live` 为真），没在运行时是上一次同步留下的那句和时间（`record`），没有可用记录时是窗口打开时的初值（`derived`）。`update install --yes` 与窗口的「升级到新版…」是同一条路：验证发行包与签名，运行中的 MacKit 先退出，替换 `MacKit.app` 后再重开，配置保留，替换失败回滚，换下来的旧 App 移到废纸篓；没有新版时退出 0（`installed` 为假），先看会做什么用 `--dry-run`，做完用 `update check` 读回。它可能要几分钟（下载与验证各有上限）。未完成时退出 1，`error.code` 说明停在哪：`check_incomplete`、`manual_install`（这个安装位置或渠道不能由命令替换，给出安装包地址）、`upgrade_failed`、`app_busy`、`replace_failed`、`cleanup_failed`（新版已装好，旧包没能移走）。失败输出是 `{"ok": false, "command": "…", "error": {"code": "…", "message": "…"}}`；退出码 2 除了参数不对（`usage`），还有 `import`、`sync`、`update install` 缺 `--yes`（`confirmation_required`）和导出目标已存在又没加 `--force`（`file_exists`）。完整的输出字段与错误码见 `mackit config --help`。这组设置不在任何 `--home` 目录里（开关在 App 的偏好域，备份在 Application Support，副本在 iCloud Drive），沙盒 `--home` 下 `config` 回答 `isolated_home`；`update install` 替换的是本机装着的 App，在沙盒 `--home` 下同样回答 `isolated_home`、什么都不动，`update check` 照常可读。原有的 `mackit update`（不带子命令，对源码目录执行 `git pull --ff-only`）不变。

`keys --json` 自 0.3.5 起输出 `{ok, count, rows}`，此前版本输出行数组。

只留在界面里的操作：按键录制（命令行直接写键名）、在 Finder 中显示、打开系统设置的权限页、下载 Homebrew 官方安装包并打开系统安装器（缺 brew 时 `deps --json` 给出官方安装包地址）、切页与搜索框聚焦、未保存草稿与退出确认、打开在线手册和 GitHub 链接。App 用 `mackit gui` 这个不列在帮助里的 JSON 通道调用同一引擎。

## 两种预设

- **developer**：保留 Neovim 原生移动和 Ctrl-W 窗口键，默认只安装终端组件。
- **tianli**：保留 S 保存、Q 退出、J/K 移动15行、空格 Leader，以及桌面的右侧修饰键习惯。使用 `--profile tianli` 选择。

0.3.6 之后的源码里按键分两层（随 tianli 预设安装）：Karabiner 只做键到键的映射，凡是要运行脚本或打开应用的键都由 skhd 绑定，每个动作以系统通知反馈；不经过 Hammerspoon，Hammerspoon 不运行时这些键照常可用。个人脚本只通过 `~/.config/mackit/bin/` 下的同名可执行文件接入，文件不存在时对应按键不做任何事。配置安装不代替 macOS 权限授权，也不会自动启动窗口管理服务。

个人目录、账号、历史、Git 身份与设备标识不随开源包分发。本机覆盖放在 `~/.config/mackit/`，更新时保留。安装会备份既有文件与软链；若安装后你换成了新的配置，恢复命令会先拒绝覆盖新内容。

## 结构

```text
components/    每个应用的配置、keymaps、功能实现
profiles/      developer / tianli 预设
mackit/        安装、恢复、查询与检查
data/          从键位声明生成的索引
site/          产品主页与自动生成手册
tests/         隔离安装和原生配置验证
```

详见[配置与恢复](docs/configuration.md)、[实际验证范围](docs/validation.md)。源码声明检查不能定位所有第三方 App 的抢键。

MIT；第三方代码保留其原许可，见 [THIRD_PARTY.md](THIRD_PARTY.md)。
