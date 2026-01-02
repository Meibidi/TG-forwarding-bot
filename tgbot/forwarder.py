"""
转发模块 - 处理消息转发逻辑
"""

import asyncio
from typing import List, Optional, Dict, Union
from pyrogram import Client
from pyrogram.errors import FloodWait, ChatWriteForbidden, ChannelPrivate, PeerIdInvalid
from pyrogram.types import Message

from logger import setup_logger

logger = setup_logger("forwarder")

ChatId = Union[int, str]


class NodeForwarder:
    """节点消息转发器"""

    def __init__(self, client: Client, target_chats: List[ChatId]):
        """
        初始化转发器

        Args:
            client: Pyrogram 客户端实例
            target_chats: 目标群组 ID 列表
        """
        self.client = client
        self.target_chats = target_chats
        self._resolved_chats: Dict[ChatId, bool] = {}

    async def resolve_chat(self, chat_id: ChatId) -> bool:
        """
        解析群组，确保 Bot 可以访问该群组

        Args:
            chat_id: 群组 ID

        Returns:
            是否成功解析
        """
        if chat_id in self._resolved_chats:
            return self._resolved_chats[chat_id]

        try:
            # 尝试获取群组信息来解析 peer
            chat = await self.client.get_chat(chat_id)
            logger.info(f"成功解析群组: {chat.title} ({chat_id})")
            self._resolved_chats[chat_id] = True
            return True
        except PeerIdInvalid:
            logger.error(f"无法解析群组 {chat_id}: Bot 可能未加入该群组")
            self._resolved_chats[chat_id] = False
            return False
        except Exception as e:
            logger.error(f"解析群组 {chat_id} 失败: {e}")
            self._resolved_chats[chat_id] = False
            return False

    async def resolve_all_targets(self):
        """预先解析所有目标群组"""
        logger.info("正在解析目标群组...")
        for chat_id in self.target_chats:
            await self.resolve_chat(chat_id)

    async def forward_nodes(
        self,
        nodes: List[str],
        source_message: Optional[Message] = None
    ) -> dict:
        """
        转发节点到目标群组

        Args:
            nodes: 节点链接列表
            source_message: 原始消息对象（可选）

        Returns:
            转发结果统计 {"success": int, "failed": int, "details": list}
        """
        if not nodes:
            return {"success": 0, "failed": 0, "details": []}

        # 构建转发消息
        message_text = self._build_message(nodes, source_message)

        results = {
            "success": 0,
            "failed": 0,
            "details": []
        }

        for chat_id in self.target_chats:
            try:
                await self._send_to_chat(chat_id, message_text)
                results["success"] += 1
                results["details"].append({
                    "chat_id": chat_id,
                    "status": "success"
                })
                logger.info(f"成功转发到群组: {chat_id}")

            except FloodWait as e:
                # 处理限流
                logger.warning(f"FloodWait: 等待 {e.value} 秒后重试")
                await asyncio.sleep(e.value)
                try:
                    await self._send_to_chat(chat_id, message_text)
                    results["success"] += 1
                    results["details"].append({
                        "chat_id": chat_id,
                        "status": "success"
                    })
                except Exception as retry_error:
                    results["failed"] += 1
                    results["details"].append({
                        "chat_id": chat_id,
                        "status": "failed",
                        "error": str(retry_error)
                    })
                    logger.error(f"重试转发失败 {chat_id}: {retry_error}")

            except ChatWriteForbidden:
                results["failed"] += 1
                results["details"].append({
                    "chat_id": chat_id,
                    "status": "failed",
                    "error": "无权限发送消息"
                })
                logger.error(f"无权限发送消息到群组: {chat_id}")

            except ChannelPrivate:
                results["failed"] += 1
                results["details"].append({
                    "chat_id": chat_id,
                    "status": "failed",
                    "error": "频道已私有或被封禁"
                })
                logger.error(f"无法访问频道: {chat_id}")

            except Exception as e:
                results["failed"] += 1
                results["details"].append({
                    "chat_id": chat_id,
                    "status": "failed",
                    "error": str(e)
                })
                logger.error(f"转发到 {chat_id} 失败: {e}")

        return results

    async def _send_to_chat(self, chat_id: ChatId, text: str) -> Message:
        """
        发送消息到指定群组

        Args:
            chat_id: 群组 ID
            text: 消息文本

        Returns:
            发送的消息对象
        """
        return await self.client.send_message(
            chat_id=chat_id,
            text=text,
            disable_web_page_preview=True
        )

    def _build_message(
        self,
        nodes: List[str],
        source_message: Optional[Message] = None
    ) -> str:
        """
        构建转发消息文本

        Args:
            nodes: 节点链接列表
            source_message: 原始消息对象

        Returns:
            格式化的消息文本
        """
        lines = []

        # 添加来源信息
        if source_message:
            chat_title = getattr(source_message.chat, 'title', '未知群组')
            lines.append(f"📡 来源: {chat_title}")
            lines.append(f"⏰ 时间: {source_message.date}")
            lines.append("")

        # 添加节点信息
        lines.append(f"🔗 发现 {len(nodes)} 个节点:")
        lines.append("")

        for node in nodes:
            lines.append(node)
            lines.append("")

        return "\n".join(lines)

    async def forward_raw_message(self, message: Message) -> dict:
        """
        直接转发原始消息

        Args:
            message: 要转发的消息对象

        Returns:
            转发结果统计
        """
        results = {
            "success": 0,
            "failed": 0,
            "details": []
        }

        for chat_id in self.target_chats:
            try:
                await message.forward(chat_id)
                results["success"] += 1
                results["details"].append({
                    "chat_id": chat_id,
                    "status": "success"
                })
            except FloodWait as e:
                logger.warning(f"FloodWait: 等待 {e.value} 秒")
                await asyncio.sleep(e.value)
                try:
                    await message.forward(chat_id)
                    results["success"] += 1
                except Exception as retry_error:
                    results["failed"] += 1
                    results["details"].append({
                        "chat_id": chat_id,
                        "status": "failed",
                        "error": str(retry_error)
                    })
            except Exception as e:
                results["failed"] += 1
                results["details"].append({
                    "chat_id": chat_id,
                    "status": "failed",
                    "error": str(e)
                })
                logger.error(f"转发消息到 {chat_id} 失败: {e}")

        return results
