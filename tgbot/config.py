"""
配置模块 - 解析 config.ini 文件
"""

import configparser
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Union, Set


@dataclass
class TelegramConfig:
    """Telegram API 配置"""
    api_id: int
    api_hash: str
    bot_token: Optional[str]


@dataclass
class ModeConfig:
    """运行模式配置"""
    run_mode: str  # 'bot' 或 'user'
    session_name: str


@dataclass
class MonitorConfig:
    """监听配置"""
    monitor_mode: str  # 'custom' 或 'auto'
    source_chats: List[Union[int, str]]
    exclude_chats: List[Union[int, str]]
    chat_types: Set[str]  # 要监听的群组类型


@dataclass
class ForwardConfig:
    """转发配置"""
    target_chats: List[Union[int, str]]
    forward_mode: str  # 'extract' 或 'forward'


@dataclass
class FilterConfig:
    """过滤配置"""
    nodes_only: bool
    keywords: List[str]
    exclude_keywords: List[str]


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


@dataclass
class BotConfig:
    """机器人完整配置"""
    telegram: TelegramConfig
    mode: ModeConfig
    monitor: MonitorConfig
    forward: ForwardConfig
    filter: FilterConfig
    proxy: ProxyConfig
    logging: LoggingConfig

    # 运行时填充的动态群组列表
    _dynamic_source_chats: List[Union[int, str]] = field(default_factory=list)

    @property
    def is_bot_mode(self) -> bool:
        """是否为 Bot 模式"""
        return self.mode.run_mode.lower() == 'bot'

    @property
    def is_user_mode(self) -> bool:
        """是否为用户模式"""
        return self.mode.run_mode.lower() == 'user'

    @property
    def is_auto_monitor(self) -> bool:
        """是否为自动监听模式"""
        return self.monitor.monitor_mode.lower() == 'auto'

    @property
    def source_chats(self) -> List[Union[int, str]]:
        """获取监听群组列表"""
        if self.is_auto_monitor and self._dynamic_source_chats:
            return self._dynamic_source_chats
        return self.monitor.source_chats

    def set_dynamic_chats(self, chats: List[Union[int, str]]):
        """设置动态群组列表（auto 模式使用）"""
        self._dynamic_source_chats = chats


def parse_chat_ids(chat_str: str) -> List[Union[int, str]]:
    """
    解析群组 ID 字符串为列表（支持数字 ID 或 @username）
    """
    if not chat_str or not chat_str.strip():
        return []

    result = []
    for chat_id in chat_str.split(","):
        chat_id = chat_id.strip()
        if not chat_id:
            continue

        if chat_id.startswith("@"):
            result.append(chat_id)
        else:
            try:
                result.append(int(chat_id))
            except ValueError:
                result.append(f"@{chat_id}" if not chat_id.startswith("@") else chat_id)

    return result


def parse_keywords(keyword_str: str) -> List[str]:
    """解析关键词字符串为列表"""
    if not keyword_str or not keyword_str.strip():
        return []
    return [kw.strip() for kw in keyword_str.split(",") if kw.strip()]


def parse_chat_types(type_str: str) -> Set[str]:
    """解析群组类型字符串为集合"""
    if not type_str or not type_str.strip():
        return set()  # 空集合表示所有类型
    return {t.strip().lower() for t in type_str.split(",") if t.strip()}


def load_config(config_path: str = "config.ini") -> BotConfig:
    """
    加载并解析配置文件
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    config = configparser.ConfigParser()
    config.read(config_path, encoding="utf-8")

    # 解析 Telegram 配置
    bot_token = config.get("telegram", "bot_token", fallback="").strip()
    telegram = TelegramConfig(
        api_id=config.getint("telegram", "api_id"),
        api_hash=config.get("telegram", "api_hash"),
        bot_token=bot_token if bot_token else None
    )

    # 解析模式配置
    mode = ModeConfig(
        run_mode=config.get("mode", "run_mode", fallback="bot").strip().lower(),
        session_name=config.get("mode", "session_name", fallback="tg_forwarder").strip()
    )

    # 解析监听配置
    monitor = MonitorConfig(
        monitor_mode=config.get("monitor", "monitor_mode", fallback="custom").strip().lower(),
        source_chats=parse_chat_ids(config.get("monitor", "source_chats", fallback="")),
        exclude_chats=parse_chat_ids(config.get("monitor", "exclude_chats", fallback="")),
        chat_types=parse_chat_types(config.get("monitor", "chat_types", fallback=""))
    )

    # 解析转发配置
    forward = ForwardConfig(
        target_chats=parse_chat_ids(config.get("forward", "target_chats", fallback="")),
        forward_mode=config.get("forward", "forward_mode", fallback="extract").strip().lower()
    )

    # 解析过滤配置
    filter_config = FilterConfig(
        nodes_only=config.getboolean("filter", "nodes_only", fallback=True),
        keywords=parse_keywords(config.get("filter", "keywords", fallback="")),
        exclude_keywords=parse_keywords(config.get("filter", "exclude_keywords", fallback=""))
    )

    # 解析代理配置
    proxy_username = config.get("proxy", "username", fallback="").strip()
    proxy_password = config.get("proxy", "password", fallback="").strip()
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
        mode=mode,
        monitor=monitor,
        forward=forward,
        filter=filter_config,
        proxy=proxy,
        logging=logging_config
    )
