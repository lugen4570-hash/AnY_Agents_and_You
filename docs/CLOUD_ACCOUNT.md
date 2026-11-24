# AnY 云账号与偏好同步测试

设置中的「账号与同步」是可选功能。本地协作、项目、会话及已有远程控制连接继续使用原有流程。云账号服务目前只接入测试部署。

## 已实现的范围

- 设置页默认打开微信扫码。测试入口可生成、刷新二维码，并在服务端收到扫码事件后显示待确认。用户在微信内打开确认链接并确认后，桌面才能领取会话。
- 测试短信复用 Supabase Auth 的发码和验码。客户端显示 60 秒重发倒计时，服务端也限制同一号码的发送频率。已登录的测试微信账号可以绑定未被占用的测试手机号。
- 每份本地数据目录保存一个随机 UUID 和可修改的设备名，服务端默认允许同一账号登录 3 台设备。新登录会轮换同一设备的旧会话。正式通道上线后还需另行确认设备上限策略。
- 单台设备撤销后，所有读取、写入及同步都要重新通过服务端会话校验。Realtime 广播只发送会话状态变化的通知，客户端收到后重新校验。断网重连、窗口聚焦及周期性检查也会重新校验。
- 用户明确开启后才同步外观主题、界面语言。新设备优先恢复已有云偏好，首次启用时从当前设备初始化。设备修改不同字段时会自动合并，同一字段有冲突时由用户选保留哪份。断网期间的待同步项以账号为范围保存在本地。
- 本地请求只会转交明确列出的云账号字段，数据库再次验证偏好字段和值。模型密钥、客户端访问令牌、本机路径、会议正文和附件留在本机。云账号本身使用单独的会话凭据，服务端只保存其摘要。

## 接入独立 Supabase 测试项目

将 `supabase/migrations/202611240001_any_cloud.sql` 应用到独立测试项目，部署 `any-cloud` Edge Function。账号、会话和偏好表在私有 schema，API RPC 只对服务角色开放。

| 测试配置 | 放置位置 |
| --- | --- |
| `ANY_TEST_KEY` | Edge Function 密钥，设为随机 32 字符以上 |
| `ANY_WECHAT_TEST_APP_ID`、`ANY_WECHAT_TEST_APP_SECRET`、`ANY_WECHAT_TEST_CALLBACK_TOKEN` | Edge Function 密钥，仅用公众号测试号 |
| `ANY_WECHAT_TEST_CALLBACK_URL` | 测试回调公网 HTTPS URL，以 `/any-cloud/wechat` 结尾 |
| `ANY_TEST_SMS_ENABLED=1` | 已配置 Supabase Auth 测试号码或测试短信渠道时，在 Edge Function 开启 |
| `ANY_TEST_CLOUD_URL`、`ANY_TEST_CLOUD_KEY` | AnY 本地后台环境变量，分别为测试函数 URL、与服务端对应的测试访问密钥 |

通过本地运行的 Edge Function 联调时，cloudflared 只代理 Edge 测试服务。把隧道给出的回调 URL 配到公众号测试号，并用同一 URL 配置函数环境变量。首次验证分别使用一个已经关注测试号的微信账号和一个首次关注的账号，观察 `SCAN`、带场景值的 `subscribe`、扫码确认链接和过期刷新。真实测试号事件和微信中的确认链接仍需实测。公众号测试号与微信开放平台的正式网站应用扫码属于不同通道。

`ANY_TEST_FIXTURES=1` 只用于下面的本地自动化，允许持测试密钥的夹具触发模拟扫码与确认。接真实测试号时使用单独部署并保持夹具关闭。不要把服务角色密钥、微信密钥或测试访问密钥放进网页、安装包或提交。

## 本地复验

本地测试通过真实 Python 后台和 Edge Function HTTP 接口，使用 PGlite 执行同一份 PostgreSQL 迁移。微信扫码、短信和 Supabase 网关由本地夹具模拟。

```powershell
npm.cmd install --prefix .test-tmp/cloud-tools --no-audit --no-fund @electric-sql/pglite deno playwright-core
$env:ANY_CLOUD_TEST_DENO = 'deno'
node tests/cloud_account_integration.mjs
```

可以将 `ANY_CLOUD_TEST_DENO` 设为 Deno 可执行文件路径，并设置 `ANY_CLOUD_TEST_CHROME` 为本机 Chromium 或 Chrome 路径以开启浏览器验收。测试启动多个不同数据目录和端口的 AnY 客户端，核对二维码状态、偏好恢复、并发冲突、超限、跨账号隔离、下线后的请求拒绝以及短信倒计时所需的服务端响应。

## 正式入口状态

Windows/macOS 正式包继续支持免登录；微信扫码、手机号登录、绑定手机号、云设备管理和同步还未正式开放。还缺独立 Supabase 测试项目接入、微信测试号实测、真实 Realtime 广播验收、正式微信网站应用和短信渠道，以及正式协议及隐私政策。生产微信适配需要采用正式身份授权，以真实端到端结果确定可展示的扫码状态。

参考 [Supabase 数据库函数](https://supabase.com/docs/guides/database/functions)、[Supabase Realtime 广播](https://supabase.com/docs/guides/realtime/broadcast)。
