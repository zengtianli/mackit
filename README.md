# Tianli MacKit

[English](README_EN.md) · [产品主页](https://mackit.tianli.cyou) · [快捷键手册](https://mackit.tianli.cyou/keys.html)

把 Mac 的终端、编辑器与桌面快捷键整理成一套找得到、改得明白、能恢复的配置。

**原生 macOS App + CLI；自带运行环境，关闭 App 后不常驻。** 管理 zsh、Neovim、Hammerspoon、Ghostty、tmux、Yazi、Karabiner、yabai/skhd；每个组件的自定义快捷键集中在自己的 keymaps 文件。

## 下载 App（推荐）

[下载 MacKit 0.2.0 · Apple Silicon DMG](https://github.com/zengtianli/mackit/releases/download/v0.2.0/MacKit-0.2.0-arm64.dmg) · [官网与演示](https://mackit.tianli.cyou/)

需要 macOS 14+、Apple Silicon（M 系列）。App 内置运行环境，无需先安装 Python 或 Git。使用 Developer ID 签名并经 Apple 公证。

1. 下载并打开 DMG，把 **Tianli MacKit** 拖到 **Applications / 应用程序**。
2. 从应用程序打开 App，在“安装配置”选择预设与组件，点击“预览配置变化”。
3. 点击“安装缺失软件与依赖”；缺少 Homebrew 时，点“安装 Homebrew”并在系统安装器完成授权。
4. 点击“备份并安装配置”，完成后重新打开终端和相关应用。

App 提供快捷键搜索、配置文件编辑（保存前备份）、依赖检查与按记录恢复。已有 MacKit 安装会接管原配置源；首次安装将配置放在 `~/.local/share/mackit`。管理员密码只在系统安装器输入；辅助功能等权限按系统与各应用提示自行确认。yabai/skhd 仍是手动安装、启动的可选高级组件。

App 快捷键：⌘1–4 切页、⌘F 搜索、⌘R 刷新、⌘S 保存、⌘Return 预览。App 当前提供 arm64 安装包，Intel 用户可使用下方 CLI。

[App 操作与恢复说明](docs/macos-app.md) · [构建 App](docs/build-app.md)

## 命令行方式

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
mackit doctor               # 检查安装来源、依赖及声明冲突
mackit restore              # 恢复最近一次安装前的配置
```

编号效果：`01_第一行`、`02_第二行`。配置绑定与文本处理实现在不同文件，查看按键不用再翻功能代码。

## 两种预设

- **developer**：保留 Neovim 原生移动和 Ctrl-W 窗口键，默认只安装终端组件。
- **tianli**：保留 S 保存、Q 退出、J/K 移动15行、空格 Leader，以及桌面的右侧修饰键习惯。使用 `--profile tianli` 选择。

Hammerspoon 在 developer 预设下默认不开全局键，可从菜单栏逐项启用。配置安装不代替 macOS 权限授权，也不会自动启动窗口管理服务。

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
