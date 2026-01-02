"""
Telegram Proxy Node Listener - 主程序入口
支持 Bot 模式和 User 模式的代理节点监听转发程序
支持自定义群组和自动加载所有群组两种监听模式
"""

import sys
from pathlib import Path
from typing import Optional, List, Dict, Union

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram import idle
from pyrogram.enums import ChatType

from config import load_config, BotConfig
from parser import extract_nodes, contains_nodes
from forwarder import NodeForwarder
from logger import setup_logger


# 全局变量
config: Optional[BotConfig] = None
logger = None
forwarder: Optional[NodeForwarder] = None
app: Optional[Client] = None
chat_id_map: Dict[Union[int, str], dict] = {}  # 群组信息缓存


def create_client(cfg: BotConfig) -> Client:
    """创建 Pyrogram 客户端"""
    session_path = Path(__file__).parent / cfg.mode.session_name

    client_params = {
        "name": str(session_path),
        "api_id": cfg.telegram.api_id,
        "api_hash": cfg.telegram.api_hash,
    }

    if cfg.is_bot_mode:
        if not cfg.telegram.bot_token:
            raise ValueError("Bot 模式需要配置 bot_token")
        client_params["bot_token"] = cfg.telegram.bot_token
        logger.info("运行模式: Bot")
    else:
        logger.info("运行模式: User (Userbot)")
        logger.info("首次运行需要登录验证，请按提示输入手机号和验证码")

    if cfg.proxy.enabled:
        proxy_config = {
            "scheme": cfg.proxy.type,
            "hostname": cfg.proxy.host,
            "port": cfg.proxy.port,
        }
        if cfg.proxy.username and cfg.proxy.password:
            proxy_config["username"] = cfg.proxy.username
            proxy_config["password"] = cfg.proxy.password
        client_params["proxy"] = proxy_config
        logger.info(f"已启用代理: {cfg.proxy.type}://{cfg.proxy.host}:{cfg.proxy.port}")

    return Client(**client_params)


def check_message_filter(text: str, cfg: BotConfig) -> bool:
    """检查消息是否符合过滤条件"""
    if not text:
        return False

    # 排除关键词检查
    if cfg.filter.exclude_keywords:
        for keyword in cfg.filter.exclude_keywords:
            if keyword.lower() in text.lower():
                return False

    # 只转发节点消息
    if cfg.filter.nodes_only:
        if not contains_nodes(text):
            return False
    elif cfg.filter.keywords:
        has_keyword = any(kw.lower() in text.lower() for kw in cfg.filter.keywords)
        if not has_keyword:
            return False

    return True


def get_chat_type_name(chat_type) -> str:
    """获取群组类型名称"""
    type_map = {
        ChatType.CHANNEL: "channel",
        ChatType.SUPERGROUP: "supergroup",
        ChatType.GROUP: "group",
        ChatType.PRIVATE: "private",
        ChatType.BOT: "bot",
    }
    return type_map.get(chat_type, str(chat_type).lower())


def should_monitor_chat(chat, cfg: BotConfig) -> bool:
    """判断是否应该监听该群组"""
    chat_id = chat.id

    # 检查是否在排除列表中
    if chat_id in cfg.monitor.exclude_chats:
        return False
    if hasattr(chat, 'username') and chat.username:
        if f"@{chat.username}" in cfg.monitor.exclude_chats:
            return False

    # 检查群组类型
    if cfg.monitor.chat_types:
        chat_type = get_chat_type_name(chat.type)
        if chat_type not in cfg.monitor.chat_types:
            return False

    # 排除目标群组（避免循环转发）
    if chat_id in cfg.forward.target_chats:
        return False
    if hasattr(chat, 'username') and chat.username:
        if f"@{chat.username}" in cfg.forward.target_chats:
            return False

    return True


async def load_dialogs_and_setup(client: Client, cfg: BotConfig) -> List[int]:
    """
    加载对话列表并设置监听群组

    Returns:
        监听群组 ID 列表
    """
    global chat_id_map

    logger.info("正在同步对话列表...")
    dialog_count = 0
    source_chats = []

    async for dialog in client.get_dialogs():
        dialog_count += 1
        chat = dialog.chat
        chat_id = chat.id

        # 缓存群组信息
        chat_info = {
            "id": chat_id,
            "title": getattr(chat, 'title', getattr(chat, 'first_name', str(chat_id))),
            "username": chat.username,
            "type": get_chat_type_name(chat.type)
        }
        chat_id_map[chat_id] = chat_info
        if chat.username:
            chat_id_map[f"@{chat.username}"] = chat_info

        # 根据模式确定是否监听
        if cfg.is_auto_monitor:
            # 自动模式：根据规则判断
            if should_monitor_chat(chat, cfg):
                source_chats.append(chat_id)
        else:
            # 自定义模式：检查是否在配置列表中
            if chat_id in cfg.monitor.source_chats:
                source_chats.append(chat_id)
            elif chat.username and f"@{chat.username}" in cfg.monitor.source_chats:
                source_chats.append(chat_id)

    logger.info(f"已加载 {dialog_count} 个对话")
    return source_chats


def register_handlers(client: Client, cfg: BotConfig, fwd: NodeForwarder, source_chats: List[int]):
    """注册消息处理器"""

    # 使用 filters.chat 来过滤监听的群组
    if source_chats:
        chat_filter = filters.chat(source_chats)
    else:
        # 如果没有群组，使用一个永远不匹配的过滤器
        chat_filter = filters.chat([0])

    @client.on_message(chat_filter)
    async def handle_message(c: Client, message: Message):
        """处理来自监听群组的消息"""
        try:
            text = message.text or message.caption or ""

            if not check_message_filter(text, cfg):
                return

            nodes: List[str] = []
            if cfg.filter.nodes_only or cfg.forward.forward_mode == "extract":
                nodes = extract_nodes(text)
                if cfg.filter.nodes_only and not nodes:
                    return

            chat_title = getattr(message.chat, 'title', '未知群组')

            if nodes:
                logger.info(f"从 [{chat_title}] 发现 {len(nodes)} 个节点")
            else:
                logger.info(f"从 [{chat_title}] 收到符合条件的消息")

            result = await fwd.forward_message(message, nodes)
            logger.info(f"转发完成: 成功 {result['success']}, 失败 {result['failed']}")

        except Exception as e:
            logger.error(f"处理消息时出错: {e}")

    # Bot 模式命令
    if cfg.is_bot_mode:
        @client.on_message(filters.command("start") & filters.private)
        async def cmd_start(c: Client, message: Message):
            mode_text = "Bot 模式" if cfg.is_bot_mode else "用户模式"
            monitor_mode = "自动加载" if cfg.is_auto_monitor else "自定义"
            await message.reply_text(
                f"🤖 **Telegram 消息转发器**\n\n"
                f"运行模式: {mode_text}\n"
                f"监听模式: {monitor_mode}\n"
                f"监听群组数: {len(source_chats)}\n\n"
                "使用 /status 查看详细状态"
            )

        @client.on_message(filters.command("status") & filters.private)
        async def cmd_status(c: Client, message: Message):
            forward_mode = "提取节点" if cfg.forward.forward_mode == "extract" else "直接转发"
            nodes_only = "是" if cfg.filter.nodes_only else "否"
            monitor_mode = "自动加载" if cfg.is_auto_monitor else "自定义"

            status_text = (
                "📊 **运行状态**\n\n"
                f"🔄 运行模式: {'Bot' if cfg.is_bot_mode else 'User'}\n"
                f"📡 监听模式: {monitor_mode}\n"
                f"🔍 监听群组数: {len(source_chats)}\n"
                f"📤 目标群组数: {len(cfg.forward.target_chats)}\n"
                f"📋 转发模式: {forward_mode}\n"
                f"🔗 仅节点消息: {nodes_only}\n"
                f"🌐 代理状态: {'已启用' if cfg.proxy.enabled else '未启用'}\n\n"
                "✅ 运行正常"
            )
            await message.reply_text(status_text)

        @client.on_message(filters.command("list") & filters.private)
        async def cmd_list(c: Client, message: Message):
            """列出监听的群组"""
            if not source_chats:
                await message.reply_text("当前没有监听任何群组")
                return

            lines = ["📋 **监听群组列表**\n"]
            for i, chat_id in enumerate(source_chats[:20], 1):
                info = chat_id_map.get(chat_id, {})
                title = info.get('title', str(chat_id))
                chat_type = info.get('type', 'unknown')
                lines.append(f"{i}. [{chat_type}] {title}")

            if len(source_chats) > 20:
                lines.append(f"\n... 等共 {len(source_chats)} 个群组")

            await message.reply_text("\n".join(lines))


async def start_app():
    """启动应用"""
    global app, forwarder, config, chat_id_map

    await app.start()

    # 获取当前用户信息
    me = await app.get_me()
    if config.is_bot_mode:
        logger.info(f"已登录: @{me.username} (Bot)")
    else:
        name = me.first_name or ""
        if me.last_name:
            name += f" {me.last_name}"
        username = f"@{me.username}" if me.username else ""
        logger.info(f"已登录: {name} {username}")

    # 加载对话并确定监听群组
    source_chats = await load_dialogs_and_setup(app, config)

    if config.is_auto_monitor:
        logger.info(f"自动监听模式: 已加载 {len(source_chats)} 个群组")
        if config.monitor.chat_types:
            logger.info(f"  群组类型过滤: {', '.join(config.monitor.chat_types)}")
        if config.monitor.exclude_chats:
            logger.info(f"  排除群组数: {len(config.monitor.exclude_chats)}")
    else:
        logger.info(f"自定义监听模式: {len(source_chats)} 个群组")

    # 显示监听群组
    logger.info("监听群组列表:")
    for chat_id in source_chats[:10]:
        info = chat_id_map.get(chat_id, {})
        title = info.get('title', str(chat_id))
        chat_type = info.get('type', 'unknown')
        logger.info(f"  ✓ [{chat_type}] {title}")
    if len(source_chats) > 10:
        logger.info(f"  ... 等共 {len(source_chats)} 个群组")

    # 解析目标群组
    logger.info("目标群组列表:")
    for chat_id in config.forward.target_chats:
        if chat_id in chat_id_map:
            info = chat_id_map[chat_id]
            logger.info(f"  ✓ {info['title']}")
            forwarder._resolved_chats[chat_id] = True
            forwarder._chat_info[chat_id] = info['title']
        else:
            logger.warning(f"  ✗ 未找到 {chat_id}")
            forwarder._resolved_chats[chat_id] = False

    if not source_chats:
        logger.warning("警告: 没有可监听的群组！")

    # 注册处理器
    register_handlers(app, config, forwarder, source_chats)

    logger.info("=" * 50)
    logger.info("启动完成，正在监听消息...")
    logger.info("按 Ctrl+C 退出")
    logger.info("=" * 50)

    await idle()
    await app.stop()
    logger.info("程序已退出")


def main():
    """主函数"""
    global config, logger, forwarder, app

    config_path = Path(__file__).parent / "config.ini"

    try:
        config = load_config(str(config_path))

        log_file = Path(__file__).parent / config.logging.file
        logger = setup_logger(
            name="tgbot",
            level=config.logging.level,
            log_file=str(log_file)
        )

        logger.info("=" * 50)
        logger.info("Telegram 消息转发器启动中...")
        logger.info("=" * 50)

        # 验证配置
        if not config.is_auto_monitor and not config.monitor.source_chats:
            logger.error("自定义模式下未配置监听群组 (source_chats)")
            logger.info("提示: 设置 monitor_mode = auto 可自动加载所有群组")
            sys.exit(1)

        if not config.forward.target_chats:
            logger.error("未配置目标群组 (target_chats)")
            sys.exit(1)

        monitor_mode = "自动加载" if config.is_auto_monitor else "自定义"
        logger.info(f"监听模式: {monitor_mode}")
        logger.info(f"目标群组数: {len(config.forward.target_chats)}")
        logger.info(f"转发模式: {config.forward.forward_mode}")

        app = create_client(config)

        forwarder = NodeForwarder(
            app,
            config.forward.target_chats,
            config.forward.forward_mode
        )

        logger.info("正在连接 Telegram 服务器...")
        app.run(start_app())

    except FileNotFoundError as e:
        print(f"错误: {e}")
        print("请确保 config.ini 文件存在并正确配置")
        sys.exit(1)

    except ValueError as e:
        if logger:
            logger.error(f"配置错误: {e}")
        else:
            print(f"配置错误: {e}")
        sys.exit(1)

    except KeyboardInterrupt:
        if logger:
            logger.info("收到退出信号")

    except Exception as e:
        if logger:
            logger.error(f"发生错误: {e}")
        else:
            print(f"发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
