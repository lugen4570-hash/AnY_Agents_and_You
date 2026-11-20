# 合拍 Windows 安装程序

当前本地构建输出 `Cojam-Setup-2.8.7.exe`，Windows 壳改为 Tauri 2；GitHub 账号停用导致本轮尚未上线。官网公开下载版本以实际部署结果为准。安装程序基于 Inno Setup 6.7.4 构建，当前使用的编译器显示“Non-commercial use only”；如果项目将商业分发，需要先核对并满足 Inno Setup 的商业使用许可。

安装程序默认安装到当前用户的 `%LOCALAPPDATA%\Programs\Cojam`，无需管理员权限；创建开始菜单快捷方式，并默认提供桌面快捷方式。运行中的应用需要先退出。应用首次启动时在安装目录旁创建 `data` 文件夹。

卸载器删除安装时登记的程序和快捷方式，不删除运行时生成的 `data`。因此卸载后安装目录可能保留会话数据。旧的便携 ZIP 或源码版若在其他目录保存数据，安装程序不会自动搬迁：需要用户确认原数据目录后再另行迁移，不应覆盖新安装中已有的数据。

当前的安装程序和内部 EXE 均未签名；下载或运行时仍可能出现安全提示。正式签名流程见 `SIGNING.md`。用户明确要求先将未签名安装程序放到官网，页面已说明这一状态。

## 构建与验证

先运行 `build_exe.ps1`（单文件核心及 `dist/CojamCore/` 目录核心）和 `build_desktop.ps1`（需要 Rust、MSVC 与 Windows SDK，产出 Tauri 壳 `dist/CojamDesktop.exe`），再运行 `python packaging/build_release.py` 生成便携版和 ZIP，并使用 Inno Setup 编译 `packaging/cojam-desktop.iss`，输出 `dist/Cojam-Setup-2.8.7.exe`。定义 `TEST_BUILD` 会生成独立 AppId（`{E49FBE28-CC82-4E08-B5CD-E48A2C894472}`）的测试安装包。验证并完成签名后用 `python packaging/build_report.py --validation <验证记录.json>` 生成最终哈希和报告；`COJAM_REQUIRE_SIGNATURE=1` 时仍要求有效签名。

安装器使用独占写句柄探测 `{app}\Cojam.exe`、`{app}\CojamCore.exe` 及 `{app}\_internal\python3*.dll`，不再用重命名判断进程是否退出。`PrepareToInstall` 最多等待 8 秒，无占用才通过 `[InstallDelete]` 清理旧 `_internal`；`InitializeUninstall` 也拒绝运行中卸载，正常卸载才通过 `[UninstallDelete]` 清理 `_internal`。全过程不触碰 `data`。实际验收确认被中止的安装和卸载均保留全部 1031 项运行库文件哈希。

## 2.8.7 Tauri 壳验收（2026-11-19）

正式 Release 构建、Rust 8 项单测及全量回归 481 项通过。使用独立 TEST_BUILD 安装从 2.8.5、2.8.6 升级，验证旧会话/消息保留、原生窗口启动和 WM_CLOSE、重装清理残留、运行中安装/卸载中止、正常卸载保留 data；生产更新辅助脚本的关窗、安装、重启和旧消息恢复也已实测通过。详见 [TAURI_MIGRATION.md](TAURI_MIGRATION.md)。

2.8.6 历史构建曾在临时目录验证升级与数据保留；2.8.7 的实际重验进一步修正了重命名锁检测，以下以新版本结果为准。官网部署由 `.github/workflows/pages.yml` 从 `website/` 发布到 GitHub Pages（构建时从对应 Release 下载附件）。

## 2.8.6 桌面核心目录化构建（2026-11-18）

- 安装版与桌面 ZIP 中的后台核心改为 PyInstaller `--onedir` 平铺布局（安装目录内为 `Cojam.exe` + `CojamCore.exe` + `_internal\` + `data\`）；便携单文件版 `Cojam-Portable-2.8.6.exe`、浏览器 ZIP `Cojam-2.8.6-win64.zip` 与成员连接端 `Cojam-Member-2.8.6.zip` 保持原有形态。
- 内嵌 39 项前端及预设资源逐字节校验一致、不含已删 `sw.js`；桌面 ZIP 含 1031 项 `_internal\` 文件且与 `dist/CojamCore/_internal` 逐项一致；成员包 56 项源码及预设通过校验且 ZIP 均不含个人会议或设备数据。
- 从真实 `2.8.5` 桌面包写入会话（`2026-11-18_2133_Pre-Upgrade_Meeting`、5 条消息）及 `sentinel.txt` / `devices.json` 后升级到 `2.8.6`：原有数据 SHA-256 保持一致，桌面窗口启动后可读取旧会话且 `WM_CLOSE` 正常退出；覆盖重装清除旧 `_internal` 残留文件；运行中 `CojamCore.exe` 触发安装中止且不破坏 `_internal` 或 `data`；静默卸载移除程序与 `_internal` 并保留全部 `data`。


## 2.8.0 本地构建（2026-11-13）

- 后台、桌面壳、安装包和便携 ZIP 均从最新源码重建，包含消息选择 / 复制 / 引用、联系人折叠入口、右上角会议工具和可用的详情 / 看板抽屉。
- EXE 内嵌 HTML、CSS、Agent 管理脚本与源码逐字节一致；桌面壳内包含 `text_select=True` 参数。隔离端口下的打包后台 API、界面和正常停止验证通过；ZIP 校验通过且未包含账户、设备、会议或密钥数据。
- 独立 AppId 的测试安装包在项目临时目录验证安装，安装后的两个 EXE 哈希与构建产物一致；隐藏启动的桌面窗口创建成功并响应正常。关闭测试窗口后桌面 / 后台正常退出；卸载后测试数据保留，独立卸载登记已移除。测试不覆盖当前用户正在使用的安装或数据目录。
- 产物位于 `dist/`，本轮仍为未签名构建；打包本身不会发布到官网或 GitHub Releases。
