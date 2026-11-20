# 新账号官网迁移记录

2026-11：官网源码与使用说明链接指向 `lugen4570-hash/Cojam`。目标站点为 `https://lugen4570-hash.github.io/Cojam/`。

- GitHub Pages 工作流在缺少对应 Release 时可构建网页，但不发布不可用的更新清单或安装文件；发布附件存在时会校验安装包的大小和 SHA-256。
- 新仓库尚无 2.8.6 Release，网页下载入口暂时指向 Releases 页面并说明安装包尚未发布。
- 网页构建已成功；部署因仓库尚未启用 GitHub Pages 返回 404。需要在仓库 Settings → Pages 将 Build and deployment 的 Source 设置为 GitHub Actions，然后重新运行 Deploy website 工作流。
- 现有桌面程序的更新器仍指向旧账号官网。此迁移只修改网页，不代表现有安装包已切换更新源；发布新版本前须协调更新器、清单和实际安装包。
