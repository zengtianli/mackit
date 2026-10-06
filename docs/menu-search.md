# 搜索当前 App 的菜单命令

MacKit 自带原生菜单搜索，不依赖 Raycast、Hammerspoon 或云端。面板按需启动，关闭后退出；在搜索框为空时列出所有可读取的菜单命令，输入后只过滤这个 App 的菜单。

在 MacKit 的「窗口 → skhd 快捷键」添加一条：录制呼出键，动作选择「搜索当前 App 菜单（MacKit）」，保存并应用。没有默认注册的全局键；可重新录制或删除，冲突检测与已有键位总表共用。热键监听复用已经安装的 skhd，不新增后台服务。

按呼出键时锁定拥有菜单栏的 App；↑↓ 选择，回车执行，Esc 或点击其他窗口取消。支持完整菜单路径、同名命令区分、快捷键、勾选及禁用状态。中文输入法正在组词时，回车仍用于确认候选；输入框的系统编辑键保留。每次打开重新读取，面板内也可点「刷新」。

读取和执行使用 macOS 辅助功能接口，需要正式安装的 MacKit 获得辅助功能权限。没有权限时显示说明和系统设置入口，不自动修改权限。异常和超时会明确显示；禁用项不会执行。选择保留实际菜单对象并在执行前核对所属 App、标题和启用状态，避免把旧位置编号误用到新菜单。

CLI 与面板共用原生实现：

```sh
mackit menu status --json
mackit menu show
mackit menu scan --json                 # 当前 App，纯读取
mackit menu scan --pid 123 --json       # 指定已运行 App，纯读取
mackit menu execute --pid 123 --path-json '["View","Show Status Bar"]' --json
```

执行必须提供唯一的完整路径，并且目标 App 仍在前台。读、显示和执行本机 App 的命令都拒绝隔离 `--home`，不会突破测试沙盒。Agent 的真实界面验收只用平台 Computer Use；不能用 CLI 执行代替真实热键和回车验收。

开发检查：`MacKit --menu-self-test --output DIR` 离屏使用生产面板，覆盖过滤、中文、三级路径、重复名称、禁用保护、输入法及上下键/回车/Esc 的进程内处理，并导出浅色/深色 PNG。加 `--pid N` 时截图读取该 App 的真实菜单；整个测试不弹窗、不抢焦点、不执行外部菜单命令。

实现参考 [Raycast 官方说明](https://manual.raycast.com/navigation)、[2021 年功能发布](https://www.raycast.com/changelog/1-20-0) 和 [第三方扩展](https://github.com/BalliAsghar/menu-bar-search-raycast)。MacKit 独立编写，未复制 Raycast 安装包或第三方仓库源码。单机实测与尚未验证的范围见项目 handoff 和用户提供的 R1–R9 清单。
