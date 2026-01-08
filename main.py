import asyncio
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register

@register(
    "GroupDigest",
    "xueLepain",
    "群重要消息自动记录与汇总",
    "0.1.0",
    "https://github.com/lepainxue666/astrbot_plugin_group_digest",
)
class GroupDigest(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.user_id = self.config.get("user_id", "")
        self.message_list = []
        self.last_digest_date = ""

    async def initialize(self):
        """插件初始化方法"""
        self.message_list = self.get_kv_data("message_list", [])
        self.last_digest_date = self.get_kv_data("last_digest_date", "")
        logger.info("群消息汇总插件：初始化成功")
        
        if self.config.get("enable_daily_digest", True):
            asyncio.create_task(self._daily_digest_loop())
            logger.info(f"群消息汇总插件：每日汇总已启用，时间：{self.config.get('daily_digest_time', '21:00')}")
        else:
            logger.info("群消息汇总插件：每日汇总已禁用")

    async def _daily_digest_loop(self):
        while True:
            now = datetime.now()
            digest_time = self.config.get("daily_digest_time", "21:00")
            target_time = datetime.strptime(digest_time, "%H:%M").time()
            
            target_datetime = datetime.combine(now.date(), target_time)
            if now >= target_datetime:
                target_datetime += timedelta(days=1)
            
            wait_seconds = (target_datetime - now).total_seconds()
            logger.info(f"下次汇总时间: {target_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
            await asyncio.sleep(wait_seconds)
            
            await self._send_daily_digest()

    async def _send_daily_digest(self):
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            if self.last_digest_date == today:
                logger.info("今日已发送过汇总")
                return
            
            if not self.user_id:
                logger.warning("未设置用户ID，无法发送汇总")
                return
            
            messages = self._get_messages_by_days(1)
            if not messages:
                logger.info("今日无重要消息")
                return
            
            digest = self._format_digest(messages, "今日")
            await self.context.send_message(f"private:{self.user_id}", digest)
            
            self.last_digest_date = today
            await self.put_kv_data("last_digest_date", today)
            logger.info("每日汇总已发送")
        except Exception as e:
            logger.error(f"发送每日汇总失败: {e}")

    def _is_important_message(self, event: AstrMessageEvent, user_id: str) -> bool:
        message_str = event.message_str.strip()
        
        if not message_str or len(message_str) < 2:
            return False
        
        spam_keywords = ["红包", "砍价", "投票", "帮忙点", "拼多多", "助力", "集赞", "转发", "抽奖", "免费领"]
        if any(keyword in message_str for keyword in spam_keywords):
            return False
        
        message_components = event.message_obj.message
        for component in message_components:
            if hasattr(component, 'type'):
                if component.type == "at":
                    if hasattr(component, 'qq'):
                        if component.qq == "all":
                            return True
                        if user_id and component.qq == user_id:
                            return True
        
        important_keywords = ["重要", "紧急", "通知", "公告", "会议", "截止", "deadline", "必须", "务必"]
        if any(keyword in message_str for keyword in important_keywords):
            return True
        
        if len(message_str) > 50:
            return True
        
        return False

    def _save_message(self, event: AstrMessageEvent):
        try:
            message_data = {
                "timestamp": event.message_obj.timestamp,
                "group_id": event.group_id,
                "group_name": self._get_group_name(event),
                "sender_id": event.get_sender_id(),
                "sender_name": event.get_sender_name(),
                "content": event.message_str,
                "is_at_all": self._check_at_all(event),
                "is_at_me": self._check_at_me(event),
            }
            
            self.message_list.append(message_data)
            
            if len(self.message_list) > 1000:
                self.message_list = self.message_list[-1000:]
            
            asyncio.create_task(self.put_kv_data("message_list", self.message_list))
        except Exception as e:
            logger.error(f"保存消息失败: {e}")

    def _get_group_name(self, event: AstrMessageEvent) -> str:
        try:
            return f"群{event.group_id}"
        except:
            return "未知群"

    def _check_at_all(self, event: AstrMessageEvent) -> bool:
        try:
            for component in event.message_obj.message:
                if hasattr(component, 'type') and component.type == "at":
                    if hasattr(component, 'qq') and component.qq == "all":
                        return True
        except:
            pass
        return False

    def _check_at_me(self, event: AstrMessageEvent) -> bool:
        try:
            for component in event.message_obj.message:
                if hasattr(component, 'type') and component.type == "at":
                    if hasattr(component, 'qq') and component.qq == self.user_id:
                        return True
        except:
            pass
        return False

    def _get_messages_by_days(self, days: int) -> List[Dict]:
        try:
            max_days = self.config.get("max_query_days", 7)
            if days > max_days:
                days = max_days
            
            cutoff_time = (datetime.now() - timedelta(days=days)).timestamp()
            filtered_messages = [
                msg for msg in self.message_list 
                if msg["timestamp"] >= cutoff_time
            ]
            
            return sorted(filtered_messages, key=lambda x: x["timestamp"], reverse=True)
        except Exception as e:
            logger.error(f"获取消息失败: {e}")
            return []

    def _format_digest(self, messages: List[Dict], time_range: str) -> str:
        if not messages:
            return f"{time_range}没有重要消息"
        
        digest_lines = [f"📊 {time_range}重要消息汇总\n"]
        digest_lines.append("=" * 40 + "\n")
        
        grouped_messages = {}
        for msg in messages:
            group_name = msg["group_name"]
            if group_name not in grouped_messages:
                grouped_messages[group_name] = []
            grouped_messages[group_name].append(msg)
        
        for group_name, group_msgs in grouped_messages.items():
            digest_lines.append(f"\n📢 {group_name}\n")
            digest_lines.append("-" * 30 + "\n")
            
            for msg in group_msgs:
                time_str = datetime.fromtimestamp(msg["timestamp"]).strftime("%H:%M")
                prefix = ""
                if msg["is_at_all"]:
                    prefix = "[@全体] "
                elif msg["is_at_me"]:
                    prefix = "[@我] "
                
                content = msg["content"][:100]
                if len(msg["content"]) > 100:
                    content += "..."
                
                digest_lines.append(f"{time_str} {prefix}{msg['sender_name']}: {content}\n")
        
        digest_lines.append("\n" + "=" * 40)
        digest_lines.append(f"\n共 {len(messages)} 条重要消息")
        
        return "".join(digest_lines)

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_message(self, event: AstrMessageEvent):
        try:
            if not event.is_group():
                return
            
            if not self.user_id:
                self.user_id = event.get_sender_id()
                logger.info(f"设置用户ID: {self.user_id}")
            
            if self._is_important_message(event, self.user_id):
                self._save_message(event)
                logger.info(f"记录重要消息: {event.message_str[:50]}")
        except Exception as e:
            logger.error(f"处理消息失败: {e}")

    @filter.command_group("digest")
    def digest_group(self):
        pass

    @digest_group.command("recent")
    async def recent_digest(self, event: AstrMessageEvent, days: int = 1):
        """查询最近重要消息
        
        Args:
            days(int): 查询天数，默认1天
        """
        if not event.is_private():
            yield event.plain_result("请在私聊中使用此命令")
            return
        
        if not self.user_id:
            self.user_id = event.get_sender_id()
        
        if days < 1:
            days = 1
        
        max_days = self.config.get("max_query_days", 7)
        if days > max_days:
            yield event.plain_result(f"查询天数不能超过{max_days}天")
            return
        
        messages = self._get_messages_by_days(days)
        if not messages:
            yield event.plain_result(f"最近{days}天没有重要消息")
            return
        
        time_range = f"最近{days}天" if days > 1 else "今日"
        digest = self._format_digest(messages, time_range)
        yield event.plain_result(digest)

    @filter.command("最近重要消息", alias={"最近重要消息"})
    async def recent_digest_alias(self, event: AstrMessageEvent, days: int = 1):
        """查询最近重要消息（中文指令）
        
        Args:
            days(int): 查询天数，默认1天
        """
        async for result in self.recent_digest(event, days):
            yield result

    @digest_group.command("setuser")
    async def set_user(self, event: AstrMessageEvent):
        """设置接收汇总的用户ID"""
        if not event.is_private():
            yield event.plain_result("请在私聊中使用此命令")
            return
        
        self.user_id = event.get_sender_id()
        yield event.plain_result(f"已设置接收汇总的用户ID: {self.user_id}")

    @digest_group.command("clear")
    async def clear_messages(self, event: AstrMessageEvent):
        """清空所有记录的消息"""
        if not event.is_private():
            yield event.plain_result("请在私聊中使用此命令")
            return
        
        self.message_list = []
        await self.put_kv_data("message_list", [])
        yield event.plain_result("已清空所有记录的消息")

    @digest_group.command("status")
    async def status(self, event: AstrMessageEvent):
        """查看插件状态"""
        if not event.is_private():
            yield event.plain_result("请在私聊中使用此命令")
            return
        
        status_info = f"""
📊 插件状态
{'=' * 30}
用户ID: {self.user_id or '未设置'}
已记录消息数: {len(self.message_list)}
每日汇总: {'启用' if self.config.get('enable_daily_digest', True) else '禁用'}
汇总时间: {self.config.get('daily_digest_time', '21:00')}
最大查询天数: {self.config.get('max_query_days', 7)}
上次汇总日期: {self.last_digest_date or '从未汇总'}
"""
        yield event.plain_result(status_info)

    async def terminate(self):
        logger.info("群消息汇总插件已停止")
