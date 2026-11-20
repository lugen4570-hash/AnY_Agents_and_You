# Tauri 2 桌面迁移（2.8.7，本地验收通过，尚未上线）

本分支接续 2.8.6 的目录化后台，包含正式 Tauri 2 壳及原生选择器、后台身份验证、owner_tab 生命周期、忙碌关闭确认、外链、下载、主题和浏览器回退。2026-11-19 已完成 Windows 编译及下列实机验收，并合入主分支 b26ca64 的模型、Agent 忙碌隔离和更新器改动。GitHub 账号停用仍阻止线上发布。主工作区的本地预设修改未混入产物。

## 2026-11-19 本地验收

| 场景 | 结果 |
| --- | --- |
| Rust 编译、8 项单测及正式 Release 构建 | 通过 |
| 全量回归 481 项，0 个失败模块 | 通过 |
| Mypy（39 文件）、Ruff、JS/Rust/YAML/PowerShell 检查 | 通过 |
| 两种核心身份/API、共享 owner 与末页退出；39 项内嵌资源逐字节比较 | 通过 |
| 正式 WebView2 窗口、文件/文件夹选择及取消选择 | 通过 |
| sandbox 附件不能访问父页面原生桥；blob 下载 | 通过 |
| 刷新保持原生 owner，WM_CLOSE 后壳及末页后台正常退出 | 通过 |
| 忙碌/未知状态取消关闭保留 owner，明确确认只注销一次 | 通过 |
| 外来服务、其他安装目录及忙碌旧后台的原生错误提示 | 通过 |
| 2.8.5、2.8.6 升级到 2.8.7，真实测试会话及消息保留 | 通过 |
| 覆盖安装清理旧运行库；运行中安装/卸载中止且运行库哈希不变 | 通过 |
| 正常卸载完整保留 data | 通过 |
| 生产更新辅助脚本关窗、等待后台退出、安装并重新拉起 | 通过，核心 PID 改变，测试会话和 sentinel 保留 |

实际验收修复了三处问题：HTTP 500 不能静默判为空闲；原生标题必须保持“合拍 Cojam”供更新器查找；Windows 上重命名不能可靠判断运行中映像，安装/卸载改用独占写句柄探测。两个原生选择器的授权还进一步收紧到本次准确的 loopback 端口及根页面。CI 增加运行中安装/卸载保护，并统一生成便携 EXE、SHA-256 和构建报告。

旧提示词测试已修正：ACP 重试显式提供要重放的目标/看板，本机 CLI 测试检查真实系统指令通道，不再要求用户消息重复前言。没有为这些测试改变生产提示词行为。

窗口自动化测得“启动到联系人首屏就绪”约 10.35 秒，包含调试端口和现有测试数据，不是严格冷启动 P50/P95，不能直接与旧原型的 7.2 秒等条件比较。早期错误地要求空数据必须出现可发送会话得到的 91 秒不属于启动成绩。

最终壳为 7,646,720 字节，安装包为 13,318,098 字节（12.70 MiB），桌面 ZIP 为 15,827,327 字节。完整大小/哈希和签名状态见 `dist/SHA256SUMS-2.8.7.txt`、`dist/build-report-2.8.7.json`。本轮仍未签名，不覆盖旧版附件。

原始报告保存在主工作区 `.test-tmp/tauri287-ui/`：`window-report.json`、`close-report.json`、`backend-errors-report.json`、`install-report.json`、`update-helper-report.json`；全量日志为 `.test-tmp/rel287-msvc-tests-final.log`。测试使用独立端口和数据，没有调用真实 AI，也没有停止 8765 会议。

验证范围：未执行 macOS Tauri、真实系统主题切换、系统缺失 WebView2 回退、默认浏览器外链端到端及真实公网更新下载实测。更新辅助脚本使用真实安装包，在隔离 TEST_BUILD 安装中执行。旧的 macOS 构建入口保留。

## 构建与边界

- `build_exe.ps1` 生成浏览器单文件核心及桌面目录核心；`build_desktop.ps1` 使用 `cargo build --locked --release` 生成正式壳，保持发行文件名和更新器窗口标题契约。
- 安装目录仍为 `Cojam.exe`、`CojamCore.exe`、`_internal/`、`data/`；保持 2.8.6 的运行中安装保护与数据保留。
- Python 浏览器版和成员端不更换协议。macOS 原有构建入口保留，Tauri macOS 不在本次已验证支持范围。
- 前端 `cojamDesktop` 适配层同时支持 pywebview 和 Tauri；只有原生壳负责桌面心跳，浏览器仍独立注册。Rust 初次注册失败时中止启动，定时重新注册可恢复失效的租约，关闭前先停止并等待续租线程，避免关闭后再次注册。
- 原生选择器只授权主窗口、本次准确端口的根页面，sandbox 隔离已实际验证；未暴露文件读写、终端或任意命令执行接口。
- Tauri 创建失败时使用系统浏览器的独立页面身份；原生租约自然过期，避免刚启动的浏览器被最后一个 owner 提前回收。
- CI 改为版本驱动的 Windows 构建、测试和产物上传；目前不会自动发布 Release 或修改官网。待真实窗口验收通过后，发布与官网上线仍须按 AGENTS.md 全流程执行。

## 历史候选验证记录（2026-11-18，已由上述实测更新）

- 相关 Python/Node 回归：owner_lifecycle 10 项、desktop_shell 37 项、frontend_runtime 30 项、headless 8 项通过。修改关闭确认后 desktop_shell 37 项再次通过。
- `mypy bridge`（39 文件）、Ruff、4 个改动 JS 文件的 `node --check`、`git diff --check` 通过。
- `cargo fmt --check` 和 `cargo metadata --locked --no-deps` 通过。这两项不能代替 Rust 类型检查或运行测试。
- 全量回归执行 476 项，3 个失败模块为 `test_acp.py`、`test_workdir.py`、`test_wrapup.py`；已在干净的基准 `fe88d60` 独立重跑这三个模块，均复现同样的提示词断言失败。该结果不等于全量测试通过；发行前仍需确认这些既有测试与提示词契约。日志在主工作区 `.test-tmp/rel287-tests.log` 和 `.test-tmp/rel287-baseline-tests.log`。
- `cargo check --locked` 失败于依赖的 build script 链接阶段：找不到 MSVC `link.exe`。尚未完成 Rust 类型检查、Rust 单测或壳 EXE 构建。
- 两种 Python 核心已本地构建，均未签名。打包程序在独立端口与独立数据目录通过版本/API、运行路径/数据路径、4 个更改前端资源逐字节校验；两个 owner 中关闭一个后服务仍在，关闭最后一个后服务正常退出。临时原始报告：主工作区 `.test-tmp/rel287-core-validation.json`。
- 目录版核心从未收到 owner 注册时，启动租约到期后退出码为 0；确认窗口初始化失败前的孤儿回收路径可用。CI YAML、Tauri JSON 和 PowerShell 构建脚本语法解析通过，尚未在远端执行 CI。
- 单文件核心 SHA-256：`2384f823e6c2a6c68c77d5c65b1e7c06a0b9d7d440befabca4388d004f3a6fa9`；目录核心 EXE SHA-256：`3c43de79d7797e1182a69bcadc2ac9bf4d93f3b2f13c3ecc91fa1b30dffdb3e3`。此处不是完整发行包清单。

## 发布阻塞与后续步骤

1. MSVC 与 Windows SDK 已由用户安装，编译阻塞已解除。
2. GitHub 仍返回账号 suspended，无法推送、使用远程 Actions、上传 Release 或部署 Pages。用户需恢复账号及有效认证。
3. 本地已完成上表列明的编译与场景验证；未覆盖项保持上述明确边界。
4. 旧实验原型的 7.2 秒不能视为正式壳成绩；未来性能比较仍需同机同数据的严格冷/热启动基准。
5. 完整发布时核对版本、重新构建所有产物、记录签名状态并生成最终哈希及报告；待 Release 附件验证后再更新官网、验证 Pages 与实际下载，提交并推送最终交接。不得直接将 2.8.6 的后台改造称为 Tauri 迁移已完成。

Phase 1b 的首屏和轮询优化未混入本分支。
