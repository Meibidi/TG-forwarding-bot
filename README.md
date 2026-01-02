# Telegram 消息转发器

基于 **Pyrogram** 的 Telegram 消息监听转发程序，支持 **Bot 模式** 和 **User 模式**。
可用于监听指定群组消息，识别代理节点信息并转发到指定目标。

---

## ✨ 功能特性

- **双模式支持**：Bot 模式 和 User (Userbot) 模式可切换
- **灵活的群组配置**：支持数字 ID 和 @username 两种格式
- **多种转发方式**：
  - `extract` - 提取节点后重新发送（更整洁）
  - `forward` - 直接转发原始消息（保留来源）
- **智能过滤**：
  - 仅转发包含节点的消息
  - 关键词过滤/排除
- **代理支持**：socks5/http 代理
- **FloodWait 自动处理**
- **模块化设计**，易于维护与扩展

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

## 📁 项目结构

```text
tgbot/
├── main.py            # 程序入口
├── config.py          # 配置解析
├── parser.py          # 节点识别与提取
├── forwarder.py       # 转发逻辑
├── logger.py          # 日志模块
├── config.ini         # 配置文件
├── requirements.txt   # 依赖列表
└── README.md
```

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 获取 Telegram API 凭证

1. 访问 https://my.telegram.org
2. 登录你的 Telegram 账号
3. 点击 "API development tools"
4. 创建应用，获取 `api_id` 和 `api_hash`

### 3. 选择运行模式

#### Bot 模式
1. 在 Telegram 中找到 @BotFather
2. 发送 `/newbot` 创建机器人
3. 获取 `bot_token`
4. 在 config.ini 中设置 `run_mode = bot`

#### User 模式（推荐）
1. 只需要 `api_id` 和 `api_hash`
2. 在 config.ini 中设置 `run_mode = user`
3. 首次运行时会要求输入手机号和验证码

### 4. 配置 config.ini

```ini
[telegram]
api_id = 你的API_ID
api_hash = 你的API_HASH
bot_token = 你的BOT_TOKEN  # 仅 bot 模式需要

[mode]
# bot 或 user
run_mode = user
session_name = tg_forwarder

[monitor]
# 要监听的群组，支持多个（逗号分隔）
# 支持格式: -1001234567890 或 @channelname
source_chats = @source_channel,@another_group

[forward]
# 转发目标群组
target_chats = @my_channel
# 转发模式: extract（提取节点）或 forward（直接转发）
forward_mode = extract

[filter]
# 是否只转发包含节点的消息
nodes_only = true
# 关键词过滤（可选）
keywords =
# 排除关键词（可选）
exclude_keywords = 广告,推广

[proxy]
enabled = false
type = socks5
host = 127.0.0.1
port = 1080
```

### 5. 运行

```bash
python tgbot/main.py
```

---

## 🔧 配置详解

### [mode] 运行模式

| 参数 | 说明 |
|------|------|
| `run_mode` | `bot` - Bot模式（需要bot_token）<br>`user` - 用户模式（使用个人账号） |
| `session_name` | 会话文件名（用于保存登录状态） |

**两种模式对比：**

| 特性 | Bot 模式 | User 模式 |
|------|---------|----------|
| 需要 bot_token | ✅ | ❌ |
| 可访问私有群组 | 需被邀请 | 已加入即可 |
| 可访问公开频道 | 需被添加 | 直接访问 |
| 转发限制 | 较多 | 较少 |
| 首次登录 | 无需 | 需要验证码 |

### [forward] 转发配置

| 参数 | 说明 |
|------|------|
| `target_chats` | 转发目标，多个用逗号分隔 |
| `forward_mode` | `extract` - 提取节点重发<br>`forward` - 直接转发原消息 |

### [filter] 过滤配置

| 参数 | 说明 |
|------|------|
| `nodes_only` | `true` - 只转发包含节点的消息<br>`false` - 转发所有消息 |
| `keywords` | 关键词列表（逗号分隔），消息需包含其中之一 |
| `exclude_keywords` | 排除关键词，包含则不转发 |

---

## 📝 Bot 命令（仅 Bot 模式）

| 命令 | 说明 |
|------|------|
| `/start` | 显示欢迎信息 |
| `/status` | 查看运行状态 |
| `/help` | 显示帮助 |

---

## ❓ 常见问题

### Q: 如何获取群组 ID？

**方法1：** 使用 Bot
- 将 @userinfobot 或 @getidsbot 添加到群组
- 或转发群组消息给这些 Bot

**方法2：** 使用 @username
- 如果群组/频道有用户名，直接使用 `@username` 格式
- 例如：`source_chats = @telegram`

### Q: User 模式首次登录？

首次运行 User 模式时：
1. 输入手机号（带国家代码，如 `+8613800138000`）
2. 在 Telegram 中收到验证码
3. 输入验证码完成登录
4. 之后会自动使用保存的 session

### Q: Bot 无法接收消息？

1. 确保 Bot 已加入群组
2. 在 @BotFather 中使用 `/setprivacy` 设置为 Disabled
3. 检查群组 ID 是否正确

### Q: 出现 "Peer id invalid" 错误？

- Bot/User 可能未加入该群组
- 检查群组 ID 格式是否正确
- 尝试使用 `@username` 格式

---

## 📄 许可证

MIT License
