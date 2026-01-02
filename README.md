# Telegram Proxy Node Listener Bot

基于 **Pyrogram（Bot 模式）** 的 Telegram 机器人
用于监听指定群组消息，识别代理节点信息并转发到指定目标。

---

## 功能特性

- 监听指定群组 / 超级群消息
- 自动识别代理节点链接
- 支持多节点同时提取
- 转发至多个可配置目标群组 / Bot
- 使用 `config.ini` 进行集中配置
- 支持代理（socks / http）开关
- FloodWait 自动处理
- 模块化设计，易于维护与扩展

---

## 支持的节点类型

- vmess://
- vless://
- trojan://
- ss://
- ssr://
- hysteria://
- hy2://
- tuic://
- wireguard://

---

## 项目结构

```text
tgbot/
├── main.py            # 程序入口
├── config.py          # config.ini 解析
├── parser.py          # 节点识别与提取
├── forwarder.py       # 转发逻辑
├── logger.py          # 日志模块
├── config.ini         # 主配置文件
├── requirements.txt   # 依赖列表
└── README.md
```

---

## 安装步骤

### 1. 克隆项目

```bash
git clone <repository_url>
cd tgbot
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 获取 Telegram API 凭证

1. 访问 https://my.telegram.org
2. 登录你的 Telegram 账号
3. 点击 "API development tools"
4. 创建应用，获取 `api_id` 和 `api_hash`

### 4. 创建 Bot

1. 在 Telegram 中找到 @BotFather
2. 发送 `/newbot` 创建新机器人
3. 按提示设置名称和用户名
4. 获取 `bot_token`

### 5. 配置 config.ini

编辑 `config.ini` 文件，填入你的配置：

```ini
[telegram]
api_id = 你的API_ID
api_hash = 你的API_HASH
bot_token = 你的BOT_TOKEN

[monitor]
# 要监听的群组 ID（可以有多个，用逗号分隔）
source_chats = -1001234567890,-1009876543210

[forward]
# 转发目标群组 ID
target_chats = -1001234567890

[proxy]
enabled = false
type = socks5
host = 127.0.0.1
port = 1080
username =
password =

[logging]
level = INFO
file = bot.log
```

### 6. 获取群组 ID

要获取群组/频道的 ID，可以：

1. 将 @userinfobot 或 @getidsbot 添加到群组
2. 或者转发群组消息给这些 Bot
3. 超级群/频道 ID 通常以 `-100` 开头

### 7. 将 Bot 添加到群组（重要！）

⚠️ **这一步非常关键，否则会出现 "Peer id invalid" 错误**

1. 将你的 Bot 添加到要监听的**源群组**（需要有读取消息权限）
2. 将你的 Bot 添加到**目标群组**（需要有发送消息权限）
3. 如果是频道，需要将 Bot 设为管理员
4. **使用 @username 格式**（推荐）：
   - 如果频道/群组有用户名，可以直接使用 `@username` 格式
   - 例如：`target_chats = @mychannel`
   - 这比数字 ID 更可靠

### 8. 配置示例

**使用数字 ID：**
```ini
[forward]
target_chats = -1001234567890
```

**使用用户名（推荐）：**
```ini
[forward]
target_chats = @mychannel,@mygroup
```

---

## 运行机器人

```bash
cd tgbot
python main.py
```

或者在项目根目录：

```bash
python tgbot/main.py
```

---

## Bot 命令

| 命令 | 说明 |
|------|------|
| `/start` | 显示欢迎信息和支持的节点类型 |
| `/status` | 查看机器人运行状态 |
| `/help` | 显示帮助信息 |

---

## 配置说明

### [telegram] 节

| 参数 | 说明 |
|------|------|
| api_id | Telegram API ID（从 my.telegram.org 获取） |
| api_hash | Telegram API Hash |
| bot_token | Bot Token（从 @BotFather 获取） |

### [monitor] 节

| 参数 | 说明 |
|------|------|
| source_chats | 要监听的群组/频道 ID，多个用逗号分隔 |

### [forward] 节

| 参数 | 说明 |
|------|------|
| target_chats | 转发目标群组/频道 ID，多个用逗号分隔 |

### [proxy] 节

| 参数 | 说明 |
|------|------|
| enabled | 是否启用代理（true/false） |
| type | 代理类型（socks5/http） |
| host | 代理服务器地址 |
| port | 代理端口 |
| username | 代理用户名（可选） |
| password | 代理密码（可选） |

### [logging] 节

| 参数 | 说明 |
|------|------|
| level | 日志级别（DEBUG/INFO/WARNING/ERROR） |
| file | 日志文件路径 |

---

## 常见问题

### Q: Bot 无法接收群组消息？

A: 确保：
1. Bot 已被添加到群组
2. 群组隐私模式已关闭（在 @BotFather 中使用 `/setprivacy` 设置为 Disabled）
3. config.ini 中的群组 ID 正确

### Q: 转发失败？

A: 检查：
1. Bot 是否有权限在目标群组发送消息
2. 目标群组 ID 是否正确
3. 查看日志文件获取详细错误信息

### Q: 如何使用代理？

A: 在 `config.ini` 中设置：
```ini
[proxy]
enabled = true
type = socks5
host = 127.0.0.1
port = 1080
```

---

## 许可证

MIT License
