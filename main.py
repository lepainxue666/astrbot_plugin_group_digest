from astrbot.api.star import Context, register
from astrbot.api.event import MessageEvent

@register(
    "GroupDigest",
    "xueLepain",
    "群重要消息自动记录与汇总",
    "0.1",
    "https://github.com/lepainxue666/astrbot_plugin_group_digest",
)
class GroupDigest:
    def __init__(self, context: Context):
        self.context = context

    async def on_message(self, event: MessageEvent):
        # 收到任何消息都会进这里
        if event.is_group():
            group_id = event.get_group_id()
            user_id = event.get_user_id()
            text = event.get_plain_text()

            # 测试：群里有人说话就回复一句
            await event.reply(f"已记录群 {group_id} 的消息 👀")
