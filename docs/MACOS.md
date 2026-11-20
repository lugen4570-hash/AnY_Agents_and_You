# macOS 分发

## 可直接转发的 Python 浏览器分发包

`dist/macOS/Cojam-2.8.7-macOS-Python.zip` 是完整会议室的浏览器分发版，包含前端、Python 核心、默认 Agent/模型目录及成员连接包。它不包含 Python 运行时或原生桌面壳；Apple Silicon 和 Intel Mac 需要先安装 Python 3.11+，再解压并双击“启动合拍.command”。不需要安装额外 Python 包。

数据保存在 `~/Library/Application Support/Cojam/`，程序文件夹可随新版替换。启动时会补充常见 Python/CLI 路径并检查版本，浏览器自动打开；通过界面“退出”结束服务。网络不可达或本机 AI CLI 未安装/登录时，分发包不会自动替代这些条件。

构建方式：

```sh
python packaging/build_macos_python.py
```

构建脚本只读取指定 Git 提交中的文件，排除本机未提交预设、会议数据和凭据，生成 ZIP、SHA-256 与独立构建报告。压缩包中的 `.command` 使用 LF 和 Unix 可执行权限。Windows 上可以完成源文件打包、资源/哈希检查和解包后 Python 服务验证；这些检查不等于真实 Mac 的 Finder 或浏览器验收。

## 独立应用包（需要 Mac 构建）

以下为既有 pywebview Mac 构建入口；本轮补齐了模型目录和成员包资源，但没有在 Mac 上编译或验收。Tauri 壳目前仅完成 Windows 验证。

需要 macOS 和 Python 3.11 或更新版本。源码运行：

```sh
python3 -m pip install 'pywebview>=5.3'
python3 desktop_launcher.py
```

制作独立应用包须在目标架构的 Mac 上运行：

```sh
python3 -m pip install 'pywebview>=5.3' pyinstaller
bash packaging/build_macos.sh
```

产物位于 `dist/Cojam-<版本>-macOS-<架构>.zip`。分别在 Apple Silicon 和 Intel Mac 上构建对应版本。解压后将 Cojam.app 移至应用程序文件夹。构建脚本只进行临时签名，没有开发者签名或 Apple 公证，系统可能阻止打开；正式分发需要开发者签名和公证。

桌面版的数据和日志默认保存在 `~/Library/Application Support/Cojam/`；可通过 `ROUNDTABLE_LOG_DIR` 覆盖。本机 AI 命令仍需单独安装并登录。Finder 启动时会补充 `~/.local/bin`、`/opt/homebrew/bin` 和 `/usr/local/bin` 到 PATH。

macOS 包的构建和实际运行需要在 Mac 上验证。本仓库的 Windows 更新安装器不适用于 macOS，请手动替换应用包，保留上述数据目录。
