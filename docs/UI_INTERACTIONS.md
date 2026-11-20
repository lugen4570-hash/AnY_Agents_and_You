# 界面与消息交互（2026-11-18）

## 全 Agent 真实模型与思考强度索引对齐（2026-11-18 · 2.8.5）

- 清理各预设配置（`antigravity`、`cursor`、`opencode`、`grok`、`qodercli`、`gemini`、`qwen`）及内置 `claude` 中硬编码或虚构的 `models` 列表；[agents.py](../bridge/agents.py) 通过 `user_explicit_models()` 仅将用户配置文件或 Agent 设置保存的模型视为显式列表。
- [model_catalog.py](../bridge/model_catalog.py) 对 Antigravity（`agy models`）与 Cursor（`cursor-agent --list-models`）自动折叠 `<model>-<effort>[-fast]` 变体为基础模型、按模型分别列出真实 `efforts_by_model`，并提取清理零宽字符与后缀强度的 `model_labels`；[drivers.py](../bridge/drivers.py) 的 `_resolve_cli_model_effort()` 在调用时将基础模型与 `effort` 适配为执行端可接受的参数（Antigravity 为不支持思考强度的编排/中等模型清空 `--effort`，Cursor 按需回拼变体名并映射 `gpt-5.5` 的 `extra-high`）。
- [agents.py](../bridge/agents.py) 与 [model_catalog.py](../bridge/model_catalog.py) 按真实配置与查询源索引其余 Agent：OpenCode 解析 `opencode.json`/`opencode.jsonc`（含注释与尾逗号）并在本机已配置其他 Provider 时过滤未配置的 `opencode/*` 公共模型（覆盖 CLI 与 ACP）；Grok 合并 `~/.grok/models_cache.json` 与 `grok models` 输出；Qoder CLI 将 `--list-models` 超时放宽至 25s 并从 `MODEL` 表头起解析且兼容非零退出；Claude 读取 `~/.claude/settings.json`、`statusline-last-input.json` 与 `stats-cache.json`。
- 稳定化 `model_catalog._key()`（`v: 2`，仅依赖 `driver`、`bin`、`env` 及 ACP `workdir`），避免调整默认模型/参数使实时索引缓存失效；[agent_settings.py](../bridge/agent_settings.py) 复用 `model_catalog.capabilities(None, pid)`；[model_catalog.py](../bridge/model_catalog.py) `display_model_name()`、[room.py](../bridge/room.py) 与 [model-settings.js](../static/model-settings.js) 在顶栏状态条、模型弹窗及下拉框统一优先展示可读模型名（兼容剥离旧变体后缀匹配基础可读名），未提供可读名时回退模型 ID。
- 空闲 Agent 不再受同会话其他忙碌 Agent 阻挡：[room.py](../bridge/room.py) `set_models()`、[model_catalog.py](../bridge/model_catalog.py) `refresh()`、[execution.py](../bridge/execution.py) `prepare()`/`release()`、[web.py](../bridge/web.py) `/api/agents/config` 与 [app-meeting.js](../static/app-meeting.js) `openAi()` 均改为按目标 Agent 自身忙碌状态（`busy_for(ai)` / `aiBusy`）校验。
- [index.html](../index.html)、[studio.css](../static/studio.css) 与 [update.js](../static/update.js)：桌面端与浏览器端底栏的「更新」按钮默认 `hidden`（`退出` 保持右对齐），仅在后台检测到可用更新或处于下载/安装流程时显示；下载过程同步显示已下载 MB 与传输速率；[updater.py](../bridge/updater.py) 对大于 1 MB 的安装包自动启用 4 线程 HTTP Range 分片并发、断点重试与零拷贝落盘（不支持 Range 时自动回退单流）。

## 左滑收起侧栏、会话管理与状态分离及权限整合（2026-11-16 · 2.8.4）

- 桌面端（`>= 850px`）侧栏使用左移面板收起图标，点击后平滑向左滑收并消除列间距（`translateX(-104%)` + 列宽过渡至 `0px`），同步切换 `inert`；展开按钮改为贴合屏幕左边缘中部的可悬停窄把手，不再在顶栏内插入按钮。
- 右上角 `⋯`（`#bar`）仅保留「会话管理」操作（讨论/干活模式、成员与权限、整理并落盘、会议详情与看板）；参会成员实时状态条 `#caps` 移至对话顶栏独立展示，点击即可设置对应成员模型、思考强度、上下文与压缩。
- 「会话成员与权限」及邀请向导将细碎权限整合为 3 项核心权限：**参与对话**（`read` + `post` + `trigger`）、**看板与附件**（`board` + `files`）、**允许干活**（`work`），保存时无损写回后端 6 个字段；弹窗顶部提供**全选/全取消成员**及各核心权限**一键全开/全关**按钮。

## 侧栏桌面端收起、全 Agent 对齐与移除 PWA（2026-11-16）

- 桌面端（视口宽度 ≥ 850px）支持点击侧栏按钮或按 `Ctrl+K` / `Cmd+K` 收起和展开左侧栏（`body.nav-collapsed`），状态持久化在 `localStorage['cojam_nav_collapsed']`；移动端抽屉（`body.nav-open`）保持不变。
- 彻底移除网页端 PWA（删除 `manifest.webmanifest`、`sw.js`、`offline.html` 及 512px 图标），不再出现浏览器「在应用中打开」安装提示，保留标准图标和启动时清理历史 Service Worker / Cache Storage 的逻辑。
- 上下文用量、模型切换与上下文压缩对所有 Agent 对齐：
  - `cli` / `acp` / `http` / `external` 接入按各自协议解析真实 token 用量与上下文窗口并显示（无返回时显示暂无数据，不做估算）。
  - `http` / `external` 开放模型与思考强度设置（未配置默认提供 `low` / `medium` / `high`）；`aider` 预置补充 `--model {model}`；ACP 会话 `configOptions` 自动缓存并支持 `opencode` / `cursor` / `antigravity` 实时枚举；刷新模型索引后立即重绘模型控件。
  - `openAi` 对话框为所有 AI 开放「压缩上下文」：原生支持按原路径压缩，有会话的 `delta` 接入走摘要换新会话，无状态连接与 `context="full"` 接入保存 `compact_checkpoints` 摘要检查点并在后续轮次拼接新消息。

## Agent 与会话操作简化（2026-11-15）

- Claude 的详细规则进入追加系统指令，Codex app-server 在新建及续接时通过 `developerInstructions` 接收规则；普通聊天输入只含目标 / 看板、消息与必要变更。没有独立系统指令通道的接入使用简短说明，有记忆的会话在规则和权限未变化时不重复发送。权限、模式及文件护栏仍由后端执行；完整上下文接入仍需获得必要的短规则。
- 点击 Agent 默认只显示名称、连接状态、检查 / 连接按钮和一个“高级设置”入口；路径、启动参数、协议、模型索引、加入规则及权限编辑保留在高级页。自定义程序参数、HTTP 接入和手动 MCP 配置默认折叠。桌面待命离线不会自动切换 CLI，接入提示与调度行为保持一致。
- 当前空闲会话可直接移入回收站，成功后清理当前页面状态并自动选择其他会话；最后一场删除后显示空状态并移除地址栏里的旧会话 ID。运行或排队中的会话继续受保护。
- 删除联系人会自动从已加载、未加载、已归档和回收站内的会话解除关联，撤销密钥、待命及内部访问，保留历史消息。目标联系人正在执行、排队、交给终端或交接时拒绝且不部分删除；其他成员仍可继续工作。写入失败会回滚会话元数据。删除用户覆盖的预置联系人后，不会让同名预置再次出现。
- 回归包括提示与系统指令分离、短规则及增量行为、联系人跨会话清理、失败回滚、忙碌保护、简洁设置入口和当前会话删除。独立 Edge 实测覆盖高级设置进入与返回、连接检查、删除当前会话自动切换、删除联系人自动移出其他会话、删除最后一场后的空状态，无页面 JS 异常。验证截图与脚本保留在 `.test-tmp/simplicity-*` 和 `.test-tmp/ui-bugs-browser/`。
- 本轮相关回归共 167 项通过；项目范围 Ruff 与 `mypy bridge` 通过。桌面及 390px 窄屏的简洁详情页均已验证，无横向溢出。上述修改已纳入 2.8.2 安装包与便携版。

## HTML 附件与弹窗拖动修复（2026-11-15）

- 聊天消息和输入框待发送的非图片附件均可点击文件名打开会议室内预览，保留独立下载入口。HTML 在仅允许脚本的隔离 iframe 内显示，不能访问会议室主界面的 DOM 或凭证；同目录图片、脚本和样式由父页面鉴权读取并内嵌。关闭预览会取消请求并销毁 iframe。支持 PDF 和常见文本预览；其他格式保留下载。文本 / HTML 预览上限为 4 MB，HTML 直接引用的本地附件合计上限为 8 MB。
- 桌面壳开启 pywebview 的 `ALLOW_DOWNLOADS`，修复原先下载被默认禁用、点击非图片附件无反应的问题。
- 通用弹窗只在主指针于遮罩上按下、未明显移动且仍在遮罩上松开时响应关闭。从弹窗内拖出、在遮罩上拖动、取消指针操作均不会误关闭；取消按钮和 Esc 行为保留。
- 验证：29 项前端回归、37 项桌面壳回归、16 项联系人回归；独立会话中的真实 Edge 验证了 HTML 按钮交互、同目录脚本与图片、主页面隔离、文本预览、关闭清理、两种拖动及普通遮罩点击，无页面 JS 异常。截图与脚本保存在 `.test-tmp/ui-bugs-*` 和 `.test-tmp/ui-bugs-browser/`。
- 上述修复已纳入 2.8.2 安装包与便携版。源码运行的后台按启动时缓存界面资源，需要正常重启后刷新；使用旧版独立桌面 EXE 时应更新到 2.8.2。

联系人区保留「管理」和「接入」。管理页统一提供 Agent 配置、扫描本机 Agent、连接与心跳、我的浏览器 / 设备；远程浏览器不提供本机扫描。Agent 的状态取自连接状态，程序被检测到不代表已连接。启动不自动打开扫描或接入引导，扫描由用户主动操作。

桌面窗口使用 `text_select=True`。消息正文显式允许文字选择，兼容仍注入全局禁止选字样式的旧桌面壳。每条用户 / Agent 消息常驻复制与引用操作，选中同一条消息的文字后显示片段操作条。右键可复制或引用片段、复制整条消息或引用整条消息。取消选择后不再沿用历史片段，切换会议会关闭消息菜单和操作条。

复制在安全上下文优先使用 Clipboard API；HTTP（包含 tailnet 地址）或权限被拒时，使用隐藏文本框复制，并恢复原焦点与选区。失败会明确提示使用 Ctrl/Cmd+C，避免显示虚假的成功提示。

已验证：37 项桌面壳测试；23 项前端测试；独立数据下的真实浏览器拖选、片段 / 整条引用、HTTP 复制回退、失败提示、管理入口与手动扫描、390px 手机布局，未出现页面 JS 异常。截图与浏览器验证脚本保留在忽略目录 `.test-tmp/message-actions-*`。浏览器验证模拟旧壳禁选 CSS；未通过手工操作已安装的桌面 EXE 验收。

运行中的 tailnet 服务沿用 `D:\Cojam\Cojam\data`，服务按启动时的快照提供界面资源，更新需要正常重启后台，再刷新浏览器，无需迁移或重建会议数据。源码桌面壳改动需重启源码桌面窗口；独立发行 EXE 已随本轮 2.8.0 本地安装包重新构建，包含文字选择设置。


## 侧栏与会议工具整合

联系人默认收起为一行入口，展开列表最高 170px，保留更多空间给项目和会议。手机侧栏缩小品牌与搜索区域的间距。各屏幕统一使用右上角「⋯」打开会议工具，包含会话管理、新会话、模式、成员权限、落盘、会议详情与看板，以及参会成员的模型 / effort 入口；点击外部或 Escape 关闭。

原「面板」按钮缺少事件绑定，现改为「会议详情与看板」并连接右侧抽屉。支持遮罩 / 关闭按钮 / Escape 关闭和键盘焦点恢复。原来空白的环境、上下文、工具和产出区使用实际会议状态渲染；产出显示已记录的文件改动。没有数据时显示空状态。卡片使用独立按钮折叠。

验证覆盖 390、768、1280 和 1600px：实际鼠标点击菜单、详情、成员设置，检查默认收起和展开后的联系人占用、菜单边界、抽屉层级、关闭方式与卡片操作。截图在 `.test-tmp/navigation-*.png`，无页面 JS 异常。回归测试见 `tests/test_meeting_navigation.py`。


## 全局导航与当前会议分区（2026-11-13 后续调整）

本节替代上一版将会话管理和新会话放在会议工具内的安排。侧栏顺序为：品牌与搜索、新建会话、项目与会话、默认收起的联系人、应用更新 / 退出。项目与会话标题行提供管理（包含归档和回收站）与新建项目；项目行仅保留一个新建会话的「＋」。新建对话默认选择当前项目，项目行「＋」明确选择所在项目，兼容按工作目录归组的旧会议。

右上角会议工具只提供当前会议的模式、成员与权限、整理并落盘、详情与看板、模型和 effort；右侧详情保持按需抽屉。其他会议等待回复的数量移到左侧管理按钮及手机导航提示点，浏览器标题和各会话状态仍保留。移动端打开管理或新建时关闭左侧导航。

本轮不改后端接口或数据格式，不替换已发布的 2.8.0 安装包。验证通过后更新源码运行的 tailnet 服务并提交推送；后续重新打包时使用新的补丁版本。


验证记录：23 项前端回归、2 项会议导航回归和 2 项模型设置测试通过。独立数据下验证 390 / 768 / 1280 / 1600px 布局及菜单点击；浏览器内实际执行全局 / 项目内新建、归档、删除、恢复、切换会议和手机管理入口关闭侧栏。消息拖选、复制回退、片段与整条引用回归通过，无页面 JS 异常。截图和验证脚本位于忽略目录 `.test-tmp/sidebar-global-*`。
