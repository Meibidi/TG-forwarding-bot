"""
Telegram Proxy Node Listener - 主程序入口
支持 Bot 模式和 User 模式的代理节点监听转发程序
"""

import sys
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram import idle

from typing import Optional, List
from config import load_config, BotConfig
from parser import extract_nodes, contains_nodes
from forwarder import NodeForwarder
from logger import setup_logger


# 全局变量
config: Optional[BotConfig] = None
logger = None
forwarder: Optional[NodeForwarder] = None
app: Optional[Client] = None


def create_client(config: BotConfig) -> Client:
    """
    创建 Pyrogram 客户端

    Args:
        config: 配置对象

    Returns:
        配置好的 Pyrogram 客户端
    """
    # 获取 session 文件路径
    session_path = Path(__file__).parent / config.mode.session_name

    # 基本参数
    client_params = {
        "name": str(session_path),
        "api_id": config.telegram.api_id,
        "api_hash": config.telegram.api_hash,
    }

    # 根据模式添加不同的参数
    if config.is_bot_mode:
        if not config.telegram.bot_token:
            raise ValueError("Bot 模式需要配置 bot_token")
        client_params["bot_token"] = config.telegram.bot_token
        logger.info("运行模式: Bot")
    else:
        logger.info("运行模式: User (Userbot)")
        logger.info("首次运行需要登录验证，请按提示输入手机号和验证码")

    # 代理配置
    if config.proxy.enabled:
        proxy_config = {
            "scheme": config.proxy.type,
            "hostname": config.proxy.host,
            "port": config.proxy.port,
        }
        if config.proxy.username and config.proxy.password:
            proxy_config["username"] = config.proxy.username
            proxy_config["password"] = config.proxy.password

        client_params["proxy"] = proxy_config
        logger.info(f"已启用代理: {config.proxy.type}://{config.proxy.host}:{config.proxy.port}")

    return Client(**client_params)


def check_message_filter(text: str, config: BotConfig) -> bool:
    """
    检查消息是否符合过滤条件

    Args:
        text: 消息文本
        config: 配置对象

    Returns:
        是否应该处理该消息
    """
    if not text:
        return False

    # 排除关键词检查
    if config.filter.exclude_keywords:
        for keyword in config.filter.exclude_keywords:
            if keyword.lower() in text.lower():
                return False

    # 只转发节点消息
    if config.filter.nodes_only:
        if not contains_nodes(text):
            return False
    # 关键词过滤
    elif config.filter.keywords:
        has_keyword = any(
            kw.lower() in text.lower()
            for kw in config.filter.keywords
        )
        if not has_keyword:
            return False

    return True


def register_handlers(app: Client, config: BotConfig, forwarder: NodeForwarder):
    """
    注册消息处理器

    Args:
        app: Pyrogram 客户端
        config: 配置对象
        forwarder: 转发器对象
    """

    @app.on_message(filters.chat(config.source_chats))
    async def handle_message(client: Client, message: Message):
        """处理来自监听群组的消息"""
        try:
            # 获取消息文本
            text = message.text or message.caption or ""

            # 检查消息过滤
            if not check_message_filter(text, config):
                return

            # 提取节点（如果需要）
            nodes: List[str] = []
            if config.filter.nodes_only or config.forward.forward_mode == "extract":
                nodes = extract_nodes(text)
                if config.filter.nodes_only and not nodes:
                    return

            chat_title = getattr(message.chat, 'title', '未知群组')

            if nodes:
                logger.info(f"从 [{chat_title}] 发现 {len(nodes)} 个节点")
            else:
                logger.info(f"从 [{chat_title}] 收到符合条件的消息")

            # 转发消息
            result = await forwarder.forward_message(message, nodes)
            logger.info(
                f"转发完成: 成功 {result['success']}, 失败 {result['failed']}"
            )

        except Exception as e:
            logger.error(f"处理消息时出错: {e}")

    # Bot 模式特有的命令处理
    if config.is_bot_mode:
        @app.on_message(filters.command("start") & filters.private)
        async def cmd_start(client: Client, message: Message):
            """处理 /start 命令"""
            mode_text = "Bot 模式" if config.is_bot_mode else "用户模式"
            await message.reply_text(
                f"🤖 **Telegram 消息转发器**\n\n"
                f"当前运行模式: {mode_text}\n\n"
                "我会监听指定群组的消息，自动识别并转发代理节点。\n\n"
                "**支持的节点类型:**\n"
                "• VMess / VLESS\n"
                "• Trojan\n"
                "• Shadowsocks (SS/SSR)\n"
                "• Hysteria / Hysteria2\n"
                "• TUIC / WireGuard\n\n"
                "使用 /status 查看运行状态\n"
                "使用 /help 查看帮助"
            )

        @app.on_message(filters.command("status") & filters.private)
        async def cmd_status(client: Client, message: Message):
            """处理 /status 命令"""
            forward_mode = "提取节点" if config.forward.forward_mode == "extract" else "直接转发"
            nodes_only = "是" if config.filter.nodes_only else "否"

            status_text = (
                "📊 **运行状态**\n\n"
                f"🔄 运行模式: {'Bot' if config.is_bot_mode else 'User'}\n"
                f"🔍 监听群组数: {len(config.source_chats)}\n"
                f"📤 目标群组数: {len(config.forward.target_chats)}\n"
                f"📋 转发模式: {forward_mode}\n"
                f"🔗 仅节点消息: {nodes_only}\n"
                f"🌐 代理状态: {'已启用' if config.proxy.enabled else '未启用'}\n\n"
                "✅ 运行正常"
            )
            await message.reply_text(status_text)

        @app.on_message(filters.command("help") & filters.private)
        async def cmd_help(client: Client, message: Message):
            """处理 /help 命令"""
            help_text = (
                "📖 **帮助信息**\n\n"
                "**可用命令:**\n"
                "/start - 显示欢迎信息\n"
                "/status - 查看运行状态\n"
                "/help - 显示此帮助\n\n"
                "**配置说明:**\n"
                "• `run_mode`: bot 或 user\n"
                "• `forward_mode`: extract 或 forward\n"
                "• `nodes_only`: 是否只转发节点消息\n\n"
                "详细配置请查看 config.ini 文件"
            )
            await message.reply_text(help_text)


async def start_app():
    """启动应用"""
    global app, forwarder

    await app.start()

    # 获取当前用户/机器人信息
    me = await app.get_me()
    if config.is_bot_mode:
        logger.info(f"已登录: @{me.username} (Bot)")
    else:
        name = me.first_name
        if me.last_name:
            name += f" {me.last_name}"
        username = f"@{me.username}" if me.username else ""
        logger.info(f"已登录: {name} {username}")

    # User 模式下，先获取对话列表来缓存 peer 信息
    if config.is_user_mode:
        logger.info("正在同步对话列表（首次可能较慢）...")
        dialog_count = 0
        chat_map = {}  # 用于快速查找
        async for dialog in app.get_dialogs():
            dialog_count += 1
            chat_map[dialog.chat.id] = dialog.chat
            if hasattr(dialog.chat, 'username') and dialog.chat.username:
                chat_map[f"@{dialog.chat.username}"] = dialog.chat
        logger.info(f"已加载 {dialog_count} 个对话")

        # 解析监听群组
        logger.info("正在解析监听群组...")
        for chat_id in config.source_chats:
            if chat_id in chat_map:
                chat = chat_map[chat_id]
                title = getattr(chat, 'title', getattr(chat, 'first_name', str(chat_id)))
                logger.info(f"  ✓ {title} ({chat.id})")
            else:
                logger.warning(f"  ✗ 未找到 {chat_id}（请确认已加入该群组）")

        # 解析目标群组
        logger.info("正在解析目标群组...")
        for chat_id in config.forward.target_chats:
            if chat_id in chat_map:
                chat = chat_map[chat_id]
                title = getattr(chat, 'title', getattr(chat, 'first_name', str(chat_id)))
                logger.info(f"  ✓ {title} ({chat.id})")
                forwarder._resolved_chats[chat_id] = True
                forwarder._chat_info[chat_id] = title
            else:
                logger.warning(f"  ✗ 未找到 {chat_id}（请确认已加入该群组）")
                forwarder._resolved_chats[chat_id] = False
    else:
        # Bot 模式使用原来的解析方式
        await forwarder.resolve_all_targets()

        logger.info("正在解析监听群组...")
        for chat_id in config.source_chats:
            try:
                chat = await app.get_chat(chat_id)
                logger.info(f"  ✓ {chat.title} ({chat_id})")
            except Exception as e:
                logger.warning(f"  ✗ 无法解析 {chat_id}: {e}")

    logger.info("=" * 50)
    logger.info("启动完成，正在监听消息...")
    logger.info("按 Ctrl+C 退出")
    logger.info("=" * 50)

    # 保持运行
    await idle()

    await app.stop()
    logger.info("程序已退出")


def main():
    """主函数"""
    global config, logger, forwarder, app

    # 确定配置文件路径
    config_path = Path(__file__).parent / "config.ini"

    try:
        # 加载配置
        config = load_config(str(config_path))

        # 初始化日志
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
        if not config.source_chats:
            logger.error("未配置监听群组 (source_chats)")
            sys.exit(1)

        if not config.forward.target_chats:
            logger.error("未配置目标群组 (target_chats)")
            sys.exit(1)

        logger.info(f"监听群组数: {len(config.source_chats)}")
        logger.info(f"目标群组数: {len(config.forward.target_chats)}")
        logger.info(f"转发模式: {config.forward.forward_mode}")

        # 创建客户端
        app = create_client(config)

        # 初始化转发器
        forwarder = NodeForwarder(
            app,
            config.forward.target_chats,
            config.forward.forward_mode
        )

        # 注册处理器
        register_handlers(app, config, forwarder)

        # 启动
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
