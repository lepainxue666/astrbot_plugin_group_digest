import time
from datetime import datetime, timedelta
from typing import List, Dict

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent
from astrbot.api.event import filter
from astrbot.api.message_components import Plain, At
from astrbot.api.star import Context, Star, register


# 内存缓存（最小可用版，后面可换 SQLite）
IMPORTANT_MESSAGES: List[Dict] = []


@register(
    "GroupDigest",
    "xueLepain",
    "群重要消息自动记录与汇总",
    "0.1",
    "https://github.com/lepainxue666/astrbot_plugin_group_digest”，
)
class GroupDigestPlugin(Star):

    def __init__(self, context: Context, config=None):
        super().__init__(context)
        self.config = config or {}
        logger.info("GroupDigest 插件已加载")

    # =========================
    # 群消息监听
    # =========================
    @filter.event_message_type(filter.EventMessageType.GROUP)
    async def on_group_message(self, event: AstrMessageEvent):
        """
        监听所有群消息，记录重要消息
        """
        message = event.message_obj.message
        group_id = event.get_group_id()
        sender_id = event.get_sender_id()
        sender_name = event.get_sender_name()

        is_important = False
        text_content = ""

        for comp in message:
            if isinstance(comp, Plain):
                text_content += comp.text
            elif isinstance(comp, At):
                # @全体 或 @我
                if comp.qq == "all" or str(comp.qq) == str(event.get_self_id()):
                    is_important = True

        if not is_important:
            return

        IMPORTANT_MESSAGES.append({
            "time": time.time(),
            "group_id": group_id,
            "sender_id": sender_id,
            "sender_name": sender_name,
            "content": text_content.strip(),
        })

        logger.info(f"记录重要消息: {sender_name} @ 群 {group_id}")

    # =========================
    # 私聊命令：最近重要消息
    # =========================
    @filter.event_message_type(filter.EventMessageType.PRIVATE)
    async def on_private_message(self, event: AstrMessageEvent):
        message = event.message_obj.message
        text = ""

        for comp in message:
            if isinstance(comp, Plain):
                text += comp.text.strip()

        if not text.startswith("最近重要消息"):
            return

        # 默认 1 天
        days = 1
        parts = text.split()
        if len(parts) >= 2:
            try:
                days = int(parts[1].replace("天", ""))
            except ValueError:
                pass

        since = time.time() - days * 86400
        records = [m for m in IMPORTANT_MESSAGES if m["time"] >= since]

        if not records:
            await self.context.send_message(
                event.get_session_id(),
                "最近没有重要消息 🙂"
            )
            return

        lines = []
        for m in records[-20:]:
            t = datetime.fromtimestamp(m["time"]).strftime("%m-%d %H:%M")
            lines.append(
                f"[{t}] {m['sender_name']}：{m['content']}"
            )

        await self.context.send_message(
            event.get_session_id(),
            "\n".join(lines)
        )

