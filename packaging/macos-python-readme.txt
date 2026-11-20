合拍 Cojam — macOS 浏览器分发版（需要 Python）
===========================================

这是完整会议室的浏览器版，不是独立 .app 安装包。
适用于 Apple Silicon / Intel Mac，需自行安装 Python 3.11 或更新版本。
不需要安装 pywebview、Node.js、Rust 或其他 Python 包。

使用方法
--------
1. 首次使用先安装 Python：https://www.python.org/downloads/macos/
2. 解压整个压缩包，将 Cojam 文件夹放在固定位置。
3. 双击「启动合拍.command」，浏览器会自动打开合拍。
4. 启动后的终端窗口保持打开；使用界面中的「退出」结束服务。

如果双击提示没有执行权限，在终端输入 chmod +x 后加一个空格，
把「启动合拍.command」拖入终端，按回车，再双击启动。
本包未做 Apple 开发者签名或公证；如系统拦截，请按系统提示处理。

会议记录和设置保存在：~/Library/Application Support/Cojam/
换新版时替换程序文件夹即可，保留上述数据目录。
分发包不包含制作者的会议记录、登录凭据或设备数据。

运行本机 AI 前，仍需自行安装并登录对应 CLI（如 Codex、Claude）。
Mac 浏览器也可以通过邀请链接参加其他电脑的会议，前提是网络可达。
GitHub 更新服务暂不可用时，请由分发者手动提供新版压缩包。

验证状态
--------
本包在 Windows 上完成干净源码打包、资源/权限位/哈希校验及解包后
Python 后台启停验证。尚未在真实 Mac 上验证 Finder 启动和浏览器流程。
它不包含 Python 运行时，也不包含原生 Tauri 桌面壳。
