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

    def __init__(
        self,
        client: Client,
        target_chats: List[ChatId],
        forward_mode: str = "extract"
    ):
        """
        初始化转发器

        Args:
            client: Pyrogram 客户端实例
            target_chats: 目标群组 ID 列表
            forward_mode: 转发模式 ('extract' 或 'forward')
        """
        self.client = client
        self.target_chats = target_chats
        self.forward_mode = forward_mode
        self._resolved_chats: Dict[ChatId, bool] = {}
        self._chat_info: Dict[ChatId, str] = {}  # 缓存群组名称

    async def resolve_chat(self, chat_id: ChatId) -> bool:
        """
        解析群组，确保客户端可以访问该群组

        Args:
            chat_id: 群组 ID（数字或 @username）

        Returns:
            是否成功解析
        """
        if chat_id in self._resolved_chats:
            return self._resolved_chats[chat_id]

        try:
            # 尝试获取群组信息来解析 peer
            chat = await self.client.get_chat(chat_id)
            chat_title = getattr(chat, 'title', str(chat_id))
            self._chat_info[chat_id] = chat_title
            logger.info(f"成功解析群组: {chat_title} ({chat_id})")
            self._resolved_chats[chat_id] = True
            return True
        except PeerIdInvalid:
            # 尝试通过获取对话记录来解析
            try:
                logger.info(f"尝试通过对话记录解析 {chat_id}...")
                async for dialog in self.client.get_dialogs():
                    if dialog.chat.id == chat_id or (
                        hasattr(dialog.chat, 'username') and
                        dialog.chat.username and
                        f"@{dialog.chat.username}" == str(chat_id)
                    ):
                        chat_title = getattr(dialog.chat, 'title', str(chat_id))
                        self._chat_info[chat_id] = chat_title
                        logger.info(f"成功解析群组: {chat_title} ({chat_id})")
                        self._resolved_chats[chat_id] = True
                        return True

                logger.error(f"无法解析群组 {chat_id}: 未加入该群组或ID错误")
                logger.error(f"  提示: 请确认已加入该群组，或尝试使用 @username 格式")
                self._resolved_chats[chat_id] = False
                return False
            except Exception as e2:
                logger.error(f"解析群组 {chat_id} 失败: {e2}")
                self._resolved_chats[chat_id] = False
                return False
        except Exception as e:
            logger.error(f"解析群组 {chat_id} 失败: {e}")
            self._resolved_chats[chat_id] = False
            return False

    async def resolve_all_targets(self) -> int:
        """
        预先解析所有目标群组

        Returns:
            成功解析的群组数量
        """
        logger.info("正在解析目标群组...")
        success_count = 0
        for chat_id in self.target_chats:
            if await self.resolve_chat(chat_id):
                success_count += 1

        logger.info(f"目标群组解析完成: {success_count}/{len(self.target_chats)} 个成功")
        return success_count

    async def forward_message(self, message: Message, nodes: Optional[List[str]] = None) -> dict:
        """
        根据配置的模式转发消息

        Args:
            message: 原始消息对象
            nodes: 提取的节点列表（仅 extract 模式需要）

        Returns:
            转发结果统计
        """
        if self.forward_mode == "forward":
            return await self._forward_raw_message(message)
        else:
            return await self._forward_extracted_nodes(nodes or [], message)

    async def _forward_extracted_nodes(
        self,
        nodes: List[str],
        source_message: Optional[Message] = None
    ) -> dict:
        """
        提取节点后重新发送

        Args:
            nodes: 节点链接列表
            source_message: 原始消息对象

        Returns:
            转发结果统计
        """
        if not nodes:
            return {"success": 0, "failed": 0, "details": []}

        # 构建转发消息
        message_text = self._build_message(nodes, source_message)

        return await self._send_to_all_targets(message_text)

    async def _forward_raw_message(self, message: Message) -> dict:
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
            # 检查群组是否已解析
            if not self._resolved_chats.get(chat_id, False):
                if not await self.resolve_chat(chat_id):
                    results["failed"] += 1
                    results["details"].append({
                        "chat_id": chat_id,
                        "status": "failed",
                        "error": "无法解析群组"
                    })
                    continue

            try:
                await message.forward(chat_id)
                results["success"] += 1
                results["details"].append({
                    "chat_id": chat_id,
                    "status": "success"
                })
                chat_name = self._chat_info.get(chat_id, str(chat_id))
                logger.info(f"成功转发到: {chat_name}")

            except FloodWait as e:
                logger.warning(f"FloodWait: 等待 {e.value} 秒")
                await asyncio.sleep(e.value)
                try:
                    await message.forward(chat_id)
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

            except Exception as e:
                results["failed"] += 1
                results["details"].append({
                    "chat_id": chat_id,
                    "status": "failed",
                    "error": str(e)
                })
                logger.error(f"转发消息到 {chat_id} 失败: {e}")

        return results

    async def _send_to_all_targets(self, text: str) -> dict:
        """
        发送消息到所有目标群组

        Args:
            text: 要发送的消息文本

        Returns:
            发送结果统计
        """
        results = {
            "success": 0,
            "failed": 0,
            "details": []
        }

        for chat_id in self.target_chats:
            # 检查群组是否已解析
            if not self._resolved_chats.get(chat_id, False):
                if not await self.resolve_chat(chat_id):
                    results["failed"] += 1
                    results["details"].append({
                        "chat_id": chat_id,
                        "status": "failed",
                        "error": "无法解析群组"
                    })
                    continue

            try:
                await self._send_to_chat(chat_id, text)
                results["success"] += 1
                results["details"].append({
                    "chat_id": chat_id,
                    "status": "success"
                })
                chat_name = self._chat_info.get(chat_id, str(chat_id))
                logger.info(f"成功发送到: {chat_name}")

            except FloodWait as e:
                logger.warning(f"FloodWait: 等待 {e.value} 秒后重试")
                await asyncio.sleep(e.value)
                try:
                    await self._send_to_chat(chat_id, text)
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
                    logger.error(f"重试发送失败 {chat_id}: {retry_error}")

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
                logger.error(f"发送到 {chat_id} 失败: {e}")

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

    # 兼容旧接口
    async def forward_nodes(
        self,
        nodes: List[str],
        source_message: Optional[Message] = None
    ) -> dict:
        """兼容旧接口"""
        return await self._forward_extracted_nodes(nodes, source_message)

    async def forward_raw_message(self, message: Message) -> dict:
        """兼容旧接口"""
        return await self._forward_raw_message(message)
