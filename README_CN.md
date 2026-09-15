# Tianli MacKit

[English](README.md) · [产品主页](https://mackit.tianli.cyou) · [快捷键手册](https://mackit.tianli.cyou/keys.html)

把 Mac 的终端、编辑器与桌面快捷键整理成一套找得到、改得明白、能恢复的配置。

**一个 CLI，原生配置文件，没有新增常驻进程。** 管理 zsh、Neovim、Hammerspoon、Ghostty、tmux、Yazi、Karabiner、yabai/skhd；每个组件的自定义快捷键集中在自己的 keymaps 文件。

## 安装

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

