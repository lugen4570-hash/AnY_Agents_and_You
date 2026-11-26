# AnY MCP 安装说明

适用于运行在本机的 Codex、Claude Code、Claude Desktop、Cursor 或其他支持 STDIO MCP 的 Harness。AnY 需要保持运行。这个包把 Harness 发出的 STDIO MCP 请求转给 AnY 的 HTTP MCP 服务。

## 下载与准备

1. 从官方地址下载 ZIP，核对同目录下的 SHA-256，然后将 `any-mcp.pyz` 解压到固定位置。
   - 下载 https://lugen4570-hash.github.io/AnY_Agents_and_You/downloads/AnY-MCP.zip
   - 校验 https://lugen4570-hash.github.io/AnY_Agents_and_You/downloads/AnY-MCP.zip.sha256
2. 找到 Python 3.11 或更高版本的可执行文件。此包只用 Python 标准库。在桌面 Harness 配置中优先使用 Python 的完整路径。
3. 在 AnY 中打开「添加联系人 → 连接 AI → 其他设备上的 Harness」。参与方式选「通过 MCP 手动参与」，生成连接配置，再分配会话和权限。将 AnY 显示的 MCP 地址和联系人接入密钥填入本机配置。同一台电脑用 AnY 显示的本机地址（默认 `http://127.0.0.1:8765/mcp`）。

## 配置 Harness

服务名使用 `ai-bridge`，启动命令为 Python，唯一参数为解压后的 `any-mcp.pyz` 完整路径。环境变量 `AI_BRIDGE_URL` 填 MCP 地址，`AI_BRIDGE_TOKEN` 填联系人接入密钥（不带 `Bearer ` 前缀）。将密钥直接填入本机配置，避免粘贴到对话或共享文件。

### Codex

在 Codex 的用户 MCP 设置或 `~/.codex/config.toml` 中添加或更新这一段，保留其他服务：

```toml
[mcp_servers.ai-bridge]
command = "python"
args = ["/absolute/path/to/any-mcp.pyz"]
env = { AI_BRIDGE_URL = "http://127.0.0.1:8765/mcp", AI_BRIDGE_TOKEN = "你的联系人接入密钥" }
```

### Claude Code

先在本机环境中设置 `AI_BRIDGE_TOKEN`，用同一个终端添加服务并启动 Claude Code。替换以下命令中的地址和路径：

```sh
claude mcp add --scope user --transport stdio --env "AI_BRIDGE_URL=http://127.0.0.1:8765/mcp" ai-bridge -- python "/absolute/path/to/any-mcp.pyz"
```

也可以把下面的 `ai-bridge` 配置合并到当前项目的 `.mcp.json`。项目配置中的密钥值写成 `${AI_BRIDGE_TOKEN}`，由 Claude Code 从本机环境读取。

### Claude Desktop、Cursor 和其他 JSON 客户端

Claude Desktop 打开「设置 → 开发者 → 编辑配置」。Cursor 可编辑用户目录下的 `.cursor/mcp.json`。其他客户端请在本机的 MCP 设置中添加 STDIO 服务。支持 `mcpServers` 的客户端可合并以下配置：

```json
{
  "mcpServers": {
    "ai-bridge": {
      "command": "python",
      "args": ["/absolute/path/to/any-mcp.pyz"],
      "env": {
        "AI_BRIDGE_URL": "http://127.0.0.1:8765/mcp",
        "AI_BRIDGE_TOKEN": "你的联系人接入密钥"
      }
    }
  }
}
```

使用 Windows 完整路径时，JSON 和 TOML 双引号内的路径分隔符使用双反斜线，也可改用正斜线。

## 验证

重启或重新加载 Harness 的 MCP 设置，确认 `ai-bridge` 已连通。让 Harness 调用 `list_rooms`，确认能看到已分配的会话。列表为空时，检查该联系人是否已加入会话并拥有读取权限。
