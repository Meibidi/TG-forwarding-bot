"""
配置模块 - 解析 config.ini 文件
"""

import configparser
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class TelegramConfig:
    """Telegram API 配置"""
    api_id: int
    api_hash: str
    bot_token: str


@dataclass
class ProxyConfig:
    """代理配置"""
    enabled: bool
    type: str
    host: str
    port: int
    username: Optional[str]
    password: Optional[str]


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str
    file: str


from typing import Union


@dataclass
class BotConfig:
    """机器人完整配置"""
    telegram: TelegramConfig
    source_chats: List[Union[int, str]]
    target_chats: List[Union[int, str]]
    proxy: ProxyConfig
    logging: LoggingConfig


def parse_chat_ids(chat_str: str) -> List[Union[int, str]]:
    """
    解析群组 ID 字符串为列表（支持数字 ID 或 @username）

    Args:
        chat_str: 逗号分隔的群组 ID 字符串

    Returns:
        群组 ID 列表（整数或用户名字符串）
    """
    if not chat_str or not chat_str.strip():
        return []

    result = []
    for chat_id in chat_str.split(","):
        chat_id = chat_id.strip()
        if not chat_id:
            continue

        # 如果是 @username 格式
        if chat_id.startswith("@"):
            result.append(chat_id)
        else:
            # 尝试解析为整数
            try:
                result.append(int(chat_id))
            except ValueError:
                # 如果不是数字，当作用户名处理
                result.append(f"@{chat_id}" if not chat_id.startswith("@") else chat_id)

    return result


def load_config(config_path: str = "config.ini") -> BotConfig:
    """
    加载并解析配置文件

    Args:
        config_path: 配置文件路径

    Returns:
        BotConfig 配置对象

    Raises:
        FileNotFoundError: 配置文件不存在
        ValueError: 配置值无效
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    config = configparser.ConfigParser()
    config.read(config_path, encoding="utf-8")

    # 解析 Telegram 配置
    telegram = TelegramConfig(
        api_id=config.getint("telegram", "api_id"),
        api_hash=config.get("telegram", "api_hash"),
        bot_token=config.get("telegram", "bot_token")
    )

    # 解析监听群组
    source_chats = parse_chat_ids(config.get("monitor", "source_chats", fallback=""))

    # 解析目标群组
    target_chats = parse_chat_ids(config.get("forward", "target_chats", fallback=""))

    # 解析代理配置
    proxy_username = config.get("proxy", "username", fallback="")
    proxy_password = config.get("proxy", "password", fallback="")
    proxy = ProxyConfig(
        enabled=config.getboolean("proxy", "enabled", fallback=False),
        type=config.get("proxy", "type", fallback="socks5"),
        host=config.get("proxy", "host", fallback="127.0.0.1"),
        port=config.getint("proxy", "port", fallback=1080),
        username=proxy_username if proxy_username else None,
        password=proxy_password if proxy_password else None
    )

    # 解析日志配置
    logging_config = LoggingConfig(
        level=config.get("logging", "level", fallback="INFO"),
        file=config.get("logging", "file", fallback="bot.log")
    )

    return BotConfig(
        telegram=telegram,
        source_chats=source_chats,
        target_chats=target_chats,
        proxy=proxy,
        logging=logging_config
    )
