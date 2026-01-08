from datetime import datetime, timedelta
from typing import List

from astrbot.api.event import GroupMessageEvent, PrivateMessageEvent
from astrbot.api.star import Star, register
from astrbot.api.context import Context


@register(
    name="astrbot_plugin_group_digest",
    description="群重要消息自动记录与汇总",
    version="0.1.0",
    author="xue Lepain"
)
class GroupDigestPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        # 内存存储（最小可用，后续可换 sqlite）
        self.records: List[dict] = []

    # ========== 群消息监听 ==========
    async def on_group_message(self, event: GroupMessageEvent):
        msg = event.message
        sender = event.sender
        group = event.group

        is_at_me = event.is_at_me
        is_at_all = event.is_at_all

        if not (is_at_me or is_at_all):
            return  # 非重要消息直接忽略

        record = {
            "group_id": group.id,
            "group_name": group.name,
            "sender_id": sender.id,
            "sender_name": sender.nickname,
            "content": msg.plain_text,
            "time": datetime.now(),
        }

        self.records.append(record)

    # ========== 私聊指令 ==========
    async def on_private_message(self, event: PrivateMessageEvent):
        text = event.message.plain_text.strip()

        if not text.startswith("最近重要消息"):
            return

        days = 1
        parts = text.split()
        if len(parts) >= 2:
            try:
                days = int(parts[1].replace("天", ""))
            except ValueError:
                pass

        since = datetime.now() - timedelta(days=days)
        msgs = [r for r in self.records if r["time"] >= since]

        if not msgs:
            await event.reply("📭 最近没有记录到重要消息")
            return

        lines = [f"📌 最近 {days} 天的重要消息：\n"]
        for r in msgs[-20:]:
            lines.append(
                f"[{r['time'].strftime('%m-%d %H:%M')}] "
                f"{r['group_name']} / {r['sender_name']}：\n"
                f"{r['content']}\n"
            )

        await event.reply("\n".join(lines))
