# macOS 下载与本机构建

官网「macOS 下载包」提供 ZIP，适用于 Apple Silicon 和 Intel Mac。先安装 Python 3.11 或更新版本，再解压整个 AnY 文件夹。

## 使用下载包

- 双击「启动 AnY.command」打开浏览器版。终端窗口在使用期间保持打开，通过 AnY 界面的「退出」结束后台服务。
- 双击「构建 AnY 桌面版.command」生成独立应用窗口。首次构建需要联网，脚本会在包内的 `.venv-macos-build` 安装 pywebview 和 PyInstaller。完成后打开 `dist/AnY.app`，也可拖到「应用程序」。
- 在运行 AnY 的 Mac 上进入「新建项目 → 选择文件夹」，即可用系统目录选择器填写项目路径。联系人向导里的新建项目使用同一个入口。

构建还会生成 `dist/AnY-<版本>-macOS-<架构>.zip`。要分发给不同架构的 Mac，请分别使用对应架构的 Python 构建。应用使用临时签名，正式分发需要 Apple 开发者签名和公证。

## 桌面端能力与更新

桌面壳提供原生项目目录和 Agent 文件选择器，支持下载附件和成员连接包，并在会话有任务时确认是否关闭窗口。通过 Finder 启动时，AnY 会补充 Homebrew 和常见用户级 CLI 路径。

Agent 扫描会识别放在「应用程序」中的 Claude、Codex、Cursor 和 VS Code。为 Claude Desktop 或 VS Code 配置 MCP 时，AnY 会使用对应的 macOS 用户配置路径。

官网提供较新版本时，AnY 会显示更新入口。下载的 Mac ZIP 保存到「下载」，并校验大小和 SHA-256。桌面版解压新版后运行构建脚本，再退出旧版并替换 `AnY.app`。

两种启动方式都将数据保存在 `~/Library/Application Support/AnY/`（若仅存在旧版 `Cojam/` 目录会自动兼容读取）。换新版时保留该目录。本机 AI CLI 仍须单独安装和登录。

## 从源码构建

在 Mac 上生成应用：

```sh
bash packaging/build_macos.sh
```

在仓库中生成官网使用的源码 ZIP：

```sh
python packaging/build_macos_python.py
```

脚本从指定 Git 提交读取程序文件，排除未提交改动、会议数据及凭据，在 `dist/macOS/` 生成 ZIP、SHA-256 和构建报告。Windows 上可校验 ZIP、资源、权限位和解包后的 Python 后台。系统目录选择器、应用编译及 Finder 启停需要在 Mac 上验收。

GitHub Actions 的「Verify macOS desktop builds」可在 Apple Silicon 和 Intel runner 上从下载包构建，并检查签名、打包后的后台启动和成员连接包。
