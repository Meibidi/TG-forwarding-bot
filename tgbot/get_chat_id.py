"""
获取群组/频道 ID 的辅助脚本
运行后会列出你所有的对话及其 ID
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from pyrogram import Client
from config import load_config


async def main():
    config_path = Path(__file__).parent / "config.ini"
    config = load_config(str(config_path))

    # 创建客户端
    session_path = Path(__file__).parent / config.mode.session_name

    client_params = {
        "name": str(session_path),
        "api_id": config.telegram.api_id,
        "api_hash": config.telegram.api_hash,
    }

    if config.is_bot_mode and config.telegram.bot_token:
        client_params["bot_token"] = config.telegram.bot_token

    if config.proxy.enabled:
        client_params["proxy"] = {
            "scheme": config.proxy.type,
            "hostname": config.proxy.host,
            "port": config.proxy.port,
        }

    app = Client(**client_params)

    async with app:
        print("\n" + "=" * 60)
        print("你的对话列表：")
        print("=" * 60)

        count = 0
        async for dialog in app.get_dialogs():
            count += 1
            chat = dialog.chat
            chat_type = chat.type.name if hasattr(chat.type, 'name') else str(chat.type)

            # 获取标题或名称
            if hasattr(chat, 'title') and chat.title:
                name = chat.title
            elif hasattr(chat, 'first_name'):
                name = chat.first_name
                if hasattr(chat, 'last_name') and chat.last_name:
                    name += f" {chat.last_name}"
            else:
                name = "未知"

            # 获取用户名
            username = f"@{chat.username}" if chat.username else ""

            print(f"{count:3}. [{chat_type:12}] {name}")
            print(f"     ID: {chat.id}")
            if username:
                print(f"     Username: {username}")
            print()

        print("=" * 60)
        print(f"共 {count} 个对话")
        print("\n提示：")
        print("- 群组/频道 ID 以 -100 开头")
        print("- 推荐使用 @username 格式配置")
        print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
