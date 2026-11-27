# AnY 视觉约定

名称写作 AnY，来自 Agents and You。品牌以 T2 定稿为准（[design/brand/any-logo-t2/](../design/brand/any-logo-t2/)）：液态黑铬 Y 托住彭罗斯金 A，底板是蓝宝石银玻璃。三端共用这套材质语言：**银色代表你（主持人），金色代表 AI，珊瑚色只用于需要你确认或出错的地方**。

| 角色 | 色值 |
| --- | --- |
| 深底 / 墨色 | `#070A0F` · `#0B0E13` · `#101821` |
| 铬银（文字、主按钮） | `#E6EEF6` · `#C0D5E4` · `#B7D0DC` · `#647385` |
| 彭罗斯金（AI、强调） | `#FAF1C4` · `#F4CF6C` · `#E4A832` |
| 珊瑚（确认、注意） | `#FF977A` |
| 辅助文字 | `#A6B6C7` |

Agent 保留各自的身份色，只用在头像、名字和小圆点上，不给整条消息上色。

## 官网（website/）

原生 HTML、CSS 和 JavaScript，变量集中在 [website/style.css](../website/style.css) 的 `:root`。

- 首屏：T2 徽标环、标题两行入场，第二行用铬银渐变字；右侧是可切换「桌面 / 终端」和三种协作模式的会话演示。CTA 下方用一组 `dl` 列出可接入的 Agent 和平台。
- 主按钮是铬银渐变加内高光，次要操作用下划线文字链。顶栏和页脚顶部各有一条银-金-银的渐隐细线。
- 「第一次开会」用带窗口条的 `workspace-frame` 展示真实客户端截图（`assets/workspace.png`，由新版 GUI 拍摄），右侧是编号 01–03 的上手步骤。
- 页脚五个页面一致：字标、标语、产品 / 上手 / 开源三栏链接，底行显示版本号。版本由 `site.js` 读取 `update.json` 填入 `[data-site-version]`，发布时无需手改页脚。
- 背景的金色字节雨与银色语言流固定在视口后方，右下角按钮可暂停；开启减少动态效果时停用。
- 修改样式后同步更新各页面 `style.css?v=` / `site.js?v=` 的缓存键。
- 本地 `python -m http.server` 预览下载页时 `downloads/manifest.json` 会 404，它由 Pages 工作流在部署时生成，线上正常。

## 客户端 GUI

文件：[index.html](../index.html)、[static/studio.css](../static/studio.css)、[static/harness-ui.css](../static/harness-ui.css)（`gui2` 段为本轮布局层）、[static/harness-ui.js](../static/harness-ui.js)、[static/app-meeting.js](../static/app-meeting.js)。布局对齐 Claude 桌面端：

- **侧栏**自上而下：字标 + 收起按钮 → 新建会话 → 搜索（`Ctrl K`）→ 会话 / 联系人 → 项目与会话列表 → 底部账号行。设置、检查更新、退出收进账号行弹出的菜单；有更新时头像右上角出现小圆点。账号名暂时固定为「本机用户」，接云账号名需要改造 `cloud-account.js` 的闭包状态，列为后续项。
- **空会话**居中显示 T2 标记（[static/logo-mark.svg](../static/logo-mark.svg)）、问候语和新建入口。
- **消息流**：你的消息是右侧圆角气泡；Agent 与成员的消息不加卡片，头像 + 名字 + 正文平铺在页面上；发给你的消息只在名字旁加珊瑚色「→ 用户」小标，不再整块高亮；复制 / 引用 / 撤回在悬停或聚焦时出现，触屏常显。
- **输入框**是一个圆角盒子：附件按钮、文本框、圆形发送键在同一行，下面是模式、扩展、论道、模型控制；引用和待发附件也放在盒子里。
- **右侧抽屉**：安静的描边，标签页（成员 / 看板 / 改动 / 产出），扁平卡片。可固定；窄屏自动收起。
- 浅色、深色主题共用同一结构，主题存在 `localStorage["any_theme"]`。

## CLI

文件：[bridge/terminal_brand.py](../bridge/terminal_brand.py)（调色板、T2 标志栅格化、启动页）、[bridge/terminal.py](../bridge/terminal.py)、[bridge/terminal_input.py](../bridge/terminal_input.py)。基于 Textual 和 Rich。

- **启动动效**：全屏 T2 大标，按真实 A / Y 几何用半块字符超采样绘制；约 1.25 秒内斜向揭开并扫过一道高光，随后出现字标和「Agents and You」。按任意键或点击可跳过。窄终端改用小标。`NO_COLOR`、`TEXTUAL_ANIMATIONS=none`、`ANY_NO_SPLASH` 会跳过或静态显示。
- **首页**：标志、版本、当前目录、后台连接状态和上手提示。
- **对话**采用 Claude Code 式流式排版：你的消息右缩进；Agent 用各自身份色的竖条和名字；成员与 Agent 区分；系统消息是一条细分割线；不再给每条消息套方框。代码块使用 `github-dark` 主题。
- 调色板常量见 `terminal_brand.py`：`INK #0b0e13`、`PAPER #e6eef6`、`SILVER #b7d0dc`、`GOLD #e4a832`、`CORAL #ff977a`、`MINT #88d3b8`、`RAISED #12171f`。

## 验收方式

浏览器截图用 Playwright 驱动本机 Edge（`channel="msedge"`），官网检查 1440 / 1024 / 768 / 390 四档宽度且无横向溢出；GUI 用隔离后台（`ROUNDTABLE_LOG_DIR` 指向临时目录）截深浅两套主题；CLI 用 Textual 截图检查 120×36、100×30、80×24。注意：后台启动时把 `static/` 读进内存，改完前端要重启后台才能看到效果。
