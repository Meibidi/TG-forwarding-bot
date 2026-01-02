# Telegram 消息转发器

基于 **Pyrogram** 的 Telegram 消息监听转发程序。
支持 **Bot 模式** 和 **User 模式**，支持 **自动加载** 和 **自定义群组** 两种监听模式。

---

## ✨ 功能特性

### 运行模式
- **Bot 模式** - 使用 Bot Token 运行
- **User 模式** - 使用个人账号运行（推荐，功能更强）

### 监听模式
- **自动加载** (`auto`) - 自动监听账号下的所有群组/频道
- **自定义** (`custom`) - 只监听指定的群组

### 其他功能
- 多种转发方式（提取节点/直接转发）
- 智能过滤（节点过滤/关键词过滤）
- 代理支持（socks5/http）
- FloodWait 自动处理

---

## 🔗 支持的节点类型

| 协议 | 前缀 |
|------|------|
| VMess | `vmess://` |
| VLESS | `vless://` |
| Trojan | `trojan://` |
| Shadowsocks | `ss://` |
| ShadowsocksR | `ssr://` |
| Hysteria | `hysteria://` |
| Hysteria2 | `hy2://` |
| TUIC | `tuic://` |
| WireGuard | `wireguard://` |

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 config.ini

**最简配置（自动加载所有群组）：**

```ini
[telegram]
api_id = 你的API_ID
api_hash = 你的API_HASH

[mode]
run_mode = user

[monitor]
monitor_mode = auto
chat_types = channel,supergroup

[forward]
target_chats = @你的目标频道
forward_mode = extract

[filter]
nodes_only = true
```

### 3. 运行

```bash
python tgbot/main.py
```

首次运行 User 模式需要登录验证。

---

## 🔧 配置详解

### [mode] 运行模式

| 参数 | 说明 |
|------|------|
| `run_mode` | `bot` - Bot模式<br>`user` - 用户模式（推荐） |
| `session_name` | 会话文件名 |

### [monitor] 监听配置

| 参数 | 说明 |
|------|------|
| `monitor_mode` | `auto` - 自动加载所有群组<br>`custom` - 只监听指定群组 |
| `source_chats` | 要监听的群组（custom 模式） |
| `exclude_chats` | 要排除的群组（auto 模式） |
| `chat_types` | 群组类型过滤（auto 模式）<br>可选: `channel`, `supergroup`, `group`, `private` |

### [forward] 转发配置

| 参数 | 说明 |
|------|------|
| `target_chats` | 转发目标群组 |
| `forward_mode` | `extract` - 提取节点重发<br>`forward` - 直接转发 |

### [filter] 过滤配置

| 参数 | 说明 |
|------|------|
| `nodes_only` | 只转发包含节点的消息 |
| `keywords` | 关键词过滤 |
| `exclude_keywords` | 排除关键词 |

---

## 📝 配置示例

### 示例1：自动监听所有频道和超级群

```ini
[monitor]
monitor_mode = auto
chat_types = channel,supergroup
exclude_chats = @ads_channel,-1001234567890

[forward]
target_chats = @my_nodes_channel
```

### 示例2：只监听指定群组

```ini
[monitor]
monitor_mode = custom
source_chats = @vpn_channel,@free_nodes,-1002345678901

[forward]
target_chats = @my_channel
```

### 示例3：关键词过滤

```ini
[filter]
nodes_only = false
keywords = 节点,免费,VPN
exclude_keywords = 广告,推广
```

---

## 🛠 辅助工具

### 获取群组 ID

```bash
python tgbot/get_chat_id.py
```

这会列出你所有的对话及其 ID。

---

## 📝 Bot 命令（Bot 模式）

| 命令 | 说明 |
|------|------|
| `/start` | 显示欢迎信息 |
| `/status` | 查看运行状态 |
| `/list` | 列出监听的群组 |

---

## ❓ 常见问题

### Q: 推荐使用哪种模式？

A: **推荐 User 模式 + 自动加载**
- User 模式可以访问所有已加入的群组
- 自动加载无需手动配置每个群组

### Q: 如何获取正确的群组 ID？

A: 运行 `python tgbot/get_chat_id.py`，或使用 `@username` 格式

### Q: 出现 "Peer id invalid" 错误？

A:
1. 使用 `@username` 格式代替数字 ID
2. 确保已加入该群组
3. 使用 `monitor_mode = auto` 自动加载

---

## 📄 许可证

MIT License
