# macOS 下载与本机构建

打开[官网下载中心](https://lugen4570-hash.github.io/AnY_Agents_and_You/download.html#macos)，根据「苹果菜单 → 关于本机」显示的芯片或处理器选择 Apple 芯片版或 Intel 版。

## 从 DMG 安装

1. 双击下载的 DMG，把 AnY 拖入窗口里的「应用程序」。
2. 从访达的「应用程序」中打开 AnY。桌面包自带运行环境，无需先安装 Python 或打开终端。
3. 如首次开启遇到开发者验证提醒，尝试打开一次后，在「系统设置 → 隐私与安全性」向下找到 AnY，点击「仍要打开」并确认。当前 DMG 使用临时签名，尚未经过 Apple 公证。参见 [Apple 官方图文指引](https://support.apple.com/zh-cn/102445)。

## 从备用源码包运行

从下载中心选择「高级：Python 源码包」。安装 Python 3.11 或更新版本，再解压整个 AnY 文件夹。

- 双击「启动 AnY.command」打开浏览器版。终端窗口在使用期间保持打开，通过 AnY 界面的「退出」结束后台服务。
- 双击「构建 AnY 桌面版.command」生成独立应用窗口。首次构建需要联网，脚本会在包内的 `.venv-macos-build` 安装 pywebview 和 PyInstaller。完成后打开 `dist/AnY.app`，也可拖到「应用程序」。
- 在运行 AnY 的 Mac 上进入「新建项目 → 选择文件夹」，即可用系统目录选择器填写项目路径。联系人向导里的新建项目使用同一个入口。

构建也会在 `dist/` 中生成包含应用的 ZIP 和可拖入「应用程序」的 DMG。为不同架构打包时，使用对应架构的 Python 构建。

## 桌面端能力与更新

桌面壳提供原生项目目录和 Agent 文件选择器，支持下载附件和成员连接包，并在会话有任务时确认是否关闭窗口。通过 Finder 启动时，AnY 会补充 Homebrew 和常见用户级 CLI 路径。

Agent 扫描会识别放在「应用程序」中的 Claude、Codex、Cursor 和 VS Code。为 Claude Desktop 或 VS Code 配置 MCP 时，AnY 会使用对应的 macOS 用户配置路径。

官网提供较新版本时，AnY 会显示更新入口。新版桌面应用使用对应架构的 DMG 更新清单，下载后可退出旧应用并从 DMG 替换。旧客户端和源码运行方式继续使用 Python ZIP 更新清单。下载文件保存到「下载」，并验证大小和 SHA-256。

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

GitHub Actions 的「Build macOS desktop installers」在 Apple Silicon 和 Intel runner 上构建并挂载 DMG，检查架构、版本、应用签名、后台启停和成员连接包。
