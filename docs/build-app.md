# 构建 macOS App

从 GitHub 克隆完整源码，使用 macOS、Xcode/Command Line Tools 和 uv。App 原生界面使用 SwiftUI；内置 CLI 使用 PyInstaller 打包。发布的 arm64 版本在 Apple Silicon 构建。

```sh
uv venv --python 3.12 build/app-venv
uv pip install --python build/app-venv/bin/python pyinstaller==6.22.0
python3 -m unittest discover -s tests -v
bash scripts/build-app.sh --local   # 开发构建：build/local/app/MacKit.app，不改 dist/releases
bash scripts/build-app.sh           # 发行构建
```

发行构建产物为 `build/app/MacKit.app`，源码包写入 `dist/releases`；`--local` 只写 `build/local/`，避免覆盖已发布版本的同名源码包。两种方式都不装机、不启动、不公证。不设置身份时使用本机 ad-hoc 签名；公开发行应设置 `MACKIT_SIGN_IDENTITY`，对同一产物完成 Apple notarization、staple 与验证，再执行 `bash scripts/package-app.sh`。身份和凭据不写入源码。版本唯一源是根目录 `VERSION`。

构建脚本在维护者机器复用共享 Xcode 选择器，在其他机器使用 `xcrun` 的已选 Xcode。App 可分发包不依赖维护者目录、Python 安装或 uv。原生程序与冻结引擎按当前架构一起构建，不把 arm64 包标为 Universal。

`mackit gui` 是 App 使用的 JSON 协议（不列在 `--help` 中；进程总是退出 0，以 `ok` 判断结果）：stdin 为一个请求对象、stdout 为一个带 `ok` 的结果、stderr 为进度。Agent 与脚本使用公开子命令（`status`、`file`、`window`、`deps` 等），它们调用同一个 `gui.py` / `window.py` 业务层。安装与恢复仍调用 CLI 的同一事务实现。`--home` 可指定隔离验证目录（沙盒）：配置源准备在 `<目录>/.local/share/mackit`（`mackit prepare` 或 `apply` 创建），源码命令与 App 内命令都一样，目录以外的文件、软件与服务都不会被改动；App 的 `--demo-home <目录>` 对应同一路径，并禁用本机软件安装与系统权限按钮。

测试仅操作临时目录；完整软件安装、系统权限和下载插件仍需在适合的环境中验收。版本升级不要覆盖已有 GitHub Release 的同名资产。

公证：`python3 scripts/notarize.py <zip 或 dmg> <回执.json>`（使用维护者本机的 App Store Connect API 密钥，源码不含凭据）。装机：公证并 staple 后运行 `python3 scripts/install-app.py`。它校验构建回执、签名与公证，把 `/Applications/MacKit.app` 原子替换（旧副本进 `build/installed-backup/`），不启动 App；若存在同 bundle ID 的旧名 `/Applications/Tianli MacKit.app`，先用新 App 的 `mackit link` 把仍指向旧 App 的 `~/.local/bin/mackit` 改指新 App（有安装记录，可 restore），再把旧 App 移到 `~/.Trash/mackit-rename-<时间>/`。

固定产品验收见 [acceptance.md](acceptance.md)。`--ui-self-test` 在进程内离屏运行真实界面，不启动常规窗口。

产品页截图：装好当前版本后运行 `python3 scripts/capture-media.py`。它用 `macos/Sources` 的生产界面加 `scripts/capture/main.swift` 编出独立采集包（另一个 bundle ID），以 App 自带的 `-page` / `-section` 参数逐页打开，窗口放在所有屏幕之外、不成为键盘窗口、不激活 App；读回窗口服务器合成的本进程窗口图像，写入 `site/media/app.png`、`window.png`、`window-hotkeys.png` 与 `perf/media-capture.json`。引擎是已装 App 的命令（真实 HOME，只读快照）；装机版本与 `VERSION` 不同时退出 75，不录旧版。

维护者打包前须由实际构建生成 `perf/build-receipt.json`（Chapter 的 `app_sop.py build-receipt` 入口）；回执记录干净提交、源码摘要、App 版本和可执行摘要。`scripts/release-checksums.py` 校验回执与待打包 App，一致后同时生成 `dist/releases/release.json` 与入库的 `perf/release.json`。回执过期或缺失时停止，不能用打包时的 HEAD 冒充构建来源，也不能把新代码的回执绑定到旧发行包。

正式图标唯一源位于 `icon/`：Seedream 原图、提示词、打包后的 `AppIcon.png` / `AppIcon.icns` 与 `provenance.json`。构建与官网读取同一份打包图标；不要使用代码符号图覆盖正式素材。
