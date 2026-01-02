"""
Telegram Proxy Node Listener Bot - 主程序入口
基于 Pyrogram 的代理节点监听转发机器人
"""

import sys
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from pyrogram import Client, filters
from pyrogram.types import Message

from typing import Optional
from config import load_config, BotConfig
from parser import extract_nodes, contains_nodes
from forwarder import NodeForwarder
from logger import setup_logger


# 全局变量
config: Optional[BotConfig] = None
logger: Optional[object] = None
forwarder: Optional[NodeForwarder] = None


def create_client(config: BotConfig) -> Client:
    """
    创建 Pyrogram 客户端

    Args:
        config: 机器人配置

    Returns:
        配置好的 Pyrogram 客户端
    """
    # 基本参数
    client_params = {
        "name": "proxy_node_bot",
        "api_id": config.telegram.api_id,
        "api_hash": config.telegram.api_hash,
        "bot_token": config.telegram.bot_token,
    }

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


def main():
    """主函数"""
    global config, logger, forwarder

    # 确定配置文件路径
    config_path = Path(__file__).parent / "config.ini"

    try:
        # 加载配置
        config = load_config(str(config_path))

        # 初始化日志
        logger = setup_logger(
            name="tgbot",
            level=config.logging.level,
            log_file=config.logging.file
        )

        logger.info("=" * 50)
        logger.info("Telegram Proxy Node Listener Bot 启动中...")
        logger.info("=" * 50)

        # 验证配置
        if not config.source_chats:
            logger.error("未配置监听群组 (source_chats)")
            sys.exit(1)

        if not config.target_chats:
            logger.error("未配置目标群组 (target_chats)")
            sys.exit(1)

        logger.info(f"监听群组: {config.source_chats}")
        logger.info(f"目标群组: {config.target_chats}")

        # 创建客户端
        app = create_client(config)

        # 初始化转发器
        forwarder = NodeForwarder(app, config.target_chats)

        # 注册消息处理器
        @app.on_message(filters.chat(config.source_chats) & filters.text)
        async def handle_message(client: Client, message: Message):
            """处理来自监听群组的文本消息"""
            try:
                text = message.text or message.caption or ""

                # 检查是否包含节点
                if not contains_nodes(text):
                    return

                # 提取节点
                nodes = extract_nodes(text)
                if not nodes:
                    return

                chat_title = getattr(message.chat, 'title', '未知群组')
                logger.info(f"从 [{chat_title}] 发现 {len(nodes)} 个节点")

                # 转发节点
                result = await forwarder.forward_nodes(nodes, message)
                logger.info(
                    f"转发完成: 成功 {result['success']}, 失败 {result['failed']}"
                )

            except Exception as e:
                logger.error(f"处理消息时出错: {e}")

        @app.on_message(filters.command("start") & filters.private)
        async def cmd_start(client: Client, message: Message):
            """处理 /start 命令"""
            await message.reply_text(
                "🤖 **Proxy Node Listener Bot**\n\n"
                "我会监听指定群组的消息，自动识别并转发代理节点。\n\n"
                "**支持的节点类型:**\n"
                "• VMess\n"
                "• VLESS\n"
                "• Trojan\n"
                "• Shadowsocks (SS)\n"
                "• ShadowsocksR (SSR)\n"
                "• Hysteria\n"
                "• Hysteria2 (HY2)\n"
                "• TUIC\n"
                "• WireGuard\n\n"
                "使用 /status 查看运行状态"
            )

        @app.on_message(filters.command("status") & filters.private)
        async def cmd_status(client: Client, message: Message):
            """处理 /status 命令"""
            status_text = (
                "📊 **机器人状态**\n\n"
                f"🔍 监听群组数: {len(config.source_chats)}\n"
                f"📤 目标群组数: {len(config.target_chats)}\n"
                f"🌐 代理状态: {'已启用' if config.proxy.enabled else '未启用'}\n"
                f"📝 日志级别: {config.logging.level}\n\n"
                "✅ 机器人运行正常"
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
                "**工作原理:**\n"
                "机器人会自动监听配置中指定的群组，"
                "当发现包含代理节点链接的消息时，"
                "会自动提取并转发到目标群组。"
            )
            await message.reply_text(help_text)

        # 启动机器人
        logger.info("正在连接 Telegram 服务器...")

        # 使用异步启动来预先解析群组
        async def start_bot():
            await app.start()
            logger.info("已连接到 Telegram 服务器")

            # 预先解析所有目标群组
            await forwarder.resolve_all_targets()

            logger.info("机器人已启动，正在监听消息...")

            # 保持运行
            from pyrogram import idle
            await idle()

            await app.stop()

        app.run(start_bot())

    except FileNotFoundError as e:
        print(f"错误: {e}")
        print("请确保 config.ini 文件存在并正确配置")
        sys.exit(1)

    except KeyboardInterrupt:
        logger.info("收到退出信号，正在关闭...")

    except Exception as e:
        if logger:
            logger.error(f"发生错误: {e}")
        else:
            print(f"发生错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
