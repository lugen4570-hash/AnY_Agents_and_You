# 应用内更新

AnY **桌面端更新** 与 **CLI 端更新** 完全分离：

- **桌面端更新**：侧栏「更新」只检查官网 `update.json` / `macos-update-*.json`（对应 `bridge/version.py` 的 `VERSION`），用于在桌面应用中下载和升级桌面安装程序。CLI 自动拉起的本地后台（`ROUNDTABLE_CLI_MODE=1`）不会弹出桌面端更新提示。
- **CLI 端更新**：CLI 版本号由 `bridge/version.py` 的 `CLI_VERSION` 与官网 `cli/current.json`（及源码清单 `website/cli-release.json`）独立控制。在终端会话中输入 `/update`（仅检查）或 `/update install`（下载并切换版本），或在系统终端直接运行 `any update` / `any update --check`，均只更新 CLI 本体，不影响桌面端安装包。

首次从旧解压版升级桌面端时，先关闭 AnY，再手动运行安装程序，并在安装向导中选择旧程序文件夹，才能继续使用该文件夹下的 data。安装器卸载时保留 data。安装到其他文件夹不会自动迁移原会话数据。

当前安装程序未签名，哈希检查用于检测下载文件与版本清单不一致，不能代替受信任的代码签名。Windows 或浏览器仍可能提示扫描。

## 发布新版本

- **发布桌面端**：同时更新 `bridge/version.py`（`VERSION`）、`pyproject.toml`、`static/connections.js`、`desktop_tauri/src-tauri/` 与 `packaging/any-desktop.iss`。用 `build_exe.ps1`、`build_desktop.ps1` 构建核心和桌面入口并编译安装器；运行 `python packaging/make_update_manifest.py --notes "更新内容"`，连同安装包与 `website/update.json` 发布。
- **发布 CLI 端**：更新 `bridge/version.py` 的 `CLI_VERSION`，运行 `python packaging/make_cli_manifest.py --notes "CLI 更新内容"` 更新 `website/cli-release.json`（可按需打 `cli-v<CLI_VERSION>` 标签）；Pages 构建会独立生成 `_site/cli/current.json` 与源码归档包，无需触发桌面端重打包。
