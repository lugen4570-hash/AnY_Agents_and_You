# AnY 交接摘要

最近更新：2026-11-26。

## AnY 2.8.38 正式发布（2026-11-26）

- 本版包含 CLI 启动画面、欢迎面板和流式对话布局，GUI 侧栏、输入区和消息布局调整，以及公开 Agent 扫描名单扩充。GUI 账号行仍显示「本机用户」。官网设计稿保留在工作区，本次官网仅更新正式下载版本。
- 首次 2.8.37 构建发现 CLI 启动画面的类型及异常处理检查失败，未发布 Release。修复后递增至 2.8.38，发布源码为 `1d0073629ebb44bd7dfc247eefa64b0067849bc1`。Windows 全量回归、安装卸载数据保留、运行中安装保护、核心启动退出、双架构 macOS 构建与 Linux CLI 安装通过。[发布流程](https://github.com/lugen4570-hash/AnY_Agents_and_You/actions/runs/45764653651)
- 已下载 Release 全部 13 个附件并核对大小与 SHA-256，ZIP 完整性通过；实下载的 Windows 便携版和桌面核心完成启动、资源读取及退出验证，便携版与 MCP ZIP 完成认证调用。Windows 包未签名，Tauri 原生窗口交互及 Apple Silicon 实机启动仍待验收。[Release](https://github.com/lugen4570-hash/AnY_Agents_and_You/releases/tag/v2.8.38) · [构建报告](https://github.com/lugen4570-hash/AnY_Agents_and_You/releases/download/v2.8.38/build-report-2.8.38.json)
- 官网提交 `e0b44d0fae451ca040b6ca04bceaaed19f86fef5` 已通过 Pages 部署。更新清单、Windows 和 macOS 下载、MCP 包及 CLI 源码包已线上核验，文件大小与哈希一致。[Pages 部署](https://github.com/lugen4570-hash/AnY_Agents_and_You/actions/runs/45765749746) · [官网下载](https://lugen4570-hash.github.io/AnY_Agents_and_You/download.html)

## AnY 2.8.36 正式发布（2026-11-26）

- 「添加联系人 → 本机 Agent」和「通过 MCP 手动参与」已移除官网下载链接。官网首页与下载页继续提供 MCP 入口，支持提示词配置与 ZIP 下载；本机程序验证和 MCP 手动接入流程照常可用。[官网下载 MCP](https://lugen4570-hash.github.io/AnY_Agents_and_You/mcp.html)
- 源码标签 `v2.8.36` 对应 `bc36539083c4aa4146eeab04fcc09f04fde7e1a5`。Windows 静态检查、Rust 与 Python 回归、安装与卸载数据保留、运行中安装保护、核心启动退出、双架构 macOS 构建和 CLI 安装均通过。13 个 Release 附件已下载核对大小和 SHA-256，ZIP 完整性通过。实下载的 Windows 便携版与桌面核心已验证启动、联系人向导资源和退出，便携版与官网下载同版 MCP 包完成带联系人密钥的 `list_rooms` 验证。Windows 产物未签名。Tauri 窗口交互及 Apple Silicon 原生启动待真机验收。[发布流水线](https://github.com/lugen4570-hash/AnY_Agents_and_You/actions/runs/45744716345) · [Release](https://github.com/lugen4570-hash/AnY_Agents_and_You/releases/tag/v2.8.36)
- 官网提交 `05256bf41b4d9e391dd9b34666fef0f8fe9dcd88` 已部署，已核对首页、MCP 页面、更新与下载清单，实下载文件与 Release 一致，CLI 源码包与标签一致。MCP ZIP 为 24,806 字节，SHA-256 为 `9c2462eaca41485472ad36691148da045968431fbc19a06131a74c5a26cad225`。[Pages 部署](https://github.com/lugen4570-hash/AnY_Agents_and_You/actions/runs/45745905802) · [官网下载清单](https://lugen4570-hash.github.io/AnY_Agents_and_You/downloads/manifest.json)

## AnY 2.8.35 正式发布（2026-11-26）

- 官网首页和下载页新增「MCP」入口。用户可选择 Codex、Claude Code、Claude Desktop、Cursor 或其他 STDIO 客户端，复制提示词请 Harness 配置，也可下载 ZIP 参照样例手动安装。ZIP 内的 `any-mcp.pyz` 复用 AnY 的 STDIO 转发程序，需要 Python 3.11+ 与运行中的 AnY。接入凭据从 AnY 生成，在本机配置中填写。[MCP 下载页](https://lugen4570-hash.github.io/AnY_Agents_and_You/mcp.html)
- 「添加联系人 → 本机 Agent」移除根据已保存外部联系人生成的「配置 Devin」「配置 Qoder」等按钮，替换为统一 MCP 入口。「通过 MCP 手动参与」也提供同一个入口。浏览器验证了 320、390、768、1024、1440px 下的 MCP 页面、模式切换、复制和下载。独立 MCP 包已用真实 AnY 后端验证初始化、工具列表、会话可见权限和错误密钥拒绝。
- 发布源码为 `a333456e5b590a7bcfc06dd12a0819576daed618`。Windows Rust 与 Python 全量回归、安装与卸载数据保留、运行中安装保护、核心启动退出、双架构 macOS 构建和 CLI 安装检查均已通过。Windows 产物未签名。Tauri 原生界面交互与 Apple Silicon 真机启动未在本轮验收。本机有一项后台工作进程启动测试在 2.8.35 和 2.8.34 基线复现，正式 Windows CI 通过。[发布流水线](https://github.com/lugen4570-hash/AnY_Agents_and_You/actions/runs/45742751294) · [构建报告](https://github.com/lugen4570-hash/AnY_Agents_and_You/releases/download/v2.8.35/build-report-2.8.35.json)
- 实际下载并复核 Release 全部 13 个附件的大小和 SHA-256，所有 ZIP 通过完整性检查。实下载的 Windows 便携版与桌面核心均正常启动、加载本机 Agent 向导并退出，便携版同时与实下载的 MCP ZIP 完成带联系人密钥的 `list_rooms` 验证。官网提交 `44e9ff77808a8b896329583fad103d63496174e5` 已部署成功。已核对首页与下载页 MCP 入口、Windows 和 macOS 更新清单、总下载清单、MCP SHA-256 和 CLI 清单，实际下载并逐字节比对官网 Windows 安装版与便携版、双架构 macOS DMG、macOS Python ZIP 与 MCP ZIP，另校验了 CLI 源码包。[GitHub Release](https://github.com/lugen4570-hash/AnY_Agents_and_You/releases/tag/v2.8.35) · [Pages 部署](https://github.com/lugen4570-hash/AnY_Agents_and_You/actions/runs/45744002516) · [下载清单](https://lugen4570-hash.github.io/AnY_Agents_and_You/downloads/manifest.json)
- MCP ZIP 为 24,806 字节，SHA-256 为 `34a015ce57f7764b135a6391690a106c9774c5549392d8771479476736b29da7`。[MCP ZIP](https://lugen4570-hash.github.io/AnY_Agents_and_You/downloads/AnY-MCP.zip)

## AnY 2.8.34 正式发布（2026-11-25）

- 三端全面升级为 T2 蓝宝石光学座舱视觉（`Y` 冷银代表人、`A` 18K 金代表 AI，珊瑚橙用于权限确认与护栏提示，绯红用于失败或撤回）。官网采用全站暗场、半连笔花体签名字标与 `Agents and You` 副标，背景改用 Canvas 竖向落雨（随机速度与疏密分布的金色字节流 + 冷银人类协作短句，支持一键暂停与系统减弱动态效果）；GUI 同步深浅双主题、访客/接入页与桌面壳启动底色；CLI 更新主题与 `WelcomeMark`，并在 [bridge/terminal.py](../bridge/terminal.py) 修复退出时 `refresh_backend` 竞态导致的 `NoMatches` 错误。
- 发布源码为 `235122f6f0c9af6df5c63043444650fdee6d595d`。[发布流水线](https://github.com/lugen4570-hash/AnY_Agents_and_You/actions/runs/45642711275)一次通过 Windows Rust 8 项与 Python 全量回归、静态检查、安装与卸载数据保留、运行中安装保护、双架构 macOS 安装包和三种系统的 CLI 安装测试；`build-report-2.8.34.json` 标记 `source_dirty: false`。Windows 产物未签名，Tauri 桌面窗口及 macOS 实体机原生启动待真机验收。[构建报告](https://github.com/lugen4570-hash/AnY_Agents_and_You/releases/download/v2.8.34/build-report-2.8.34.json)
- [v2.8.34 Release](https://github.com/lugen4570-hash/AnY_Agents_and_You/releases/tag/v2.8.34) 的 12 个附件均已实际下载，大小与 SHA-256 与 GitHub 元数据及 [SHA-256 清单](https://github.com/lugen4570-hash/AnY_Agents_and_You/releases/download/v2.8.34/SHA256SUMS-2.8.34.txt) 一致；4 份发布 ZIP 完整性通过；下载后的 `AnYCore.exe`（`18875`）与 `AnY-Portable-2.8.34.exe`（`18876`）通过隔离数据目录启动、`/api/server/info`（`2.8.34` / `api_revision=3`）、6 份前端核心资源与 `v2.8.34` 标签逐字节比对及 `/api/server/exit` 正常退出验收。
- 官网提交 `29204d4c7058595dc10700369e025037d43bf512` 已通过 [Pages 部署](https://github.com/lugen4570-hash/AnY_Agents_and_You/actions/runs/45646692095)。已核对首页、下载页、`update.json`、三份 macOS 更新清单、`downloads/manifest.json` 与 `cli/current.json`，并实际下载验证 Windows 安装版、便携版、双架构 macOS DMG、两条 macOS Python ZIP 地址及 CLI 源码包，大小和 SHA-256 全部一致。[官网下载](https://lugen4570-hash.github.io/AnY_Agents_and_You/download.html)

| 官网文件 | 字节 | SHA-256 |
| --- | ---: | --- |
| Windows 安装版 | 13664719 | `5530610226c519b9dbcd64a0d0e19e882b472991bdb2d0454eca149436623f77` |
| Windows 便携版 | 13501666 | `7b9a1b67580ac9b3a9429a7a6c25ecc76bb2cad66243f1747ffed60c36099ade` |
| macOS Apple 芯片 DMG | 32309523 | `84b9c12d24ee2b93d6c9b16e5fe0d7b5a7afa4f97e197d9338695789b351fd36` |
| macOS Intel DMG | 27035673 | `2be54cc648a8a682dbc63155294e07c3114d8504c2e273185101925eb915c0e6` |
| macOS Python ZIP | 1986154 | `ba658d0aa931f75b4e1615993021a96aa84d0c0a1a628e90a6a23b9a1eb84bcd` |
| CLI 源码包 | 472711 | `f6161557e2ed95a97fd72bb1300f62dce1cf33ce31d75a24c41991836b2b9097` |

## AnY 2.8.33 正式发布（2026-11-25）

- 新建会话、会话成员与权限和 Agent 与连接优先用已有联系人资料显示，日常轮询只读取联系人和连接状态，主动查找已安装 Agent 时仍执行完整扫描。隔离复测中，三个入口显示内容耗时为 6–302 毫秒，轻量联系人请求为 31–34 毫秒。
- 2.8.32 首次发布流程在 Windows 全量回归中发现成员权限测试夹具缺少已加载目录，未生成正式 Release。补齐夹具后递增到 2.8.33，保留旧标签。发布源码为 `67d79ea67d4a76615d844bfa76f5d149dc3acd83`。[2.8.32 首次流程](https://github.com/lugen4570-hash/AnY_Agents_and_You/actions/runs/45635649726) · [2.8.33 发布流程](https://github.com/lugen4570-hash/AnY_Agents_and_You/actions/runs/45636863055)
- 2.8.33 的 Windows Rust 和 Python 全量回归、静态检查、安装与卸载数据保留、运行中安装保护、Windows/macOS/Linux CLI 安装均通过。两种 Mac 架构的 DMG 内容、架构和签名校验通过，Intel 构建还通过了后台启动、资源读取和退出检查。Apple 芯片版的原生启动尚未在 Apple Silicon 实机验证。Windows 构建报告标记源码干净、产物未签名。[构建报告](https://github.com/lugen4570-hash/AnY_Agents_and_You/releases/download/v2.8.33/build-report-2.8.33.json)
- 实际下载 GitHub Release 的全部 12 个附件并核对大小及 SHA-256，ZIP 完整性检查通过。下载后的 Windows 便携版和桌面核心用隔离数据目录验证了 `2.8.33 / api_revision=3`、轻量联系人接口、三份前端资源及正常退出。桌面包打开了真实的 Tauri 窗口。首次关闭时后台未在 7 秒观察窗口内退出，等待界面初始化 3 秒后复测，关闭窗口后后台约 3.3 秒退出。[GitHub Release](https://github.com/lugen4570-hash/AnY_Agents_and_You/releases/tag/v2.8.33) · [SHA-256 清单](https://github.com/lugen4570-hash/AnY_Agents_and_You/releases/download/v2.8.33/SHA256SUMS-2.8.33.txt)
- 官网提交 `5f57e944390a40e6479f0036356d0a6086d609d9` 部署成功。线上首页指向本版下载页，核对了 Windows 更新清单、三份 macOS 更新清单、下载总清单和 CLI 版本清单。实际下载了 Windows 安装版和便携版、两种 Mac DMG、两个 macOS Python ZIP 地址及 CLI 源码包，大小与 SHA-256 均一致，CLI 源码包对应发布标签。[Pages 部署](https://github.com/lugen4570-hash/AnY_Agents_and_You/actions/runs/45638857499) · [官网下载](https://lugen4570-hash.github.io/AnY_Agents_and_You/download.html)

| 官网文件 | 字节 | SHA-256 |
| --- | ---: | --- |
| Windows 安装版 | 13665773 | `e8abfa5e07ae2b41be51918c1e2602bc68c84a02bd5d3c75a198fa6d6497f2a6` |
| Windows 便携版 | 13494322 | `0a179af50aa50eb407220e75fbbf2b14071e2fc8bf5018036469520a23515236` |
| macOS Apple 芯片 DMG | 32571847 | `5a4c3b09b2af44ab2bff69b88d57c8a181d158e033e48a177284086ceafc8193` |
| macOS Intel DMG | 27028150 | `055983d1fb3ddfaa8e9071a1c2d6c2a50a383bbe2936e12591de82f3446e94d4` |
| macOS Python ZIP | 1980002 | `b5822e1dae26820750abf1f023e072e35c068a46463c9d42f4f53fc9f4b039a5` |

## AnY 2.8.31 正式发布（2026-11-25）

- 本版包含 `2.8.30` 新增的二级/多级弹窗返回导航（[app-core.js](../static/app-core.js) 弹窗返回栈、`← 返回` 顶部按钮及保存/取消回退，覆盖设置、Agent 管理与详情、自动发现、接入引导、心跳设置、模型与执行端跳转、项目设置与改名等路径，并在 [test_simplified_frontend.py](../tests/test_simplified_frontend.py) 补齐回归用例），以及 `7a274cc` 更新的新版 T2 蓝宝石图标资源。
- 发布源码为 `b2b8a8ddc96cd0fced311ed0409c8bf5585d7812`。[发布流水线](https://github.com/lugen4570-hash/AnY_Agents_and_You/actions/runs/45573428751)首次运行时 Windows 任务在 `tests/test_members.py` 出现 1 次并发轮询时机失败，重跑失败任务后通过 Windows Rust 8 项、Python 全量回归 569 项、静态检查、安装与运行保护、卸载保留数据、双架构 macOS 安装包和三种系统的 CLI 安装测试；`build-report-2.8.31.json` 标记 `source_dirty: false`。Windows 构建未签名，Tauri 桌面窗口及 macOS 实体机原生启动待真机验收。
- [v2.8.31 Release](https://github.com/lugen4570-hash/AnY_Agents_and_You/releases/tag/v2.8.31) 的 12 个附件均已实际下载，大小与 SHA-256 与 GitHub 元数据及 [SHA-256 清单](https://github.com/lugen4570-hash/AnY_Agents_and_You/releases/download/v2.8.31/SHA256SUMS-2.8.31.txt) 一致；4 份发布 ZIP 完整性通过；下载后的 `AnYCore.exe`（`18875`）与 `AnY-Portable-2.8.31.exe`（`18876`）通过隔离数据目录启动、`/api/server/info`（`2.8.31` / `api_revision=3`）、11 份前端资源与 `v2.8.31` 标签逐字节比对及 `/api/server/exit` 正常退出验收。[构建报告](https://github.com/lugen4570-hash/AnY_Agents_and_You/releases/download/v2.8.31/build-report-2.8.31.json)
- 官网提交 `eac74ae` 已通过 [Pages 部署](https://github.com/lugen4570-hash/AnY_Agents_and_You/actions/runs/45576478403)。已核对首页、下载页、`update.json`、三份 macOS 更新清单、`downloads/manifest.json` 与 `cli/current.json`，并实际下载验证 Windows 安装版、便携版、双架构 macOS DMG、两条 macOS Python ZIP 及 CLI 源码包，大小和 SHA-256 全部一致。[官网下载](https://lugen4570-hash.github.io/AnY_Agents_and_You/download.html)

| 官网文件 | 字节 | SHA-256 |
| --- | ---: | --- |
| Windows 安装版 | 13664172 | `a3b9dcf7033268cb53cf4f21881a0ff768f2749fb0b717d70fbcc5ccc21358a6` |
| Windows 便携版 | 13494145 | `8454f23332e3579bd24813cb2492ed5648ee4c9cf0d0c149ff920b21bd99f078` |
| macOS Apple 芯片 DMG | 32572037 | `8a128113842ea39aae692c03e80aa3a880975f837b37afe97fb6ba3cf9fe3220` |
| macOS Intel DMG | 25715793 | `c0e2ef62bbf0f45e8bcbe0700830b90cbf4ed96cacc811947e8a190c49b48b9c` |
| macOS Python ZIP | 1979362 | `a8bbec7a1953ba309bc121baf42e343995730ada531d018481669c41a8aca680` |
| CLI 源码包 | 471167 | `142369674be3a66a49ded8ed07bc97fb826625db44005c143135dc1e0505f237` |

## AnY 2.8.30 过渡发布（2026-11-25）

- 源码 `c5089a4` 与版本提交 `80327c5` 实现并验证了二级/多级弹窗返回导航。[发布流水线](https://github.com/lugen4570-hash/AnY_Agents_and_You/actions/runs/45571809517)全量通过并发布 [v2.8.30 Release](https://github.com/lugen4570-hash/AnY_Agents_and_You/releases/tag/v2.8.30)，本地已核对 12 个附件哈希、4 份 ZIP 完整性及 `AnYCore.exe` / `AnY-Portable-2.8.30.exe` 启停与资源一致。因同期 `main` 已合入 `2.8.31`，官网与 `update.json` 直接对齐至 `2.8.31`。

## AnY 2.8.29 正式发布（2026-11-25）

- 本版在「会话成员与权限」增加双向调用与转派、设备工作区绑定、远端停止回执和指定接收人分享。外部用户可调用获授权的直连模型。跨账号认领原生 CLI、官方云托管和离线持久排队仍待实现。[权限架构与使用说明](ROOM_CONTACT_PERMISSIONS.md)
- 发布源码为 `296c6e1502bac5d846a4de428e874a40f420735f`。[发布流水线](https://github.com/lugen4570-hash/AnY_Agents_and_You/actions/runs/45550933776)通过 Windows Rust 8 项、Python 全量回归 568 项、静态检查、安装与锁定保护、卸载保留数据、macOS 两种架构的安装包和三种系统的 CLI 安装测试。Apple 芯片构建首次在生成 DMG 时遇到 `Resource busy`，同标签重跑成功，已核对 arm64 架构、签名和 DMG 内容，原生启动待验收。
- [v2.8.29 Release](https://github.com/lugen4570-hash/AnY_Agents_and_You/releases/tag/v2.8.29) 的 12 个附件均已实际下载。各文件大小和 SHA-256 与 GitHub 元数据一致，校验清单内 11 项一致，ZIP 完整性通过。桌面核心和便携版通过独立数据目录启动、版本与 API 修订校验、新权限状态 API、四份前端文件、内置连接端源码包及退出关闭端口的验收。Windows 构建未签名，构建报告标记了构建过程中的工作树改动。本机未单独验收 Tauri 窗口交互。[SHA-256 清单](https://github.com/lugen4570-hash/AnY_Agents_and_You/releases/download/v2.8.29/SHA256SUMS-2.8.29.txt) · [构建报告](https://github.com/lugen4570-hash/AnY_Agents_and_You/releases/download/v2.8.29/build-report-2.8.29.json)
- 官网提交 `2754462c525a0a8679781cfa9642dd55308d011d` 已通过 [Pages 部署](https://github.com/lugen4570-hash/AnY_Agents_and_You/actions/runs/45552798963)。已核对首页、下载页、Windows 和三份 macOS 更新清单。实际下载 Windows 安装版与便携版、两份 DMG、两条 macOS Python ZIP 链接和 CLI 源码包，全部与对应清单的大小和 SHA-256 一致。前六条链接与 Release 对应附件一致，CLI 清单和归档源码与发布标签一致。[官网下载](https://lugen4570-hash.github.io/AnY_Agents_and_You/download.html)

| 官网文件 | 字节 | SHA-256 |
| --- | ---: | --- |
| Windows 安装版 | 13410078 | `c3e06a4e1d6dde3624b2ab683e0c5b63f501f381c45f5b73ba038e3a22fc45ba` |
| Windows 便携版 | 13383441 | `19e67432380545ef363088aea117a262ad045c888a2e95f9afabac3eb56af9a5` |
| CLI 源码包 | 435982 | `75765d5d221307ac0b8d75afde73d6b14d93a3aa8bf88fc683995eb053a3ec65` |

## AnY 2.8.28 正式发布（2026-11-24）

- 输入 `/` 即显示内置命令，Agent 技能在后台加载。桌面聊天区移除顶部横幅，左栏分为「会话」和「联系人」，手机端保留一行导航。小改动完成必要验证后直接提交推送的约定已写入 [AGENTS.md](../AGENTS.md)。
- 构建源码为 `07b230c8907f5aae0f77a422682d186d7331cf2e`。[发布流水线](https://github.com/lugen4570-hash/AnY_Agents_and_You/actions/runs/45425570124)通过 Windows Rust 8 项、Python 全量回归 559 项（0 个失败模块）、静态检查、安装保护、卸载保留数据、双架构 macOS 安装包验证及 Linux、Intel macOS、Windows 的 CLI 安装测试。Apple Silicon 通过交叉构建后的架构、签名和 DMG 检查，原生启动待验收。
- [v2.8.28 Release](https://github.com/lugen4570-hash/AnY_Agents_and_You/releases/tag/v2.8.28) 的 12 个附件已全部实际下载并核对大小和 SHA-256，Windows 三份 ZIP 完整性通过。下载后的 `AnYCore.exe` 和便携版通过隔离启动、版本 `2.8.28` / API 修订 `3`、四份变更前端资源核对以及退出后端口关闭。Windows 二进制未签名，构建报告记录了打包工作树有改动。[校验清单](https://github.com/lugen4570-hash/AnY_Agents_and_You/releases/download/v2.8.28/SHA256SUMS-2.8.28.txt) · [构建报告](https://github.com/lugen4570-hash/AnY_Agents_and_You/releases/download/v2.8.28/build-report-2.8.28.json)
- 官网提交 `784702a07d6e1be9e68d7e6767dd3075a13f5dab` 的 [Pages 部署](https://github.com/lugen4570-hash/AnY_Agents_and_You/actions/runs/45427198624)成功。线上首页、下载页、Windows 及三份 macOS 更新清单均已核对。实际下载的 Windows 安装版、便携版、两份 macOS DMG 以及两条 macOS Python ZIP 链接均与 Release 附件大小及哈希一致。CLI 源码包为 `423119` 字节，SHA-256 为 `cf5d4a5c590b7144a9cde4754ccdf6508833ca553765b434cdd8ed53005701bd`，清单、归档源码和发布标签一致。

## AnY 2.8.27 发布与云账号测试交接（2026-11-24）

### 下载安装与首次本地协作

- 官网 macOS 安装指南第四步已换成新版「新建项目」截图，图注采用「添加文件夹」。源码提交 `ec4e7ce`，已核验线上页面引用及图片与原图字节一致。[Pages 部署](https://github.com/lugen4570-hash/AnY_Agents_and_You/actions/runs/45415139646)
- [v2.8.27 正式 Release](https://github.com/lugen4570-hash/AnY_Agents_and_You/releases/tag/v2.8.27) 已发布，构建源码为 `5d05205d02a357b8d405e7092532be3757fbd2fe`。[Windows 构建](https://github.com/lugen4570-hash/AnY_Agents_and_You/actions/runs/45403832347)、[双架构 Mac 与 Linux CLI](https://github.com/lugen4570-hash/AnY_Agents_and_You/actions/runs/45402590052) 的对应任务及[汇总发布](https://github.com/lugen4570-hash/AnY_Agents_and_You/actions/runs/45405853942)通过。Release 的 12 个附件均实际下载并核对大小及 SHA-256，Windows 3 份 ZIP 完整性通过。[完整 SHA-256](https://github.com/lugen4570-hash/AnY_Agents_and_You/releases/download/v2.8.27/SHA256SUMS-2.8.27.txt)。
- [官网 Pages 部署](https://github.com/lugen4570-hash/AnY_Agents_and_You/actions/runs/45406292697)完成，部署提交 `afe7cbc444e65fdd8e5541b93b9cfd8ca39dbc46`。官网安装包、便携版和双架构 DMG 实际下载与 Release 一致；2.8.20 更新器实测可解析 2.8.27 的 Windows 清单及兼容 macOS Python ZIP 清单。
- 从官网下载 2.8.27 Windows 便携版，在独立临时数据目录中启动。免登录创建会话并同时发给已安装的 Codex、Claude，两者均实际回复，程序正常退出。Windows 安装版在 CI 独立 AppId 下验证安装、运行中防覆盖和防卸载、后台正常退出与卸载保留数据。Rust 8 项和 Python 557 项通过。
- Windows 构建报告标记构建工作树有变化；从指定标签检出后，构建脚本会重生成图标。比对安装载荷中的 32 个跟踪前端资源，5 个图标文件与 Git 字节不同，其余一致。Windows 二进制未签名。
- Intel Mac runner 通过 DMG 挂载、Intel 可执行文件架构、应用版本、签名、后台启动和退出及成员连接 ZIP 校验。Apple Silicon 版在 Intel runner 上用官方 universal2 Python 交叉构建，通过双可执行文件 arm64 架构、签名、应用版本、DMG 挂载和资源检查。两个官网 DMG 确认与上述构建同 SHA-256。两种实体 Mac 的 Finder 拖拽安装和门禁弹窗待验收，Apple Silicon 的原生启动及 CLI 待验收。
- CLI 在 Windows、Intel macOS、Linux 分别验证了从空运行目录自动安装托管 Python，再运行 `any --help`。部署后复验官网 `irm … | iex`，在独立目录成功安装并通过 `any --help` 和 `any --version`。官网 CLI 源码包实际下载为 `422666` 字节，SHA-256 `70b2717ccf32a81bb2c4a391d6ce57c83a93ea6987c9b1e70732fc409676e900`，源码来自同一发布标签。

| 官网文件 | 字节 | SHA-256 |
| --- | ---: | --- |
| Windows 安装版 | 13370698 | `860e8deef9b80958c7ffe248bba90866320e48744e1b9f809f7f58f62e24eade` |
| Windows 便携版 | 13345251 | `7de7915b5f0b9a0f1393003080f52255b6bb481cd097ed45639db43a08b621c4` |
| macOS Apple 芯片 DMG | 31365268 | `dd1b98ceedf470d01f2c044c51e65325e802a1c2df2d5631b767e918281d9fcc` |
| macOS Intel DMG | 25911397 | `87c8a5138307f557434a9140af310aef1a436efbb8f3a01fad8501b212fa8660` |
| 兼容 macOS 源码 ZIP | 787045 | `d424d0f913b315c954b65a34acb076e544b139d6321d2d35190a054dfbda1e04` |

### 云账号测试状态

- 可选账号、随机安装 ID、设备命名、服务端设备上限和会话撤销、偏好白名单及版本冲突处理已提交 `60c0b6f`。本地 Edge Function、PostgreSQL 迁移和多客户端浏览器测试通过换机恢复、断网编辑与冲突处理、账号隔离、超限、下线后的重连校验、协议提示和短信倒计时。
- 正式版可直接使用本地协作，云账号入口默认关闭。扫码事件、短信和 Realtime 网关使用测试夹具。本地确认了撤销会生成通知，客户端重连会拒绝撤销后的会话。还需真实 Supabase 项目及 Realtime、微信测试号与 cloudflared 回调、正式微信资质和短信通道、正式协议及隐私政策。部署方式和测试边界见 [CLOUD_ACCOUNT.md](CLOUD_ACCOUNT.md)。

## AnY 2.8.20 正式发布（2026-11-24）

- **本版改动**：
  - **项目设置与多目录 / 分支支持**：侧栏项目头（`⚙`）与「项目与会话管理 → 设置」支持项目改名与编辑多个工作目录（1–32 个）；新建会话时通过 `/api/projects/workspaces` 读取项目目录与同仓 Git Worktree 并展示各自检出分支，已有会话保留创建时目录。
  - **教学移入设置与界面精简**：空会话不再自动弹出协作引导卡，原 3 步协作引导集成至「设置 → 使用教学」；「继续论道」按钮从底部输入栏移至最近一次论道的最后一条相关消息下方；新建会话与模型弹出层移除「默认模型 / 默认强度 / 会话默认模型」字样，未单独指定时展示「模型 / 跟随接入设置 / 由 Agent 决定」。
  - **论道盲发轮修复**：合并并保留首轮独立表态期间暂存实时进度与外发消息、全员结束后一并公开的修复。
- **构建与验证**：构建源码提交为 [`0f79d58`](https://github.com/lugen4570-hash/AnY_Agents_and_You/commit/0f79d58457e636ecd7832c7cc38dbf997f8e19d0)。`mypy bridge`（47 个源文件）、`ruff check`、`node --check`（JS 文件）、`cargo test --locked`（8 项通过）与 `tests/run_all.py`（49 个测试模块共 552 项全部通过）均通过。在隔离发布工作树中完成构建：打包后的 `AnYCore.exe`（端口 `18765`）与 `AnY-Portable-2.8.20.exe`（端口 `18766`）完成隔离启动、`/api/server/info`（`2.8.20` / `api_revision=3`）、静态资源逐字节一致与 `/api/server/exit` 零残留退出验证；`AnY-Setup-2.8.20-test.exe` 完成静默安装、运行中核心防覆盖/防卸载保护、静默卸载、`{E49FBE28-CC82-4E08-B5CD-E48A2C894472}_is1` 清理与 `data/sentinel.txt` 保留验证；3 份发布 ZIP 完整性及零私人数据校验通过。
- **GitHub Release**：[v2.8.20](https://github.com/lugen4570-hash/AnY_Agents_and_You/releases/tag/v2.8.20) 已上传并核对全部 7 个附件（Windows 程序未签名）：
  - `AnY-Setup-2.8.20.exe`：`13,457,695` 字节，SHA-256 `a976702ef1743eb6d9d4b78f3d7179c0f2c1dca00db2d6bfbb3f1ac3fa27793e`
  - `AnY-Desktop-2.8.20-win64.zip`：`16,001,384` 字节，SHA-256 `dfc91652cd759cf40536cb26de3d08ba8fe19df985eb2ce3a6addff7469dca90`
  - `AnY-2.8.20-win64.zip`：`13,154,958` 字节，SHA-256 `b01f80d0d545b1ace664fce821d9d4548b73c538e60c55a9d901b383afad22ae`
  - `AnY-Member-2.8.20.zip`：`267,333` 字节，SHA-256 `e5ef9f1393cc20b2da49731b7631dd0cd6802e065de6207b92824d80a6ad2ea0`
  - `AnY-Portable-2.8.20.exe`：`13,417,523` 字节，SHA-256 `b64e127bba1d4ff7f170fbd8d4c2232d6d546b77cbd93378562bb2c1342dd25e`
  - `SHA256SUMS-2.8.20.txt`（`452` 字节，SHA-256 `69657a36a7dfe9b349d1680d150509dd211d1f390f5db3501d1a6346dfacbc39`）与 `build-report-2.8.20.json`（`1,779` 字节，SHA-256 `ca6a85c9d411a02a97bdf32cf9ad57b2d2266cfb721913099902baf6e1fc2578`）
- **官网与在线核对**：官网提交 [`2796661`](https://github.com/lugen4570-hash/AnY_Agents_and_You/commit/27966613a27f6c873f4b08c8cceb4f59f907e81e) 触发 [GitHub Pages 部署 45366055780](https://github.com/lugen4570-hash/AnY_Agents_and_You/actions/runs/45366055780) 成功。实测 `download.html`、`update.json`、`macos-update.json` 与 `cli/current.json` 返回 HTTP 200，并实际下载核对了线上 `AnY-Setup-2.8.20.exe`、`AnY-Portable-2.8.20.exe`、`AnY-2.8.20-macOS-Python.zip`（`773,039` 字节，SHA-256 `111adcc521f43688dd50565264be55744588270f796c73eda1cf5ce742014c4c`）、`AnY-macOS-Python.zip` 与 `cli/any-cli-27966613a27f6c873f4b08c8cceb4f59f907e81e.tar.gz`（`414,250` 字节，SHA-256 `1362f3d76a8db77388e8e948aca4f3fdbb518ebd4ec8fc839936f929b03f7c02`）。

## 项目设置与会话界面（2026-11-24）

- 项目侧栏的设置按钮支持改名和编辑多个工作目录，第一行作为新会话的默认目录。创建会话时可选择项目目录或仓库中已存在的 Git worktree，并查看各自检出的分支。已有会话保留创建时的目录。
- 首次协作教学移至「设置 → 使用教学」。论道结束后，「继续论道」出现在该次论道最后一条相关消息下。
- 会话没有单独选择模型时，模型选项显示「跟随接入设置」。显式选择和执行端实际回报的模型名称仍可查看。
- 2026-11-24 全量验证：`tests/run_all.py` 49 个模块共 552 项通过，`mypy bridge`（47 个源文件）、`ruff check`、`node --check` 与 `cargo test --locked`（8 项）通过。

## AnY 2.8.19 正式发布（2026-11-24）

- **更名与核心改动**：应用、桌面壳、安装包、命令行工具（`any`）、Cookie/环境变量与文档统一更名为 **AnY（Agents and You）**，保留历史 `Cojam` 数据与配置兼容；合并并保留了 2.8.18 撤回重建、API Key 直连文字模型、房间失败反馈/审批预览与零残留退出路径。
- **构建与验证**：构建源码为 [`fc953d9`](https://github.com/lugen4570-hash/AnY_Agents_and_You/commit/fc953d926631ce81957652395937fcb144e81de5)。`mypy bridge`（47 个源文件）、`ruff check`、`node --check`、`cargo test --locked`（8 项通过）与 `tests/run_all.py`（49 个测试模块共 549 项通过）均在隔离发布工作树中通过。打包后的 `AnYCore.exe`（端口 `18765`）与 `AnY-Portable-2.8.19.exe`（端口 `18766`）完成隔离启动、`/api/server/info`（`2.8.19` / `api_revision=3`）、静态资源逐字节一致与 `/api/server/exit` 零残留退出验证；`AnY-Setup-2.8.19-test.exe` 完成静默安装、覆盖升级、静默卸载、`{E49FBE28-CC82-4E08-B5CD-E48A2C894472}_is1` 清理与 `data/` 保留验证。
- **GitHub Release**：[v2.8.19](https://github.com/lugen4570-hash/AnY_Agents_and_You/releases/tag/v2.8.19) 已上传并核对全部 7 个附件（Windows 程序未签名）：
  - `AnY-Setup-2.8.19.exe`：`13,452,900` 字节，SHA-256 `83442904c17d4aba273cce1c20e192856e98d16be84c8e95feac9dd50d9e841c`
  - `AnY-Desktop-2.8.19-win64.zip`：`15,994,328` 字节，SHA-256 `52b3a263c31d54dcbff307c79834d017e244a54570591563f45cdb50caae56d6`
  - `AnY-2.8.19-win64.zip`：`13,146,642` 字节，SHA-256 `9a43a17c62f7058570301a3863f5af0efebd69eec6ab62b9460f14b2b523b2c0`
  - `AnY-Member-2.8.19.zip`：`266,000` 字节，SHA-256 `b5281ca4f5718c84e31bc13cc5299c7dc2ddff1203d6040fdbebcfcce83ee14f`
  - `AnY-Portable-2.8.19.exe`：`13,409,730` 字节，SHA-256 `866eedf2221ba765e16518cdfd8e167e417da03cf5ea02d8aa513ec4152aa755`
  - `SHA256SUMS-2.8.19.txt`（`452` 字节）与 `build-report-2.8.19.json`（`3,170` 字节）
- **官网与在线核对**：官网提交 [`d2dd14d`](https://github.com/lugen4570-hash/AnY_Agents_and_You/commit/d2dd14d029ac1a9db2812f589bde6332c6ddb615) 触发 [GitHub Pages 部署 45324486997](https://github.com/lugen4570-hash/AnY_Agents_and_You/actions/runs/45324486997) 成功。实测 `download.html`、`support.html`、`install-cli.py`、`update.json`、`macos-update.json` 与 `cli/current.json` 返回 HTTP 200，并实际下载核对了线上 `AnY-Setup-2.8.19.exe`、`AnY-Portable-2.8.19.exe`、`AnY-2.8.19-macOS-Python.zip`（`769,204` 字节，SHA-256 `837dd14d233bb3613f02f50d58e4cd9b17d3398bc416b04782a7bd0f4a843350`）、`AnY-macOS-Python.zip` 与 `cli/any-cli-d2dd14d029ac1a9db2812f589bde6332c6ddb615.tar.gz`（`411,846` 字节，SHA-256 `d1676a871ceaf2521d6f0d170a8d206a1e18c7e0af4c8fc8155b234a772c4c9e`）。

## API Key 直连文字模型（2026-11-24）

- 空房间「接入 AI」新增「API Key 直连」。填 OpenAI 兼容的 Chat Completions 地址、模型名称和 Key，收到测试回复后即可加入会话。加入后，房间对话文字会发送给用户选择的模型服务。该联系人仅参与文字讨论。
- Windows 使用当前用户的系统凭据加密保存 Key；其他系统复用应用的本机私有配置文件。修改接入地址或模型需重新确认 Key 并测试。
- 用本机模拟服务通过 HTTP 验证了保存、重载、回复、无效 Key 和重定向。隔离 Chrome 会话跑通了测试回复、加入会话和房间内发送。
- 无 CLI、无 Key 的新用户入口和空白 Windows 的两分钟真实账号验收仍待完成。

## 房间失败反馈、审批和改动预览（2026-11-23）

- Agent 的失败消息携带成员 ID、来源消息和本步改动状态。`turn/retry/preview` 会检查文件锁和现有撤回条件，`turn/retry` 执行前再检查一遍。工具没报告的工作区改动显示为无法确认。
- 房间状态和消息会报告 ACP 提交的一次性审批请求。`turn/approval` 只处理仍有效的请求，允许仅对当前请求生效。其他驱动按各自的权限机制运行。
- `step/diff` 按记录的步骤和路径读取文本差异。新记录保留可预览文件的改后版本，旧记录仅在当前文件仍匹配当时哈希时显示差异。二进制文件和超过上限的文本返回说明。
- 首次接入卡通过房间发送测试消息，按来源消息统计各 AI 的结果。扫描不到本机程序时可打开官方安装与登录指引。失败和审批操作在原消息内处理，宽屏可固定「改动」侧栏查看文件差异、占用和撤回预览。Chrome 使用两个测试执行端验证了首次回复、改动审查、宽屏固定、窄屏抽屉、撤回重试与实时审批。
- 空白 Windows 的无 CLI、无 Key 接入仍待选择服务方和验证。上述浏览器测试使用模拟执行端，未计入真实账号登录和模型响应耗时。

## Agent 回复随原消息撤回（2026-11-23）

- 撤回真人消息会一并撤回已记录触发来源的 Agent 回复与进度，同一因果链中的回复使用相同的来源 ID。旧日志没有来源时，不自动归属。
- 本机 CLI 和 ACP 下一轮会在需要时新建会话，使用过滤后的合拍记录重建上下文，并丢弃可能包含撤回内容的压缩摘要。旧原生会话文件保留，外部已打开的会话由其执行端管理。

## AnY (Cojam) 2.8.18 正式发布（2026-11-23）

- 撤回自己的消息会一并撤回能确认来源的 Agent 回复和进度，取消正在排队或执行的对应任务。读过撤回内容的本机 Agent 下一轮会用过滤后的会议记录重建上下文。终端和桌面接管会拦住需要重建的旧会话。旧原生会话文件保留。
- 构建源码为 [`27983cc`](https://github.com/lugen4570-hash/AnY_Agents_and_You/commit/27983ccbfd91f6720372c15f03c324ea7df3648b)。170 项 Python 测试通过。Windows 核心、桌面壳和便携版启动退出通过，43 项包内资源与源码逐字节相符。打包后的核心实际验证了连带撤回和无关回复保留。隔离安装包通过安装、覆盖安装、卸载与数据保留验证。
- [GitHub Release v2.8.18](https://github.com/lugen4570-hash/AnY_Agents_and_You/releases/tag/v2.8.18) 的 7 个附件均已重新下载并核对大小和 SHA-256。Windows 程序未签名。安装包为 `13,366,238` 字节，SHA-256 为 `d5bd7445947f37ae1b9bf03a9456c1d57441ba2e219e9fbf7404c4d7f938091f`。详细结果见 Release 附件中的校验清单和构建报告。
- [GitHub Pages 部署 45137766220](https://github.com/lugen4570-hash/AnY_Agents_and_You/actions/runs/45137766220) 已成功。实测官网首页与下载页、Windows `update.json`、安装包和便携版一致。另核对了 Pages 生成的 macOS Python 与 CLI 下载清单，并实下载校验这两份压缩包。

## AnY (Cojam) 2.8.17 正式发布（2026-11-23）

- **本版内容**：
  - **官网布局修复与域迁移**：修复 [website/capabilities.html](../website/capabilities.html)「工作台实景」因缺少 `height: auto` 导致的横版截图竖向压扁问题，将 `.panel-gallery` 改为上下全宽排布并补齐 `.frame-bar` 窗口栏圆点与左右对齐；优化 [website/support.html](../website/support.html) macOS 图文教程的图注间距、`doc-callout` 间隔与步骤分隔，样式版本升级为 `style.css?v=garden-3`。因仓库已更名为 `lugen4570-hash/AnY_Agents_and_You`，同步将官网、应用内更新器（[bridge/updater.py](../bridge/updater.py)、[static/update.js](../static/update.js)）、CLI 安装器（[website/install-cli.py](../website/install-cli.py)、[website/download.html](../website/download.html)）及 Pages 清单脚本统一迁移至 `https://lugen4570-hash.github.io/AnY_Agents_and_You/`（原 `/Cojam/` Pages 路径已返回 404）。（中间版本 `v2.8.16` 保留在 Release 历史中未覆盖，随后直接递增发布 `2.8.17` 以修正全部域名引用。）
  - **客户端与后端改进**：客户端侧栏换用高反差衬线 `AnY` 字标与 `A/Y` 字母组合（[static/wordmark.svg](../static/wordmark.svg)、[static/logo-collaboration.svg](../static/logo-collaboration.svg)、[docs/ANY-DESIGN.md](../docs/ANY-DESIGN.md)）；合入会话改名、新建会话按成员配置权限、删除项目安全移入回收站、chunked 请求体读取、`FileReader` 上传回退、CLI `any`/`cojam` 双命令与左右方向键切换房间，以及 CLI/ACP 续接会话 ID 一致性校验；并在 [AGENTS.md](../AGENTS.md) 落盘下沉定位与 Open Core 商业化记忆。
- **测试与实测验证**：
  - 发布工作树源码提交 [`ce85f5a`](https://github.com/lugen4570-hash/AnY_Agents_and_You/commit/ce85f5a55e29cde6469cc6ab820f32479100156f) / [`3b72363`](https://github.com/lugen4570-hash/AnY_Agents_and_You/commit/3b72363cab8f3025418b7afbe27f0d8398a395bc)（清单更新提交 [`0bdb045`](https://github.com/lugen4570-hash/AnY_Agents_and_You/commit/0bdb045)）：536 项 Python 测试运行中 45/46 模块通过（修复 `test_simplified_frontend.py` 并 2/2 通过；`test_logging_and_errors.py` 仅余 `bridge/detached_jobs.py` 与 `bridge/owner_lifecycle.py` 原有 4 处静默异常基线），定向验证 `test_updater.py`（14 项）、`test_update_ui.py`（3 项）、`test_macos_distribution.py`（1 项）、`test_icons.py`（2 项）、Rust `cargo test --locked`（8 项）及 `static/*.js` / `website/site.js` `node --check` 全部通过。
  - 隔离端口 `18765` / `18775` 验证 `CojamCore.exe` 与 `Cojam-Portable-2.8.17.exe` 启动、`/api/server/info`（`2.8.17`、`api_revision=3`）、内置 `index.html` / `connections.js` / `update.js` / `studio.css` / `harness-ui.css` / `wordmark.svg` / `logo-collaboration.svg` 逐字节一致及 `/api/server/exit` 正常退出；3 份 Windows ZIP 完整性（含桌面版 1035 项 `_internal` 一致性）及零隐私校验通过；`Cojam-Setup-2.8.17-test.exe` 静默安装、覆盖重装与卸载均保留 `data/sentinel.txt`。
- **GitHub Release 与线上核验**：
  - [GitHub Release v2.8.17](https://github.com/lugen4570-hash/AnY_Agents_and_You/releases/tag/v2.8.17) 已上传并核对全部 7 个未签名附件（未覆盖历史版本）：
    - `Cojam-Setup-2.8.17.exe`（`13,365,226` 字节，`f4895c2b50dc09c5ff61a499590383ed0fdbc67bdd790f387935f5cd5cb9172d`）
    - `Cojam-Desktop-2.8.17-win64.zip`（`15,900,131` 字节，`116ce7b6efbfc5224edcc51b6100cf0f8d4e6db9d75caf4a99af3e69b246fd84`）
    - `Cojam-2.8.17-win64.zip`（`13,057,256` 字节，`b136ca0e41f3c3dbab915f4dacbc3ff3f3e7122e69ceaa0e1a1aba7ac6ca93f7`）
    - `Cojam-Member-2.8.17.zip`（`254,685` 字节，`43a6992dd016413bd2c16be5d8a292d92b1d00efbda9df20d7e82422636cf00d`）
    - `Cojam-Portable-2.8.17.exe`（`13,319,608` 字节，`68afb8ee0fdd02fa4a01f52b0e698ba1611bf5eeb6c10baf5465923c3e56c5ac`）
    - `SHA256SUMS-2.8.17.txt`（`462` 字节）与 `build-report-2.8.17.json`（`2,301` 字节）
  - GitHub Pages [Deploy website 45112927145](https://github.com/lugen4570-hash/AnY_Agents_and_You/actions/runs/45112927145) 部署成功；实测拉取 `https://lugen4570-hash.github.io/AnY_Agents_and_You/`（首页、`capabilities.html`、`support.html`、`download.html`、`style.css?v=garden-3`、`install-cli.py`、`update.json`、`macos-update.json`）均返回 HTTP 200；实际下载线上 `Cojam-Setup-2.8.17.exe`、`Cojam-Portable-2.8.17.exe` 与 CI 打包的 `Cojam-2.8.17-macOS-Python.zip`（`729,426` 字节，`49d8ff196b37c17a5f9fcbd33f7f16fa651805481216a1d53830a9c192176683`），大小与哈希与线上清单及 Release 100% 一致。

## AnY (Cojam) 2.8.15 正式发布（2026-11-22）

- **本版内容**：
  - **官网与品牌视觉**：官网全面更新为大卫·霍克尼明亮花园多色版，首页使用手绘斜体 `AnY` 错版阴影字标（[website/assets/wordmark.svg](../website/assets/wordmark.svg)）、多场景协作演示与平台下载页。
  - **客户端 GUI 与桌面壳**：[index.html](../index.html)、[static/studio.css](../static/studio.css)、[static/harness-ui.css](../static/harness-ui.css)、[static/app-meeting.js](../static/app-meeting.js) 统一为霍克尼明亮多色画室浅/深双主题，拉开用户池水浅蓝气泡、Agent 彩色徽章与左竖线白卡、暖鹅黄共同目标与右侧看板语义色标层次，同步 [static/connections.js](../static/connections.js) 版本校验为 `2.8.15` 及桌面壳（[desktop_shell/main.py](../desktop_shell/main.py)、[desktop_tauri/src-tauri/src/platform.rs](../desktop_tauri/src-tauri/src/platform.rs)）`AnY` 标题与 Windows 11 标题栏颜色。
  - **CLI 终端界面**：[bridge/terminal.py](../bridge/terminal.py) 升级为泳池松林画室主题，使用圆角边框卡片区分你、Agent、人类成员与系统分割线，`F3` 看板拆分为带色标头与分割线的会议目标、待办、公告、已完成、正在改的文件、论道与成员，支持按单元格宽度折行及开关侧栏/窗口缩放自动重排。
  - **macOS 图标与打包适配**：[make_icon.py](../make_icon.py) 新增导出 `roundtable.icns` 与 `desktop_tauri/src-tauri/icons/icon.icns`，[packaging/build_macos.sh](../packaging/build_macos.sh) 为 `Cojam.app` 接入 `--icon roundtable.icns` 与 `CFBundleDisplayName="AnY"`，[packaging/build_macos_python.py](../packaging/build_macos_python.py) 随分发包打包 `roundtable.icns`。
- **测试与实测验证**：
  - 发布工作树提交 [`a48649d`](https://github.com/lugen4570-hash/Cojam/commit/a48649dcae7a04b8ba0fcbda283970957838ccfc)（清单更新提交 [`dd4e4d7`](https://github.com/lugen4570-hash/Cojam/commit/dd4e4d735c0685f31b16418f622db33c325e0d87)）：117 项 Python 测试、8 项 Rust Tauri 测试、`node --check website/site.js` 与 `static/connections.js` 全部通过。
  - 隔离端口 `18765` / `18766` 验证 `CojamCore.exe` 与 `Cojam-Portable-2.8.15.exe` 启动、`/api/server/info`（`2.8.15`）、内置静态资源字节一致性及 `/api/server/exit` 正常退出；`Cojam-Setup-2.8.15-test.exe` 静默安装、覆盖重装与卸载均保留 `data/sentinel.txt`；3 份 Windows ZIP 与 `Cojam-2.8.15-macOS-Python.zip` 完整性及零私人数据校验通过。
- **GitHub Release 与线上核验**：
  - [GitHub Release v2.8.15](https://github.com/lugen4570-hash/Cojam/releases/tag/v2.8.15) 已上传并核对全部 7 个未签名 Windows 附件（不覆盖已有版本）：
    - `Cojam-Setup-2.8.15.exe`（`13,358,291` 字节，`522ea9f88b4b7d4bd587d34490d61e88f4d0ab908275f9fa7ec97ce98fb0afb4`）
    - `Cojam-Desktop-2.8.15-win64.zip`（`15,892,864` 字节，`e136094633330d9ec4ae01e1894dceb7a7722257542048882d6b95515cf3729e`）
    - `Cojam-2.8.15-win64.zip`（`13,047,303` 字节，`e23118f4da0281dc781657946979222eef456730168fcca69f6f11aed261bb55`）
    - `Cojam-Member-2.8.15.zip`（`252,649` 字节，`80c0eb2e66bec8e0bcc7f52a0d2238c9037fcae6ae9d9cbe7b16bea0d60ce290`）
    - `Cojam-Portable-2.8.15.exe`（`13,310,155` 字节，`41605ad49c7e351327199f59a241483dfa20ad56c27bfd58f5303437a29503f8`）
    - `SHA256SUMS-2.8.15.txt`（`462` 字节）与 `build-report-2.8.15.json`（`1,821` 字节）
  - GitHub Pages [Deploy website 45012787163](https://github.com/lugen4570-hash/Cojam/actions/runs/45012787163) 部署成功；实测拉取线上首页、`download.html`、`update.json`（`2.8.15`）、`macos-update.json`（`2.8.15`，`722,423` 字节，SHA-256 `fb097f39f4e128d22220120bdc63af91462c8ac1c01a827a9a6403af68fbb4dc`，含 `Cojam/roundtable.icns`），并实际下载线上 `Cojam-Setup-2.8.15.exe`、`Cojam-Portable-2.8.15.exe` 与 `Cojam-2.8.15-macOS-Python.zip`，大小与 SHA-256 100% 一致。
  - macOS 云端构建验证 [Verify macOS desktop builds 45012788570](https://github.com/lugen4570-hash/Cojam/actions/runs/45012788570)：`build (macos-15)`（Apple Silicon）打包含新版 `.icns` 图标的 `Cojam.app`、签名校验与启动后台均通过；`build (macos-15-intel)` 完成打包与 `codesign` 校验，但启动后台探测 `curl /api/server/info` 超时（exit code 28）。

## Cojam 2.8.14 Windows 正式发布（2026-11-22）

- 发布包含按会议隔离草稿、会话跨项目迁移和空项目删除、成员模型与思考强度显示、CLI 首页隐藏归档会话，以及撤回后恢复带图草稿并取消对应 Agent 任务。构建源码为 [`33ad801`](https://github.com/lugen4570-hash/Cojam/commit/33ad801de14268b1837fa78c4c19c53e6b5b63ea)。
- 207 项 Python 测试通过。CLI 长流程中的 Codex 续接提示断言在发布前的 `9b3cd13` 与本版均失败。Windows 核心、便携版、桌面壳的启动与应用内退出已验证。测试安装包完成静默安装、覆盖和卸载，并保留测试数据。桌面退出测试先调用应用内退出，再关闭原生窗口。
- [GitHub Release v2.8.14](https://github.com/lugen4570-hash/Cojam/releases/tag/v2.8.14) 的七个附件均已重新下载并核对字节数和 SHA-256。Windows 程序未签名。安装包字节数为 `13,419,545`，SHA-256 为 `90c75611af595543f43a73ab1bc539f1ad11bea36e471daaaa7c8a6358e0b9ac`。完整数据见 Release 附带的 `SHA256SUMS-2.8.14.txt` 和 `build-report-2.8.14.json`。
- 按本轮范围保留官网页面、部署与更新清单，Windows 2.8.14 从 GitHub Release 提供。本机安装版仍为 2.8.13。

## Cojam 2.8.13 Windows 正式发布（2026-11-22）

- **问题修复与测试**：在 `bridge/drivers.py` 新增 `_live_text_from_cli_line()` 与 `_extract_assistant_content()`，在 `call_cli()` 流式读取 `on_line` 时过滤 `ndjson`/`json` 预设输出的纯协议事件行（如 `step_update`）及不完整 JSON 片段，仅提取可读文本或思考摘要推送至实时状态条；普通纯文本 CLI 保持透传。在 `tests/test_agents_registry.py` 新增 `test_ndjson_live_stream_hides_raw_protocol_json` 与 `test_live_text_extractor_supports_text_and_assistant_content`。验证情况：`tests.test_agents_registry`（47 项）、`tests.test_icons`、`tests.test_updater`、`tests.test_desktop_shell` 共 99 项通过，`tests/test_detached_jobs.py` 在 CPU 空闲下独立复跑 3/3 通过（首次高负载并发时因未设置 `ROUNDTABLE_LOG_DIR` 写入临时 `data` 且子进程超时偶发失败）；`mypy bridge/drivers.py bridge/version.py`、`ruff check bridge/drivers.py tests/test_agents_registry.py bridge/version.py`、`node --check static/connections.js` 与 `cargo test --locked`（8 项 Rust 测试）全部通过。
- **源码与 Release 发布**：基于 `2.8.12` 最新主线提交 [`c1af1516701e417165f23c919a877674c84e9cc1`](https://github.com/lugen4570-hash/Cojam/commit/c1af1516701e417165f23c919a877674c84e9cc1) 从干净工作树重新构建 Windows 全套产物（未签名），[GitHub Release v2.8.13](https://github.com/lugen4570-hash/Cojam/releases/tag/v2.8.13) 上传并逐项核对全部 7 个附件（未覆盖历史版本）：
  - `Cojam-Setup-2.8.13.exe`（`13,410,263` 字节，`04f8ed72f75ac067658a754084496b662f7b7b0b8240234d1c97bad1a3db2a0e`）
  - `Cojam-Desktop-2.8.13-win64.zip`（`15,923,368` 字节，`4bf2a152a6457f21cc97da5d28de8aa8ce9d7951577f6ac517c5070e164e3ac9`）
  - `Cojam-2.8.13-win64.zip`（`13,059,285` 字节，`de408e7e63564e5c99f593f07f506e0e4f1f41e4773986bd010d4e344446bc73`）
  - `Cojam-Member-2.8.13.zip`（`247,048` 字节，`5bd589684596efaf3edccb922f6582366ee7167962d6ebaef29c354a612e1`）
  - `Cojam-Portable-2.8.13.exe`（`13,321,879` 字节，`94e1689c95d84166879a76d7870e62df7b4dfa07059eac5a9f7d3458c57acea1`）
  - `SHA256SUMS-2.8.13.txt`（`462` 字节）与 `build-report-2.8.13.json`（`1,684` 字节）
- **实测打包与线上核验**：隔离端口 `18765` 完成 `CojamCore.exe` 与 `Cojam-Portable-2.8.13.exe` 启动退出、`/api/server/info`（`2.8.13`）及内置静态资源字节核对；3 份发布 ZIP 完整性与零私人数据校验通过；`Cojam-Setup-2.8.13-test.exe` 静默安装/覆盖重装/卸载均保留 `data/sentinel.txt` 并清理测试卸载注册表。官网提交 [`8a278c7`](https://github.com/lugen4570-hash/Cojam/commit/8a278c7) 触发 [Deploy website 44992186704](https://github.com/lugen4570-hash/Cojam/actions/runs/44992186704) 部署成功；线上核对 `https://lugen4570-hash.github.io/Cojam/`（`15,045` 字节）、`download.html`（`4,701` 字节）、`update.json`（`2.8.13`）、`macos-update.json`（`2.8.13`，`664,274` 字节）并实际下载线上 `Cojam-Setup-2.8.13.exe` 与 `Cojam-Portable-2.8.13.exe`，大小与 SHA-256 100% 一致。

## Cojam 2.8.12 Windows 正式发布（2026-11-22）

- 修复 Antigravity Orchestrator (Neon) 的思考强度选择，折叠未安装且未配置的 Agent 预设，加入图片马赛克和编辑重做，按会议恢复文字、引用和图片草稿，支持房主和真人访客撤回自己发出的消息。独立 CLI 回收十六进制模型版本标识的修复随本版保留。
- [构建源码 1e98eb0](https://github.com/lugen4570-hash/Cojam/commit/1e98eb0456f3b7e2316a4b6f018a006850317ab1) 已推送到官方 `main`。从干净工作树重新构建。已核对 [v2.8.12 正式 Release](https://github.com/lugen4570-hash/Cojam/releases/tag/v2.8.12) 中 7 个附件的大小和 SHA-256，包括安装包、桌面 ZIP、便携 ZIP、便携 EXE、成员连接端、校验文件和构建报告。Windows 构建未签名。
- 178 项 Python 测试和 8 项 Rust 测试通过。隔离验证核心、便携版和桌面版可启动并提供本版资源，应用内「退出」可关闭后台。覆盖重装清理旧运行库，卸载保留测试数据。单用标题栏关闭窗口后，隔离测试的后台在 25 秒内仍未退出。
- 官网通过 [Pages 部署 44981151110](https://github.com/lugen4570-hash/Cojam/actions/runs/44981151110) 发布。已从线上读取首页、下载页和更新清单，并重新下载安装包和便携 EXE，字节数和 SHA-256 均与 Release 一致。安装包为 `13,407,711` 字节，SHA-256 为 `2038cb2021aef06d79f87cc8bb69151bfce29438ee1762d4a42378c9f30017ad`。

## Cojam CLI 独立启动（2026-11-22）

- 直接运行 `cojam` 或 `cojam open` 时，统一使用解析后的端口复用或启动本机后台。官网安装器的启动文件从独立 Python 环境加载 Cojam，旧启动模块仍兼容。命令找不到或仍启动旧版时，从 [官网 CLI 下载页](https://lugen4570-hash.github.io/Cojam/download.html#cli) 重新运行一次系统对应的安装命令。
- 源码 `a8a582285b428090e6edf9ad75939baaf6a02b0c` 已通过 [Pages 部署 44978222139](https://github.com/lugen4570-hash/Cojam/actions/runs/44978222139)。在 Windows 从线上安装后，验证了启动文件、显式端口冷启动、打开项目列表和退出后的后台回收。针对性回归也覆盖了复用已运行后台。原有长流程 TUI 测试在发布前的基线与本轮均出现失败，未纳入本次启动验证范围。

## Cojam 2.8.11 Windows 正式发布（2026-11-22）

- **问题修复与测试**：修复 `bridge/detached_jobs.py` 在回收独立 CLI 任务结果时将 24 位十六进制 `model_revision` 强转为 `int` 导致抛错并吞掉回复（如 Antigravity 连续触发 `invalid literal for int() with base 10` 内部错误）的问题，并在 `tests/test_detached_jobs.py` 新增 `test_detached_job_handles_hex_model_revision`。验证情况：`tests/test_detached_jobs.py` 在发布工作树与主工作区均 3/3 通过（首次合并跑 `tests.test_model_catalog`/`test_icons`/`test_updater`/`test_desktop_shell` 共 66 项通过，`test_cli_job_survives_cojam_shutdown_and_collects_on_reopen` 曾因 Windows 临时目录清理占用偶发失败，单独复跑已通过）；`mypy` 检查 `detached_jobs.py`/`version.py`/`model_catalog.py` 通过；`ruff` 检查 `tests/test_detached_jobs.py`/`version.py` 通过；`node --check static/connections.js` 与 `cargo test --locked`（8 项 Rust 测试）全部通过。
- **源码与 Release 发布**：`2.8.11` 源码提交 [`a753dd383dc3bdc4b1ecde3853518d6aa5b35607`](https://github.com/lugen4570-hash/Cojam/commit/a753dd383dc3bdc4b1ecde3853518d6aa5b35607) 推送至 `lugen4570-hash/Cojam` `main`，对应 [GitHub Release v2.8.11](https://github.com/lugen4570-hash/Cojam/releases/tag/v2.8.11) 上传并核对 7 项未签名附件（未覆盖历史版本）：
  - `Cojam-Setup-2.8.11.exe`（`13,398,721` 字节，`3e85851f46fb6ef4faee3858e23b2d1ac5f4c70301c140768d85d10c0e507893`）
  - `Cojam-Desktop-2.8.11-win64.zip`（`15,915,125` 字节，`29e0f41c36c2f9b931f8630218c72432742878590fb428767a6d2b8cad79933e`）
  - `Cojam-2.8.11-win64.zip`（`13,048,340` 字节，`7d0ee25681b26fe62e80a0370e0d3bd68672c0acb15a613268df7bdfd50158a6`）
  - `Cojam-Member-2.8.11.zip`（`245,548` 字节，`33d46ba544800faf5dd69df190fd5828c756651fd2ab68828f6826d65641c4e7`）
  - `Cojam-Portable-2.8.11.exe`（`13,311,165` 字节，`44bda2a0138d455fed70292b9aa2c345b9c3d2002eb983c3836450ce15891db7`）
  - `SHA256SUMS-2.8.11.txt`（`462` 字节）与 `build-report-2.8.11.json`（`1,692` 字节）
- **实测打包与线上核验**：在隔离端口 `18765` 与独立临时测试安装路径完成 `CojamCore.exe` / `Cojam-Portable-2.8.11.exe` 启停与资源校验、3 份 ZIP 完整性与零隐私校验、以及 `Cojam-Setup-2.8.11-test.exe` 静默安装/覆盖重装/卸载保留 `data/sentinel.txt` 与注册表清理。官网提交 [`083102c`](https://github.com/lugen4570-hash/Cojam/commit/083102c) 触发 [Deploy website 44977413908](https://github.com/lugen4570-hash/Cojam/actions/runs/44977413908) 部署成功；实测拉取 `https://lugen4570-hash.github.io/Cojam/`、`download.html`、`update.json` 与官网 `Cojam-Setup-2.8.11.exe`、`Cojam-Portable-2.8.11.exe`，字节数与 SHA-256 100% 一致。

## Cojam 2.8.10 Windows 正式发布

- Agent 默认模型下拉框会列出完整选项，保留自定义模型与随模型切换的 effort。桌面更新窗口链接到新官网下载页，打包后的核心只使用新官网更新清单。旧版 2.8.7 写入的旧域名返回 404，用户需要关闭旧版并手动安装一次。
- 正式 [GitHub Release v2.8.10](https://github.com/lugen4570-hash/Cojam/releases/tag/v2.8.10) 对应源码 `15a31efb1002ccdb3ece6fb9d24ed26688b2dda0`。实际下载复核了七项附件的大小和 SHA-256。包括桌面安装包、桌面 ZIP、浏览器便携 EXE 和 ZIP、成员连接端、[SHA-256](https://github.com/lugen4570-hash/Cojam/releases/download/v2.8.10/SHA256SUMS-2.8.10.txt) 与[构建报告](https://github.com/lugen4570-hash/Cojam/releases/download/v2.8.10/build-report-2.8.10.json)。Windows 程序未签名，与 2.8.7 一致。
- 官网部署提交 `e2b7564ee8c7795ffb12513793c4d89894e1f29f`，[Pages 部署 44918239481](https://github.com/lugen4570-hash/Cojam/actions/runs/44918239481) 已成功。首页和下载页均指向 2.8.10，线上 `update.json` 的安装包实际下载为 13,542,965 字节，SHA-256 `18a834c006f38c0bc0437b5135a5b009a4ff854f0eec204b861d8f5bbfc62f99`。浏览器便携 EXE 为 13,562,445 字节，SHA-256 `0b0f542e8f1e41eaba6120e5aa0beafe43c41039d62dd654623312a69943765e`，均与 GitHub 附件完全一致。
- 实测浏览器模型下拉和自定义保存、65 项针对性回归、8 项 Rust 测试、隔离安装与卸载、运行中安装和卸载拦截、数据保留。发布后重新启动打包核心，成功读取线上 2.8.10 清单并正常退出。首次 505 项回归中的前端连接与图标缓存问题已修复重测，后台任务两项在独立 Windows 进程环境重测通过。日志静默异常检查在本轮发布前的基线同样失败。
- Pages 已恢复 `macos-update.json`，实际下载核对了 2.8.10 Mac 源码包的 657,384 字节与 SHA-256 `138894c24e19d9cea0e6cc6c3028c0aeebdbae91105509af1e1f42bdd9315e57`。CLI 安装索引也已核对对应本次部署提交。Mac 未做实机启动测试。

## Cojam 官网重设计发布与线上验证（2026-11-21）

- **官网改动与推送**：提交 [`8e163c5055af7ed5f4ddfd735e32dae3dd0d9520`](https://github.com/lugen4570-hash/Cojam/commit/8e163c5055af7ed5f4ddfd735e32dae3dd0d9520) 推送至 `lugen4570-hash/Cojam` `main`，同步移除 `website/salon.html`，回归合拍品牌配色（浅薰衣草纸白 `#f9f8fd`、深梅子墨 `#211631`/`#1c132a`、电光紫 `#6022e8`、酸橙绿 `#d5ff3f`）与交互动效，并重构多 Agent 协作舞台与四种接入方式展示。
- **GitHub Pages 部署**：`Deploy website` 工作流 Run [`44917947676`](https://github.com/lugen4570-hash/Cojam/actions/runs/44917947676) 完成（`build` 21s、`deploy` 8s）。
- **线上逐项核验**：
  - 官网首页 `https://lugen4570-hash.github.io/Cojam/`（`15,038` 字节）、[download.html](https://lugen4570-hash.github.io/Cojam/download.html)（`4,668` 字节）与 [macos.html](https://lugen4570-hash.github.io/Cojam/macos.html)（`5,155` 字节）均返回 HTTP 200 并引用 `style.css?v=20261121-cojam`，页面已确认不含“沙龙”或 `salon`；原 `website/salon.html` 返回 HTTP 404。
  - 更新清单 `https://lugen4570-hash.github.io/Cojam/update.json` 返回 HTTP 200，版本 `2.8.7`、`size: 13318098`。
  - 实际下载安装包校验一致：`Cojam-Setup-2.8.7.exe`（`13,318,098` 字节，SHA-256 `092c32e335bbfc8005af9157f077df0d942b8e00bfabf387094f19bde802c89d`）、`Cojam-Portable-2.8.7.exe`（`13,222,934` 字节，SHA-256 `42be6c6ff60b7b823c7b5cb7da7fab9bfd10618e53487756e1f182c368627368`）；既有的 GitHub Release `v2.8.7` 未被覆盖。

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
