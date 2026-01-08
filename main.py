from datetime import datetime, timedelta
from collections import defaultdict

from astrbot.api.event import GroupMessageEvent, PrivateMessageEvent
from astrbot.api.context import Context
from astrbot.api.plugin import register
from astrbot.api.scheduler import scheduler


# ===== 内存中的重要消息存储 =====
# 结构：
# {
#   "YYYY-MM-DD": [
#       {
#           "time": "HH:MM",
#           "group_id": int,
#           "group_name": str,
#           "sender": str,
#           "content": str
#       }
#   ]
# }
important_messages = defaultdict(list)


def _today_str():
    return datetime.now().strftime("%Y-%m-%d")


def _is_important(event: GroupMessageEvent) -> bool:
    """
    判定是否为重要消息
    """
    # @全体
    if event.is_at_all:
        return True

    # @机器人
    if event.is_at_bot:
        return True

    return False


@register.on_group_message()
async def on_group_message(ctx: Context, event: GroupMessageEvent):
    """
    监听群消息，记录重要消息
    """
    if not _is_important(event):
        return

    day = _today_str()

    important_messages[day].append({
        "time": datetime.now().strftime("%H:%M"),
        "group_id": event.group_id,
        "group_name": event.group_name,
        "sender": event.sender_name,
        "content": event.message
    })


def _collect_digest(days: int) -> str:
    """
    汇总最近 N 天的重要消息
    """
    if days <= 0:
        days = 1

    now = datetime.now()
    lines = []

    for i in range(days):
        day = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        records = important_messages.get(day, [])

        if not records:
            continue

        lines.append(f"\n📅 {day}")
        for r in records:
            lines.append(
                f"[{r['time']}] "
                f"{r['group_name']} | {r['sender']}：{r['content']}"
            )

    if not lines:
        return "最近没有记录到重要消息。"

    return "最近的重要消息汇总：" + "\n".join(lines)


@register.on_private_message()
async def on_private_message(ctx: Context, event: PrivateMessageEvent):
    """
    处理主动查询命令
    """
    text = event.message.strip()

    if not text.startswith("最近重要消息"):
        return

    # 默认 1 天
    days = 1

    # 解析“最近重要消息 3天”
    parts = text.split()
    if len(parts) == 2 and parts[1].endswith("天"):
        num = parts[1][:-1]
        if num.isdigit():
            days = int(num)

    digest = _collect_digest(days)

    await ctx.send_private_message(
        user_id=event.user_id,
        message=digest
    )


# ===== 每日定时自动汇总（可选，但你之前提过） =====
@scheduler.scheduled_job("cron", hour=21, minute=0)
async def daily_digest():
    """
    每天 21:00 自动向所有好友发送当天汇总
    """
    digest = _collect_digest(1)

    if "没有记录" in digest:
        return

    ctx = Context.get_global()

    for friend_id in ctx.get_friend_list():
        await ctx.send_private_message(
            user_id=friend_id,
            message=digest
        )
