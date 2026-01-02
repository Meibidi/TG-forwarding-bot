"""
节点解析模块 - 识别和提取代理节点链接
"""

import re
from typing import List, Set


# 支持的节点协议前缀
SUPPORTED_PROTOCOLS: Set[str] = {
    "vmess://",
    "vless://",
    "trojan://",
    "ss://",
    "ssr://",
    "hysteria://",
    "hy2://",
    "tuic://",
    "wireguard://"
}

# 节点链接正则表达式模式
# 匹配格式: 协议://base64或其他编码内容
NODE_PATTERN = re.compile(
    r'((?:vmess|vless|trojan|ss|ssr|hysteria|hy2|tuic|wireguard)://[A-Za-z0-9+/=_\-@:.#?&%]+)',
    re.IGNORECASE
)


def extract_nodes(text: str) -> List[str]:
    """
    从文本中提取所有代理节点链接

    Args:
        text: 要解析的文本内容

    Returns:
        提取到的节点链接列表（去重）
    """
    if not text:
        return []

    # 查找所有匹配的节点链接
    matches = NODE_PATTERN.findall(text)

    # 去重并保持顺序
    seen: Set[str] = set()
    nodes: List[str] = []
    for node in matches:
        # 清理节点链接（去除末尾可能的无效字符）
        node = clean_node(node)
        if node and node not in seen:
            seen.add(node)
            nodes.append(node)

    return nodes


def clean_node(node: str) -> str:
    """
    清理节点链接，去除无效字符

    Args:
        node: 原始节点链接

    Returns:
        清理后的节点链接
    """
    if not node:
        return ""

    # 去除末尾的标点符号和空白
    node = node.rstrip('.,;:!?\'"）)】》> \t\n\r')

    # 验证协议前缀
    node_lower = node.lower()
    for protocol in SUPPORTED_PROTOCOLS:
        if node_lower.startswith(protocol):
            return node

    return ""


def is_valid_node(node: str) -> bool:
    """
    验证节点链接是否有效

    Args:
        node: 节点链接

    Returns:
        是否为有效的节点链接
    """
    if not node:
        return False

    node_lower = node.lower()
    for protocol in SUPPORTED_PROTOCOLS:
        if node_lower.startswith(protocol):
            # 确保协议后面有内容
            content = node[len(protocol):]
            return len(content) > 0

    return False


def get_node_protocol(node: str) -> str:
    """
    获取节点的协议类型

    Args:
        node: 节点链接

    Returns:
        协议名称（小写），如 vmess, vless 等
    """
    if not node:
        return ""

    node_lower = node.lower()
    for protocol in SUPPORTED_PROTOCOLS:
        if node_lower.startswith(protocol):
            return protocol.rstrip("://")

    return ""


def contains_nodes(text: str) -> bool:
    """
    检查文本是否包含节点链接

    Args:
        text: 要检查的文本

    Returns:
        是否包含节点链接
    """
    if not text:
        return False

    return bool(NODE_PATTERN.search(text))


def format_nodes_message(nodes: List[str]) -> str:
    """
    格式化节点列表为消息文本

    Args:
        nodes: 节点链接列表

    Returns:
        格式化后的消息文本
    """
    if not nodes:
        return ""

    lines = [f"🔗 发现 {len(nodes)} 个节点:\n"]
    for i, node in enumerate(nodes, 1):
        protocol = get_node_protocol(node)
        lines.append(f"{i}. [{protocol.upper()}] {node[:50]}...")

    return "\n".join(lines)
