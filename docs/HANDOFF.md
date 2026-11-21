# Cojam 交接摘要

最近更新：2026-11-21。

## 2.8.9 macOS 适配

本版本为 Mac 下载包提供桌面构建脚本和本机项目目录选择器，补充常用桌面 Agent 发现及 Mac 更新包校验。Windows 同步打包发布。使用说明见 [MACOS.md](MACOS.md)。


## Cojam 2.8.7 发布记录（新官网与 GitHub Release 已同步）

- **发布完成**：已在 GitHub 仓库 [`lugen4570-hash/Cojam`](https://github.com/lugen4570-hash/Cojam/releases/tag/v2.8.7) 发布正式 Release `v2.8.7`，并同步官网 `https://lugen4570-hash.github.io/Cojam/`。
- **发布附件与校验**：
  - `Cojam-Setup-2.8.7.exe`（`13318098` 字节，`092c32e335bbfc8005af9157f077df0d942b8e00bfabf387094f19bde802c89d`）
  - `Cojam-Desktop-2.8.7-win64.zip`（`15827327` 字节，`02df404b967abb6fe07a396131c8b103612bb90437990123bb66a278d59664c1`）
  - `Cojam-2.8.7-win64.zip`（`12960349` 字节，`ba2ad440d846fc842e3b1ced4e4e18ff46e12fd01bb8af0ea8c367c5cacc32d5`）
  - `Cojam-Member-2.8.7.zip`（`211586` 字节，`d6d8a8c92e3a5e367a94665e7c9b6036276b736bbe9e383a7c75b2137f1a779a`）
  - `Cojam-Portable-2.8.7.exe`（`13222934` 字节，`42be6c6ff60b7b823c7b5cb7da7fab9bfd10618e53487756e1f182c368627368`）
  - `SHA256SUMS-2.8.7.txt`（`457` 字节）
  - `build-report-2.8.7.json`（`3973` 字节）
- **官网同步**：官网首页下载链接与 `website/update.json` 均已更新为 2.8.7，部署工作流自动拉取 Release 附件并校验大小与 SHA-256。

## macOS Python 浏览器分发包（2026-11-19）

已制作 `dist/macOS/Cojam-2.8.7-macOS-Python.zip`，556,850 字节，SHA-256 `d389dd3accf327f5df067c0252e96f958f114604d1b0ab2204ac59e538803a09`，干净 Git 源码提交为 `f2bb75bdc548009c30e4f9726d6f4784ac506356`。它是完整会议室的浏览器版，需要接收方先安装 Python 3.11+，不包含 Python 运行时，也不是独立 Tauri `.app`。压缩包内有可执行的“启动合拍.command”，数据默认保存在 `~/Library/Application Support/Cojam/`，没有包含本机预设改动、会议数据或凭据。

新增可重复的 Git 对象打包脚本、接收方说明和真实载荷测试；验证了 ZIP 及逐文件哈希、Unix 可执行权限/LF、嵌套成员包、构建确定性及本地改动隔离。解包后在 Windows 上实际启动 Python 后台，验证前端/成员包资源和停止流程，Mac 硬件/Finder/浏览器流程尚未测试；不能把这些宿主机检查称为 Mac 实机验证。SHA 和报告与 ZIP 同放 `dist/macOS/`。现有 `build_macos.sh` 已补齐 catalog、成员包生成和必要隐藏导入，独立应用仍须在 Mac 上编译验收。用法及边界见 [MACOS.md](MACOS.md)。

## 本轮接手状态（2.8.7 Tauri 本地验收通过，远端未发布）

用户已安装 MSVC/SDK，Codex 在隔离分支 `chore/phase1a-tauri-2.8.7` 完成正式 Tauri 壳编译，并合入主分支 `b26ca64` 的模型显示、Agent 隔离及更新器改动。Rust 8 项、全量回归 481 项及原生选择器/下载/刷新保活/关闭确认/错误后台拒绝验证通过；2.8.5、2.8.6 升级、重装、运行中安装/卸载保护、卸载保数据以及生产更新辅助脚本关窗安装重启均已实测通过。修复了 HTTP 错误误判空闲、原生标题随会话名改变影响更新、重命名无法可靠识别运行中映像三处问题。完整结果与验证边界见 [TAURI_MIGRATION.md](TAURI_MIGRATION.md)。

`dist/Cojam-Setup-2.8.7.exe` 为 13,318,098 字节，SHA-256 `092c32e335bbfc8005af9157f077df0d942b8e00bfabf387094f19bde802c89d`；桌面 ZIP 为 15,827,327 字节，SHA-256 `02df404b967abb6fe07a396131c8b103612bb90437990123bb66a278d59664c1`。便携/浏览器/成员包、完整 SHA256SUMS 与构建报告同步生成，仍为未签名构建；旧版产物不覆盖。

源码和验证文档提交 `403a7ad1f12917377da48c8ca7b4dcb95a1fb943` 已 fast-forward 合入本地 main。7 个待发布附件、测试安装器和当前原始 EXE/目录核心已复制到主工作区 dist，并独立核验 5 个二进制附件及 1031 项运行库文件；先前同名的本地 pywebview 构建备份到 `dist/_archive/2.8.7-before-tauri-1795091373/`，未改动旧版正式附件。`build-report-2.8.7.json` SHA-256 为 `38a637a9257ca26ad04ac2f7a595131737b9e6bd462b1c80180fd0d0416fa98f`，记录源码工作树洁净、完整验证结果与未签名状态。主工作区原有 opencode 预设差异在合并前后逐字节一致。

2026-11-19 实际执行 `git push origin main` 再次被拒绝，远端仍返回 `ERROR: Your account is suspended`。因此源码与本轮收尾记录尚未推至 GitHub，Release/Pages/线上哈希核验均未完成；不能报告完整“推”已完成。

GitHub 账号 suspended 仍阻止源码推送、Release、Pages 与线上下载核对，所以完整“推”尚未完成。没有提前将官网清单改成尚无 Release 的 2.8.7。账号恢复后沿用已有授权完成源码推送、附件发布与大小/哈希核验，再更新官网和实际下载校验，最后提交并推送收尾记录。主工作区的本地预设修改及会议数据保留。

## 本轮收尾状态（2026-11-18 · 2.8.6）

- **本地交付已完成，远端“推”受 GitHub 账户封禁阻塞：** 2.8.6 源码、版本号、Inno Setup 目录化升级脚本、Windows 核心程序（`--onedir` 与便携 `--onefile`）、桌面壳、安装包、便携版、成员连接端、`dist/SHA256SUMS-2.8.6.txt`、`dist/build-report-2.8.6.json` 与官网页面清单（`website/index.html`、`website/update.json`）均已在本地完成构建、全套验证与提交，并合入本地 `main`；但 GitHub 账户 `JUN-Genyan` 当前处于被封禁状态（`git ls-remote origin HEAD` 返回 `ERROR: Your account is suspended. Please visit https://support.github.com for more information.`，`gh auth status` 提示 keyring 令牌失效，仓库页面与 `https://jun-genyan.github.io/Cojam/` 均返回 `HTTP/1.1 404 Not Found`）。**以下远端步骤尚未完成：** `git push` 至 `origin/main`、发布 GitHub Release `v2.8.6` 并核对上传附件、触发/等待 GitHub Pages 部署、核验线上下载文件。待账户解封后，直接推送本地 `main`、上传 `dist/` 下 7 个 `2.8.6` Release 附件并核对 Pages 部署即可完成完整“推”闭环。
- **提交定位：** 2.8.6 源码、版本号、打包脚本、测试与 `INSTALLER.md` 提交 `74116d95a42af083b3552ad12d930c60b700331a`；官网下载链接与 `website/update.json` 同步提交 `b824c17619604e608d7580f1d150c2a65aef4369`；构建自洁净隔离工作树分支 `chore/release-2.8.6-onedir`，未包含主工作区既有未提交改动（v2.8.5 及更早发布产物保持未改动）。
- **功能与打包改动：** 安装版与桌面 ZIP 中的后台核心 `CojamCore.exe` 从 PyInstaller `--onefile` 切换为平铺目录模式 `--onedir`（安装目录保持 `Cojam.exe` + `CojamCore.exe` + `_internal/` + `data/`），保留原有 `--APPDIR` 与应用内更新路径契约；便携单文件 EXE（`Cojam-Portable-2.8.6.exe`）、浏览器 ZIP（`Cojam-2.8.6-win64.zip`）与成员连接端（`Cojam-Member-2.8.6.zip`）保持不变。更新 `packaging/cojam-desktop.iss`：`PrepareToInstall` 检测 `{app}\Cojam.exe`、`{app}\CojamCore.exe` 与 `{app}\_internal\python3*.dll` 是否处于运行占用状态（最多等待 8 秒，仍被占用则中止安装并不触碰旧 `_internal` 与 `data`），确认空闲后通过 `[InstallDelete]` 清理旧 `{app}\_internal`，卸载时通过 `[UninstallDelete]` 清理 `{app}\_internal`，全程不触碰 `{app}\data`。`sign_exe.ps1` 补充 `-ExePath` 参数供桌面壳、单文件与目录核心复用。按既定实施顺序与工具链边界（先完成目录化核心与升级保留验证，再做 Tauri 2 桌面壳；且本机无 `cargo`/`rustc`/MSVC、GitHub Actions 亦因账户封禁不可用），本轮不包含 Tauri 桌面壳构建。
- **验证与构建记录：** 安装包重编译后执行 `python tests/test_headless.py`（8 项通过）与 `.test-tmp/verify_rel286.py`（全项通过）；补齐 `docs/INSTALLER.md` 后运行 `node --check static/connections.js`、`python -m mypy bridge`（39 文件）、`python -m ruff check bridge tests/test_headless.py packaging/build_release.py` 均通过，全量 `python tests/run_all.py` 41 个模块（473 项测试）中 38 个模块通过（包含 `test_headless.py`），仅存在 3 项源自历史提交 `1026a8e` 的既有提示词模板失败（`test_acp.py::test_room_retries_lost_acp_session_with_full_first_prompt`、`test_workdir.py::test_other_folder_prompt_and_cmd`、`test_wrapup.py::test_rules_change_resent`），与本轮改动无关。
- **包内、启停与升级保数据验证：** 通过 `.test-tmp/verify_rel286.py` 在隔离端口（`18765`/`18766`/`18767`）与独立 `TEST_BUILD` 安装程序（`Cojam-Setup-2.8.6-test.exe`）下完成实测：39 项内嵌前端及预设资源与源码逐字节一致且不含已删 `sw.js`；3 个发布 ZIP 完整性通过且不含私人数据，`Cojam-Desktop-2.8.6-win64.zip` 含 1031 项 `_internal/` 文件并与 `dist/CojamCore/_internal` 逐项 SHA-256 一致，`Cojam-Member-2.8.6.zip` 含 56 项源码及预设；`CojamCore.exe`（`--onedir`）与 `Cojam-Portable-2.8.6.exe`（`--onefile`）隔离端口启停均通过，`/api/server/info` 返回 `version: 2.8.6`、`api_revision: 3` 且服务静态 JS 与源码一致；从真实 `2.8.5` 桌面包写入会议（`2026-11-18_2133_Pre-Upgrade_Meeting`、5 条消息）、`data\sentinel.txt` 与 `data\devices.json` 后静默升级至 `2.8.6`，升级后文件 SHA-256 全数一致，升级后的桌面版 `Cojam.exe` 启动成功、可读回旧会话并通过 `WM_CLOSE` 正常退出；同版覆盖重装清理 `_internal\stale_from_prev.txt`；运行中 `CojamCore.exe` 触发安装安全中止且保护 `_internal\keep_if_aborted.txt` 与 `data` 不被改写；静默卸载移除程序与 `_internal`、保留全部 `data` 并清理 `TEST_BUILD` 卸载注册项。全程未干扰 `8765` 端口正在运行的合拍会议实例。
- **待发布 2.8.6 产物（位于本地 `dist/`，未签名）：** `Cojam-Setup-2.8.6.exe`（`26707665` 字节，`da139b6053277cabd4de2d23312425e16baca791efb14ad9c6719e597b43ad3a`）、`Cojam-Desktop-2.8.6-win64.zip`（`30091126` 字节，`b8cdaba1b77baca543103d29d33f3cc07473768adcd4355feeed9c28addf49c2`）、`Cojam-2.8.6-win64.zip`（`12951813` 字节，`d213e9d78723a11cb7088fb3886ffcbc60b565b7b589b6d121c145fd2a58f238`）、`Cojam-Member-2.8.6.zip`（`209713` 字节，`99bdfcc2741592f227ba14735c1a3ed776631028c4533052e8d2de9317f5b97b`）、`Cojam-Portable-2.8.6.exe`（`13214636` 字节，`2c786d76c610e7b0ed3345059006df5260cde3a62c8794e69660859624768ada`）、`SHA256SUMS-2.8.6.txt`（`457` 字节，`6b0a6b6f46c5f0beb2eb45b1afa0d7eae8cdeb4f655f4e599f5358d686443568`）、`build-report-2.8.6.json`（`2003` 字节，`ace13049c1ddae8c1614323c13d6edaf07f148160ab11ad8338478607a561df2`）；另有验证安装包 `Cojam-Setup-2.8.6-test.exe`（`26707657` 字节，`51edaabc856327f708b988a45d9fad627c9af582970aad64e5cedaba57072080`）。
- **保留的本地内容：** 主工作区既有未提交改动（`bridge/presets/opencode.json`、`bridge/updater.py`、`docs/UI_INTERACTIONS.md`、`index.html`、`static/model-settings.js`、`static/studio.css`、`static/update.js`、`tests/test_model_settings.py`、`tests/test_update_ui.py`、`tests/test_updater.py`）与 `.agents/`、`CODE_REVIEW_REPORT.md`、`reports/`、`research_notes/`、`dist/`、`.test-tmp/` 保留在本地工作区，未纳入提交或发行包。

## 本轮历史状态（2.8.5）

- **交付已完成：** 2.8.5 源码、Windows 核心程序、桌面壳、安装包、便携版、成员连接端、GitHub Release [`v2.8.5`](https://github.com/JUN-Genyan/Cojam/releases/tag/v2.8.5) 与官网均已同步。官网部署 [44233488873](https://github.com/JUN-Genyan/Cojam/actions/runs/44233488873) 成功；线上首页及 `update.json` 均为 2.8.5。
- **实际下载已核验：** 官网安装包 `Cojam-Setup-2.8.5.exe` 为 `31665906` 字节，SHA-256 `14dd8f6b7362d5e0542a316cd8429a609f78d7488f368a0e5911ce027eb4a2db`；官网便携 EXE `Cojam-Portable-2.8.5.exe` 为 `13214881` 字节，SHA-256 `d7facb3321061b7d71ffc5f3ebcf4137e15a455bb574ab96b64d71def6cdb2ff`。均通过完整字节读取与 SHA-256 核对，与本地 `dist/` 及 GitHub Release 7 个附件一致（未签名；v2.8.2、v2.8.3、v2.8.4 既有附件未改动）。
- **提交定位：** 2.8.5 源码、版本号、测试与交互文档提交 `242669f20dc4e2ca5c455ea1c4b384cba130987c`（也是 `v2.8.5` 构建来源与标签），构建自干净 Git 归档（`bridge/presets/opencode.json` 仅纳入 `"models": []` 改动，保留既有未提交的 `"base": ["run"]` 本地差异）；官网首页与更新清单同步提交 `be41f6bd2d5b2fe55297b425351303f80c8b8a4e`。
- **功能内容：** 清理各 Agent 预设及内置 `claude` 中硬编码或虚构的模型列表；Antigravity（`agy models`）与 Cursor（`cursor-agent --list-models`）自动折叠 `<model>-<effort>[-fast]` 变体为基础模型、按模型分别统计 `efforts_by_model` 并生成清理零宽字符与后缀的可读展示名（下拉框展示 `可读名称 · model_id`），CLI 调用时由 `_resolve_cli_model_effort()` 自动适配回各工具所需参数格式；OpenCode 解析 `opencode.json`/`opencode.jsonc` 并按已配置 Provider 过滤未配置的 `opencode/*`（覆盖 CLI 与 ACP）；补齐 Grok（`models_cache.json` + `grok models`）、Qoder CLI（25s 超时、解析 `MODEL` 表头并兼容非零退出）与 Claude 本机配置读取；稳定化 `model_catalog._key()`（`v: 2`）并与 Agent 设置页复用实时目录。细节见 [UI_INTERACTIONS.md](UI_INTERACTIONS.md)。
- **验证与构建记录：** `mypy bridge` 39 文件无误，`ruff` 通过，`node --check static/model-settings.js` 与 `static/connections.js` 通过；版本号递增后 10 组专项回归全过共 174 项（`test_model_catalog.py` 11 项、`test_model_settings.py` 2 项、`test_agents_registry.py` 43 项、`test_agent_settings.py` 14 项、`test_agent_parity_and_sidebar.py` 15 项、`test_rt.py` 11 项、`test_desktop_shell.py` 37 项、`test_frontend_runtime.py` 29 项、`test_updater.py` 10 项、`test_update_ui.py` 2 项）。此前全量 `run_all.py` 38/41 模块通过，3 项既有提示词模板失败（`test_acp.py`、`test_workdir.py`、`test_wrapup.py`）源自历史提交 `1026a8e`，与本轮无关。
- **包内与安装验证：** 干净归档构建产物 `Cojam.exe` 39 项资源逐字节核验一致且不含已删 `sw.js`；ZIP 校验通过且不含私有数据，成员包内 56 项源码及预设与归档一致；封装 `Cojam.exe` 隔离端口启停通过并核验 `/api/server/info` 返回 `version: 2.8.5`、`api_revision: 3` 及 6 个静态 JS 与源码一致；独立 `TEST_BUILD` 静默安装、保留 `data\sentinel.txt` 与 `data\devices.json` 覆盖重装、卸载保留数据并清理测试注册项均通过。本地校验记录包括 `dist/build-report-2.8.5.json`、`dist/SHA256SUMS-2.8.5.txt`、`.test-tmp/release285-online-validation.json`。
- **保留的本地内容：** `bridge/presets/opencode.json`（未暂存的 `"base": ["run"]` 改动）、`.agents/`、`CODE_REVIEW_REPORT.md`、`reports/`、`research_notes/`、`dist/`、`.test-tmp/` 保留在本地工作区，未纳入提交或发行包。

## 2026-11-18 · Cojam 2.8.5 发布记录

- 已发布 [v2.8.5](https://github.com/JUN-Genyan/Cojam/releases/tag/v2.8.5)，构建源码提交为 `242669f20dc4e2ca5c455ea1c4b384cba130987c`。
- 7 个 Release 附件大小与 SHA-256：`Cojam-Setup-2.8.5.exe`（`31665906` 字节，`14dd8f6b7362d5e0542a316cd8429a609f78d7488f368a0e5911ce027eb4a2db`）、`Cojam-Desktop-2.8.5-win64.zip`（`29828451` 字节，`6c9b3aaaa02f1d8638583e5729cab20ee2d9900302c3dd643109568133bfab7e`）、`Cojam-2.8.5-win64.zip`（`12952322` 字节，`c63acd393b10176b0ace442e3229bed249b466531363665f3910fa76b0efd74a`）、`Cojam-Member-2.8.5.zip`（`209713` 字节，`e04fcf9857c6e82656a23adcd1505ebb9c2ee051d767d88059d119d616e0a21f`）、`Cojam-Portable-2.8.5.exe`（`13214881` 字节，`d7facb3321061b7d71ffc5f3ebcf4137e15a455bb574ab96b64d71def6cdb2ff`）、`SHA256SUMS-2.8.5.txt`（`457` 字节，`d63060e2066db984ad19276b4bdcf48825281d2dcd8e0505aa1f88ce0dea2c2a`）、`build-report-2.8.5.json`（`1717` 字节，`89253f2f67ea3d9ee08eaaaa3975b3a3acbd9f161d0c7f7737781d12e7b3ff31`）。

## 本轮历史状态（2.8.4）

- **交付已完成：** 2.8.4 源码、Windows 核心程序、桌面壳、安装包、便携版、成员连接端、GitHub Release [`v2.8.4`](https://github.com/JUN-Genyan/Cojam/releases/tag/v2.8.4) 与官网均已同步。官网部署 [43872342079](https://github.com/JUN-Genyan/Cojam/actions/runs/43872342079) 成功；线上首页及 `update.json` 均为 2.8.4。
- **实际下载已核验：** 官网安装包 `Cojam-Setup-2.8.4.exe` 为 `31646924` 字节，SHA-256 `9d8068f7f67043f09a823d44a3f4b8886b2a22ca351e7dcc5885a90dac319fbb`；官网便携 EXE `Cojam-Portable-2.8.4.exe` 为 `13196961` 字节，SHA-256 `68e995c78a0e59b33a61672f6ba7cf92b6fd1a1441491c27c484d9600edfd912`。均通过完整字节读取与 SHA-256 核对，与本地 `dist/` 及 GitHub Release 7 个附件一致（未签名；v2.8.2、v2.8.3 既有附件未改动）。
- **提交定位：** 2.8.4 源码、版本号、测试与交互文档提交 `408d23019e550b79a935cd2b8a15f41a77edb6d9`（也是 `v2.8.4` 构建来源与标签），构建自干净 Git 归档，排除本地未提交的 `bridge/presets/opencode.json` 及本地过程文件；官网首页与更新清单同步提交 `42e69773355d4d404143357847beaa52f8a9d142`。
- **功能内容：** 桌面端左侧栏关闭/收起改为平滑向左滑入收起并将桌面呼出按钮收拢为左边缘固定细把手（配合 `inert` 禁用收起态键盘焦点，不再在顶部保留丑 `×` 或占位的 `☰`）；将顶部成员状态条 `#caps` 从更多菜单 `#bar` 中拆出直挂顶栏，使会话管理操作与成员状态清晰分离；将 `openAgents()` 与连接授权弹窗 `connections.js` 的 6 项细分权限整合为 3 项核心权限（参与对话、看板与附件、允许干活），无损映射至后端 6 项布尔值，并新增一键全开/全关及按组批量开关功能。细节见 [UI_INTERACTIONS.md](UI_INTERACTIONS.md)。
- **验证与构建记录：** `mypy bridge` 39 文件无误，`ruff` 通过，`node --check` 语法检查通过；版本号递增后专项复跑全过（`test_agent_parity_and_sidebar.py` 15 项、`test_agent_settings.py` 14 项、`test_meeting_navigation.py` 2 项、`test_simplified_frontend.py` 2 项、`test_frontend_runtime.py` 29 项、`test_contacts_access.py` 15 项、`test_invites.py` 17 项、`test_icons.py` 2 项、`test_desktop_shell.py` 37 项）。
- **包内与安装验证：** 干净归档构建产物 `Cojam.exe` 39 项资源逐字节核验一致且不含已删 PWA 文件；`bridge.pal`、版本 `2.8.4`、`text_select` 与 `ALLOW_DOWNLOADS` 均已打入；ZIP 校验通过且无私有数据；封装 `Cojam.exe` 隔离端口启停通过；独立 `TEST_BUILD` 静默安装、保留 `data\sentinel.txt` 重装、卸载保留数据并清理测试注册项均通过。本地校验记录包括 `dist/build-report-2.8.4.json`、`dist/SHA256SUMS-2.8.4.txt`、`.test-tmp/release284-online-validation.json`。
- **保留的本地内容：** `bridge/presets/opencode.json`、`.agents/`、`CODE_REVIEW_REPORT.md`、`reports/`、`research_notes/`、`dist/`、`.test-tmp/` 保留在本地工作区，未纳入提交或发行包。

## 2026-11-16 · Cojam 2.8.4 发布记录

- 已发布 [v2.8.4](https://github.com/JUN-Genyan/Cojam/releases/tag/v2.8.4)，构建源码提交为 `408d23019e550b79a935cd2b8a15f41a77edb6d9`。
- 7 个 Release 附件大小与 SHA-256：`Cojam-Setup-2.8.4.exe`（`31646924` 字节，`9d8068f7f67043f09a823d44a3f4b8886b2a22ca351e7dcc5885a90dac319fbb`）、`Cojam-Desktop-2.8.4-win64.zip`（`29809849` 字节，`42db4d49ecb12967a9ca84d9f472ad2854c84bce3d93f447da880787d180184`）、`Cojam-2.8.4-win64.zip`（`12934502` 字节，`61ba763c34d8f1615f0b888743f80dec53656eed5e204e364cebabbee7e638bd`）、`Cojam-Member-2.8.4.zip`（`204971` 字节，`c3683e213e40727071459c9159b43e800968e27c948e14f71de531d10f23024e`）、`Cojam-Portable-2.8.4.exe`（`13196961` 字节，`68e995c78a0e59b33a61672f6ba7cf92b6fd1a1441491c27c484d9600edfd912`）、`SHA256SUMS-2.8.4.txt`、`build-report-2.8.4.json`。

## 本轮历史状态（2.8.3）

- **交付已完成：** 2.8.3 源码、Windows 核心程序、桌面壳、安装包、便携版、成员连接端、GitHub Release [`v2.8.3`](https://github.com/JUN-Genyan/Cojam/releases/tag/v2.8.3) 与官网均已同步。官网部署 [43788949427](https://github.com/JUN-Genyan/Cojam/actions/runs/43788949427) 成功；线上首页及 `update.json` 均为 2.8.3。
- **实际下载已核验：** 官网安装包 `Cojam-Setup-2.8.3.exe` 为 `31644493` 字节，SHA-256 `408b635fceea681ccd566eaee7e379488b33b4219440e7e86b7e36f5032e6df5`；官网便携 EXE `Cojam-Portable-2.8.3.exe` 为 `13194939` 字节，SHA-256 `d8e8c9f09f8734fc015143fd1ebabb90dc51251e07b8b8092a6378dc5b1d191f`。均完整读取字节并核对与本地 `dist/` 及 GitHub Release 7 个附件一致（未签名；v2.8.2 既有附件未改动）。
- **提交定位：** 2.8.3 源码、版本号、测试与交互文档提交 `3e18f5883fde72d2823538a2755579faf95ec658`（也是 `v2.8.3` 构建来源与标签），构建自干净 Git 归档，排除本地未提交的 `bridge/presets/opencode.json` 及本地过程文件；官网首页与更新清单同步提交 `999b457`。
- **功能内容：** 彻底移除网页端 PWA（删除 `manifest.webmanifest`、`sw.js`、`offline.html` 及 512px 图标并保留启动时历史 SW/Cache 清理）；支持桌面端（≥ 850px）左侧栏收起/展开及 `localStorage` 持久化；为 `cli`/`acp`/`http`/`external` 对齐真实上下文 token 解析（无返回时不估算）、模型与思考强度切换（`http`/`external` 默认开放、`aider` 补充 `--model`、ACP 自动缓存与部分 CLI 实时查询、刷新后立即重绘控件）以及全 Agent 上下文压缩（含 `context="full"` 与无状态连接摘要检查点）。细节见 [UI_INTERACTIONS.md](UI_INTERACTIONS.md)。
- **验证与构建记录：** `mypy bridge` 39 文件无误，`ruff` 通过；版本号递增后专项复跑通过（`test_agent_parity_and_sidebar.py` 13 项、`test_icons.py` 2 项、`test_compact.py` 5 项、`test_model_settings.py` 2 项、`test_meeting_navigation.py` 2 项、`test_model_catalog.py` 8 项、`test_frontend_runtime.py` 29 项、`test_desktop_shell.py` 37 项、`test_updater.py` 10 项、`test_update_ui.py` 2 项、`test_pal.py` 14 项、`test_logging_and_errors.py` 8 项、`test_atomic_json.py` 2 项、`test_board.py` 6 项、`test_send_file.py` 15 项、`test_stop_quote.py` 5 项）。此前全量 `run_all.py` 38/41 模块通过，3 项既有失败（`test_acp.py::test_room_retries_lost_acp_session_with_full_first_prompt`、`test_workdir.py::test_other_folder_prompt_and_cmd`、`test_wrapup.py::test_rules_change_resent`）源自此前 `1026a8e` 对 `build_prompt` 的条件化调整，与本次变更无关。
- **包内与安装验证：** `Cojam.exe` 39 项洁净资源逐字节核验一致且不含已删 PWA 文件；`bridge.pal`、版本 `2.8.3`、`text_select` 与 `ALLOW_DOWNLOADS` 均已打入；ZIP 校验通过且无私有数据；封装 `Cojam.exe` 隔离端口启停及 404 检查通过；独立 `TEST_BUILD` 安装、保留 `data\sentinel.txt` 重装、卸载保留数据并清理测试注册项均通过。本地校验与附件包括 `dist/build-report-2.8.3.json`、`dist/SHA256SUMS-2.8.3.txt`、`.test-tmp/release283-online-validation.json`。
- **保留的本地内容：** `bridge/presets/opencode.json`、`.agents/`、`CODE_REVIEW_REPORT.md`、`reports/`、`research_notes/`、`dist/`、`.test-tmp/` 保留在本地工作区，未纳入提交或发行包。

## 2026-11-16 · Cojam 2.8.3 发布记录

- 已发布 [v2.8.3](https://github.com/JUN-Genyan/Cojam/releases/tag/v2.8.3)，构建源码提交为 `3e18f5883fde72d2823538a2755579faf95ec658`。
- 7 个 Release 附件大小与 SHA-256：`Cojam-Setup-2.8.3.exe`（`31644493` 字节，`408b635fceea681ccd566eaee7e379488b33b4219440e7e86b7e36f5032e6df5`）、`Cojam-Desktop-2.8.3-win64.zip`（`29806956` 字节，`0f8598c057b6573e8c5c4136b6d76508a15dc80556deaf57eef075299307a8a9`）、`Cojam-2.8.3-win64.zip`（`12931626` 字节，`43f10e85212db601e3b3cdab463244aad3ee31e5b56fa69a1ce2fa96972b0802`）、`Cojam-Member-2.8.3.zip`（`204971` 字节，`c5a580c8241b8253dc1387935da4cda61236b5413b84b64c98a6f0fb878047ba`）、`Cojam-Portable-2.8.3.exe`（`13194939` 字节，`d8e8c9f09f8734fc015143fd1ebabb90dc51251e07b8b8092a6378dc5b1d191f`）、`SHA256SUMS-2.8.3.txt`、`build-report-2.8.3.json`。

## 本轮历史状态（2.8.2）

- **交付已完成：** 2.8.2 源码、Windows 安装包、便携版、成员连接端、GitHub Release 与官网已同步。官网部署 [43710202702](https://github.com/JUN-Genyan/Cojam/actions/runs/43710202702) 成功；线上首页及更新清单均为 2.8.2。
- **实际下载已核验：** 官网安装包 `32208556` 字节，SHA-256 `29617c1880fe545f2348d91f61fd256b2767bfba5171a791be2e7a20add50728`；官网便携 EXE `13497658` 字节，SHA-256 `428e1d9d1d1af589616bc089c5eb06e4fd7a76eb0f44d96350457b105a280c67`。均读取全部字节验证，与本地发布包及 GitHub 附件一致。
- **提交定位：** 功能修复 `1026a8e`；版本与工作区记忆 `e492e8b`（也是 v2.8.2 构建来源与标签）；官网及发布记录 `2d14425`。收尾前 `main` 与远端一致，发布源码来自干净 Git 归档。
- **用户工作约定：** `AGENTS.md` 已记录“推 = 提交 GitHub + 打包 + Release + 官网 + 线上一致性验证”，默认一次完成全部环节，无需再询问是否继续打包或更新官网。
- **功能细节：** 见 [UI_INTERACTIONS.md](UI_INTERACTIONS.md) 与 [Agent / 会话简化计划](superpowers/plans/2026-11-15-agent-and-session-simplicity.md)。包含附件预览、桌面下载、弹窗拖动修复、系统指令分离、单一高级设置入口、当前会话直接删除和联系人关联自动清理。
- **验证材料：** 发布附件包含 `dist/build-report-2.8.2.json`、`dist/SHA256SUMS-2.8.2.txt`。线上校验记录在 `.test-tmp/release282-online-validation.json`；资源与安装记录在 `.test-tmp/release282-resource-validation.json`、`.test-tmp/release282-install-validation.json`。真实浏览器截图在 `.test-tmp/ui-bugs-*`、`.test-tmp/simplicity-*`。测试材料和临时产物保留本地，不进入源码仓库。
- **保留的本地内容：** `bridge/presets/opencode.json` 是既有未提交修改，本轮未提交、未混入发行包；`.agents/`、`CODE_REVIEW_REPORT.md`、`reports/`、`research_notes/` 仍留在本地。不要误认为这些文件属于尚未完成的发布。
- **运行边界：** 发布过程中没有重启或替换用户正在运行的会议室，没有迁移数据目录。实际正在使用的客户端是否升级，应单独核实；源码后台会缓存启动时的界面资源，更新源码后需要正常重启才能生效。
- **后续：** 本轮请求没有遗留的功能或发布步骤；收尾交接记录已纳入本轮提交与推送。工作区约定已补充：“推”包含最终验证结果的落盘与提交，不能遗留仅在本地的收尾摘要。后续修改另行验证，下一次“推”按工作区约定完整发布，不能覆盖 2.8.2 的既有附件。

## 2026-11-15 · Cojam 2.8.2 发布与工作约定

- 工作区根目录 `AGENTS.md` 记录用户约定：“推”包含提交 GitHub、重新打包、发布 Release、更新官网并验证线上文件的完整流程，不仅是源码推送。
- 已发布 [v2.8.2](https://github.com/JUN-Genyan/Cojam/releases/tag/v2.8.2)，构建源提交为 `e492e8b6aa9b1f2e1cff88845ed74f59be886a49`。从干净的 Git 归档构建，排除用户无关的 OpenCode 本地修改。
- 包含 HTML / PDF / 文本附件预览、桌面下载恢复、弹窗拖动修复、CLI 系统指令分离、简洁 Agent 详情与高级设置入口，以及会话 / 联系人删除流程优化。
- 44 项包内资源与构建源码一致，桌面下载设置已进入新壳。独立安装、重复安装、原生窗口响应、正常退出、卸载保留测试数据与设备凭据通过。此前功能回归 167 项通过，干净源码发布检查 71 项及补充回归 84 项通过。
- GitHub 七个附件的大小与 SHA-256 均已核验；未签名。官网首页与更新清单同步到 2.8.2；安装包 `32208556` 字节，SHA-256 为 `29617c1880fe545f2348d91f61fd256b2767bfba5171a791be2e7a20add50728`。构建报告与校验文件随 Release 附件提供。

## 2026-11-14 · Cojam 2.8.1 发布

- 已发布 [v2.8.1](https://github.com/JUN-Genyan/Cojam/releases/tag/v2.8.1)，构建源码提交为 `961ec995dc1b63cb0c3b53e9559b8628bff4072b`，包含前述修复与前端模块拆分。旧版 2.8.0 附件保持原样。
- 发布附件包含 Windows 安装包、桌面 ZIP、浏览器便携 ZIP、单文件便携 EXE、成员连接端、`SHA256SUMS-2.8.1.txt` 与 `build-report-2.8.1.json`；七个附件的 GitHub 摘要及大小均与本地一致。构建未签名。
- 44 项包内资源与源码逐文件一致，平台兼容模块完整，打包服务实际提供六个拆分的前端文件，成员连接端源码与当前版本一致。
- 独立测试 AppId 下完成安装与重装，已安装载荷哈希一致；隐藏桌面窗口响应、正常关闭及后台退出、卸载后保留测试数据与设备凭据均通过，测试注册项已清除。发布版本相关的 71 项测试全部通过。
- 官网首页下载链接与 `website/update.json` 同步为 2.8.1。安装包大小为 `32199252` 字节，SHA-256 为 `8b132aca89224f7e893c22d87e16b44c03085e9efe7782caa0cb07dca7961989`；官网由 Pages 工作流从同名 Release 获取安装包和便携 EXE。

## 2026-11-14 源码同步

- 本次源码同步包含 ACP 与文件发送边界修复、会话生命周期及资源管理修复、平台兼容层 `bridge/pal/`、轮转日志、类型检查，以及 `index.html` 的 CSS / JavaScript 模块拆分。
- 同步 Agent 发现与预置更新，包含 Cursor、Qoder、Antigravity 及 Grok CLI；长提示词按预置通过标准输入或临时提示词文件传递，避免 Windows 命令行长度限制。
- 提交前回归发现并修复 Windows `taskkill` 返回非零状态时未回退 `proc.kill()` 的问题，避免子进程在超时后继续运行；补充成功、异常及非零返回状态的回归覆盖。
- 此次提交用于同步源码，版本仍为 `2.8.0`；GitHub Release 与官网安装包保持既有发布产物。最新源码尚需独立构建、安装验证并以新补丁版本发布。
- 本机 `dist/Cojam.exe` 与正式发布附件、当前源码均有差异，不应直接作为本次源码同步的发布产物。`data/`、`dist/`、本地审查与研究过程文件不纳入本次提交。
- 提交前验证：全量运行共 437 项测试，首轮 `test_live_gen.py` 与 `test_members.py` 失败，其余模块通过。修复上述进程终止问题后，`test_live_gen.py` 12 项通过；成员连接端首次出现回复数时序波动，独立重跑 `test_members.py` 19 项通过；新增回归后的 `test_pal.py` 14 项通过。`mypy bridge` 及项目既定范围 `ruff check bridge tests/test_pal.py tests/test_logging_and_errors.py` 均通过。全仓库 Ruff 扫描仍有示例、测试及本地协作脚本的未使用导入等告警，未在本次提交中扩展清理。

以下为 2026-11-13 的历史交接记录。

## 当前完成状态

- Agent 接入区分 CLI 直连与桌面 MCP 待命，通过真实心跳显示状态。程序位置、参数、默认模型 / effort、加入规则和权限均可在应用内编辑。
- 已修复桌面消息选字，补齐整条 / 片段复制与引用，并取消启动时自动弹出接入引导。
- 最新布局采用左侧导航、中央消息、按需打开的右侧详情抽屉。全局新建与会话管理归左侧；右上角只保留当前会议操作；联系人位于侧栏下方且默认收起。
- 当前会议详情与看板可正常打开，环境、上下文、工具和文件改动记录使用真实状态渲染。
- 详细行为与验证记录见 [UI_INTERACTIONS.md](UI_INTERACTIONS.md)、[AGENT_SETTINGS.md](AGENT_SETTINGS.md)、[AGENT_EXECUTION.md](AGENT_EXECUTION.md)。

## 代码与发行状态

- 功能与界面最新提交：`b3ef5c9`，已推送 `main`。
- 已公开发布 [v2.8.0](https://github.com/JUN-Genyan/Cojam/releases/tag/v2.8.0)，产物包含安装包、桌面 / 浏览器便携版、成员连接端及校验文件；当前为未签名构建。
- 官网与更新清单已指向 2.8.0，部署成功；从官网实际下载安装包并核对 SHA-256 一致。
- **已发布安装包不包含 b3ef5c9 的最后一轮全局导航分区调整。** 该调整已在源码运行的服务中生效。后续若打包发布，递增补丁版本，不覆盖既有 2.8.0 附件。

## 验证与截图

- 最后一轮：23 项前端、2 项会议导航、2 项模型设置测试通过；浏览器覆盖 390 / 768 / 1280 / 1600px，并实际执行新建、归档、删除、恢复和切换流程。
- 桌面消息拖选、复制回退和引用回归通过；2.8.0 已验证实际安装、隐藏桌面窗口响应、正常退出及卸载后保留数据。
- 最新截图来自运行中的服务，尺寸 1440×960：`.test-tmp/cojam-live-desktop.png`、`.test-tmp/cojam-live-desktop-details.png`。它们是网页内容截图，不包含原生桌面标题栏。
- 截图、浏览器验证脚本、构建报告及本机运行信息保留在忽略目录中，不上传会议内容或设备凭证。

## 后续工作

本轮请求已完成。当前没有待提交的功能修改；如继续分发最新导航布局，下一步是新补丁版本的打包、安装验证与发布。需要重启服务时，先核实实际数据目录，确认没有运行或排队任务，保留原目录及浏览器授权。
