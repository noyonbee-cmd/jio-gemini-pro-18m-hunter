"""
Clear-Chat Engine for Jio Gemini Hunter Bot.
Adheres strictly to PRD.md §4.6.
Provides private message ID tracking without content storage,
batch deletion via deleteMessages with bisection retry, and honest reporting.
"""
from __future__ import annotations
import asyncio
import logging
import time
from typing import List, Tuple
from telegram import Bot
from telegram.error import TelegramError

from db_manager import db_manager

logger = logging.getLogger(__name__)


class ChatCleaner:
    """Manages message ID tracking and batch deletion in private chats."""

    MAX_BATCH_SIZE = 100
    RATE_LIMIT_DELAY = 0.12  # 120ms throttle between API calls

    def track_incoming(self, chat_id: int, message_id: int) -> None:
        """Record incoming private message ID for future cleaning."""
        db_manager.track_message(chat_id, message_id)

    def track_outgoing(self, chat_id: int, message_id: int) -> None:
        """Record bot's outgoing message ID for future cleaning."""
        db_manager.track_message(chat_id, message_id)

    async def _delete_batch_with_bisection(
        self, bot: Bot, chat_id: int, ids: List[int], depth: int = 0
    ) -> Tuple[int, int]:
        """
        Recursively delete message IDs in batches of up to 100.
        If a batch fails (due to messages > 48h or already deleted),
        bisect the list into halves and retry smaller chunks.
        Returns: (deleted_count, failed_count)
        """
        if not ids:
            return 0, 0

        # Attempt batch deletion
        try:
            await bot.delete_messages(chat_id=chat_id, message_ids=ids)
            db_manager.delete_tracked_messages(chat_id, ids)
            await asyncio.sleep(self.RATE_LIMIT_DELAY)
            return len(ids), 0
        except TelegramError as e:
            # If batch is single message, it cannot be deleted (e.g. > 48h)
            if len(ids) == 1:
                db_manager.delete_tracked_messages(chat_id, ids)
                return 0, 1

            # Bisection: split batch into two halves and retry
            mid = len(ids) // 2
            left_ids = ids[:mid]
            right_ids = ids[mid:]

            left_del, left_fail = await self._delete_batch_with_bisection(bot, chat_id, left_ids, depth + 1)
            right_del, right_fail = await self._delete_batch_with_bisection(bot, chat_id, right_ids, depth + 1)

            return (left_del + right_del), (left_fail + right_fail)
        except Exception as e:
            logger.warning(f"Unexpected error in delete batch for chat {chat_id}: {e}")
            return 0, len(ids)

    async def clear_chat(self, bot: Bot, chat_id: int, sweep_depth: int = 300) -> str:
        """
        Clear private chat messages younger than 48 hours.
        Combines tracked IDs with an intelligent sweep of recent message IDs.
        """
        # 1. Fetch tracked message IDs (max 48h old)
        tracked_ids = set(db_manager.get_tracked_messages(chat_id, max_age_seconds=172800))

        # 2. Add sweep of recent IDs below the newest known ID
        if tracked_ids:
            newest_id = max(tracked_ids)
            sweep_min = max(1, newest_id - min(sweep_depth, 1500))
            all_candidate_ids = sorted(tracked_ids.union(range(sweep_min, newest_id + 1)), reverse=True)
        else:
            all_candidate_ids = []

        if not all_candidate_ids:
            return "🧹 **Chat is already clean.** No recent messages found within the 48-hour window."

        total_deleted = 0
        total_failed = 0

        # Chunk into batches of 100
        for i in range(0, len(all_candidate_ids), self.MAX_BATCH_SIZE):
            chunk = all_candidate_ids[i : i + self.MAX_BATCH_SIZE]
            deleted, failed = await self._delete_batch_with_bisection(bot, chat_id, chunk)
            total_deleted += deleted
            total_failed += failed

        # Purge records older than 3 days
        db_manager.purge_old_tracked_messages(days=3)

        report = (
            f"🧹 **Chat Clear Operation Finished**\n\n"
            f"• ✅ **Deleted**: `{total_deleted}` messages\n"
        )
        if total_failed > 0:
            report += (
                f"• ℹ️ **Skipped**: `{total_failed}` messages\n\n"
                "> ⚠️ *Notice: Telegram Bot API prohibits bots from deleting messages "
                "older than 48 hours or messages that were already removed.*"
            )
        else:
            report += "\n> ✨ *All messages within the 48-hour deletion window were cleared.*"

        return report

    async def clear_all_chats(self, bot: Bot, limit_chats: int = 25) -> str:
        """
        Clear tracked private chats across all users (admin maintenance).
        Requires explicit confirmation before execution.
        """
        chats = db_manager.get_all_tracked_chats(limit=limit_chats)
        if not chats:
            return "🧹 **No active tracked chats found to clean.**"

        grand_deleted = 0
        grand_failed = 0
        processed_chats = 0

        for chat_id in chats:
            tracked_ids = db_manager.get_tracked_messages(chat_id, max_age_seconds=172800)
            if not tracked_ids:
                continue

            for i in range(0, len(tracked_ids), self.MAX_BATCH_SIZE):
                chunk = tracked_ids[i : i + self.MAX_BATCH_SIZE]
                deleted, failed = await self._delete_batch_with_bisection(bot, chat_id, chunk)
                grand_deleted += deleted
                grand_failed += failed

            processed_chats += 1
            await asyncio.sleep(self.RATE_LIMIT_DELAY * 2)

        return (
            f"💥 **Global Chat Clear Complete**\n\n"
            f"• 👥 **Chats Processed**: `{processed_chats}`\n"
            f"• ✅ **Total Messages Deleted**: `{grand_deleted}`\n"
            f"• ℹ️ **Old / Skipped Messages**: `{grand_failed}`\n\n"
            "> 🛡️ Messages older than 48 hours are automatically retained per Telegram API protocol."
        )


# Global singleton instance
chat_cleaner = ChatCleaner()
