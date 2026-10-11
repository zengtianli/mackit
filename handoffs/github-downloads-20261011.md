# GitHub Release 下载收口 · 2026-10-11

- task_id：`lintel-github-release-downloads-20261011`。
- 授权：站内备用不要了，全部 GitHub Release；本轮只改 MacKit 页面、原构建入口与交接，不部署、不推送、不发新 Release。
- 源码提交：`0091a3a9ebdf0153067f97c4b811801fb2ececf5`（仅 `scripts/build-site.py`、`site/index.template.html`；5 行新增、5 行删除）。
- 构建目录：`/Users/tianli/Apps/mackit/dist/site`。
- 实际获取与校验入口：[GitHub Release](https://github.com/zengtianli/mackit/releases/tag/v0.3.6)。
- 状态：**本地构建与必要检查完成，尚未发布**；留给 Lintel 主会话冻结、统一 `site ship`。

## 本轮改动

页面版本和 Release URL 取 `perf/release.json` 的发行版本，`VERSION` 只作一致性校验；不改版本、App 更新渠道或实测数据。首屏、教程、最终获取按钮原已指向版本化 Release 页，本轮将校验值链接也统一到该页的 `SHA256SUMS`，停生成站内 `SHA256SUMS`。

原 `sop.site_build` 仍使用 `~/Dev/.venv/bin/python scripts/build-site.py`。构建先清理 `dist/site` 再生成完整站点，没有复制安装包的步骤；重建后安装包、备用 `downloads/` 目录、站内校验值文件均为零。站点保留真实 `release.json` 和 `site-manifest.json`，图片、教程视频、字幕和文字版继续沿用。

源 `dist/releases/` 中的 ZIP/DMG 等发行原件未删除；构建前后逐文件 SHA256 核对一致。`site/media/`、`perf/release.json`、`perf/lightweight.json` 和 `VERSION` 同样逐字节未变。本轮没有重建、安装或公证 App，没有重录素材，没有改变源码公开范围。

## 必要检查结果

- `apps-portal show mackit --json`：只读回本产品登记，`download` 与生成的 Release URL 一致；未改 configs、Portal、Lintel 或共享源码。
- 按原登记入口重建成功。
- 回归检查：五个获取/校验链接均为对应版本 Release 页，无站内安装包链接；遍历产物无安装包，旧下载目录与校验值文件不存在。
- GitHub 官方 API 回读：Release 已公开、非草稿，repo/tag 与页面一致；四个发行资产的名字、字节数、digest 和实际下载 URL 均与原 `perf/release.json` 一致。
- GitHub 已有 `SHA256SUMS` 只读下载到内存：自身 SHA256 与 API digest 一致，其中四条资产校验值与原发行记录一致；未保存或镜像安装包。
- SHA256 清单：覆盖 14 个公开文件（清单自身除外），文件集合与全部摘要逐项通过；`dist/site/release.json` 与原发行记录一致。
- Lintel v37 `--site apps --product mackit --bundle ...`：`ready:true`、`errors:0`、`issues:[]`，首页与快捷键附属页都覆盖。
- 自有域名的正确入口 `--site mackit --product mackit --out ...`：`ready:true`、总 issues 为空，两页 `ok:true`，warnings 为空。
- `git diff --check` 通过。只有链接与生成元数据变化，沿用已有页面/媒体证据，本轮没有重做视觉或播放验收。

复现（不发布）：

```sh
cd /Users/tianli/Apps/mackit && /Users/tianli/Dev/.venv/bin/python scripts/build-site.py
/Users/tianli/Dev/.venv/bin/python /Users/tianli/Apps/lintel/engine/lintel.py site check --site apps --product mackit --bundle /Users/tianli/Apps/mackit/dist/site --json
/Users/tianli/Dev/.venv/bin/python /Users/tianli/Apps/lintel/engine/lintel.py site check --site mackit --product mackit --out /Users/tianli/Apps/mackit/dist/site --json
```

## 剩余范围与接续

本产品本轮检查没有剩余错误。自有域名请用 `--out`；误用 `--bundle` 会走 Portal 专用分支并报 `KeyError: 'cli'`，本轮已沿正确入口通过，没有改共享接口。Portal 整站集成、私密内容闸和最终发布属于主会话；本产品未运行整站构建或 `ship`，不能将上述本地通过写成已上线。

保留其他会话的 `perf/acceptance/`、`perf/delivery-evidence.json`、`perf/install-receipt-0.3.6.json` 未跟踪产物，不纳入提交。Chapter 的 `pid 48230 / chapter-task:a2132e951bf54839a0076bdff3b6a54e` 声明由派出者收尾释放，本会话未另开同范围声明、未释放该声明。
