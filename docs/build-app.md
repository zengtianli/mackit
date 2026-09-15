# 构建 macOS App

从 GitHub 克隆完整源码，使用 macOS、Xcode/Command Line Tools 和 uv。App 原生界面使用 SwiftUI；内置 CLI 使用 PyInstaller 打包。发布的 arm64 版本在 Apple Silicon 构建。

```sh
uv venv --python 3.12 build/app-venv
uv pip install --python build/app-venv/bin/python pyinstaller==6.22.0
python3 -m unittest discover -s tests -v
bash scripts/build-app.sh
```

产物为 `build/app/Tianli MacKit.app`。不设置身份时使用本机 ad-hoc 签名；公开发行应设置 `MACKIT_SIGN_IDENTITY`，对同一产物完成 Apple notarization、staple 与验证，再执行 `bash scripts/package-app.sh`。身份和凭据不写入源码。版本唯一源是根目录 `VERSION`。

构建脚本在维护者机器复用共享 Xcode 选择器，在其他机器使用 `xcrun` 的已选 Xcode。App 可分发包不依赖维护者目录、Python 安装或 uv。原生程序与冻结引擎按当前架构一起构建，不把 arm64 包标为 Universal。

`mackit gui` 是 App 使用的 JSON 协议：stdin 为一个请求对象、stdout 为一个带 `ok` 的结果、stderr 为进度。安装与恢复仍调用 CLI 的同一事务实现。`--home` 可指定隔离验证目录；App 的 `--demo-home <目录>` 对应同一路径，并禁用本机软件安装与系统权限按钮。

测试仅操作临时目录；完整软件安装、系统权限和下载插件仍需在适合的环境中验收。版本升级不要覆盖已有 GitHub Release 的同名资产。
