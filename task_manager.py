"""
Task Manager and Cancellation Token engine.
Provides live stop functionality for ongoing operations (buying, scanning, OTP polling).
"""
from __future__ import annotations
import asyncio
from typing import Callable, Any
import logging

logger = logging.getLogger(__name__)


class CancellationToken:
    """Token used to signal task cancellation and trigger immediate refund cleanup."""
    
    def __init__(self, task_name: str = "task"):
        self.task_name = task_name
        self._is_cancelled = False
        self._cleanup_callbacks: list[Callable[[], Any]] = []

    @property
    def is_cancelled(self) -> bool:
        return self._is_cancelled

    def cancel(self) -> None:
        """Signal cancellation and run all registered cleanup callbacks."""
        if self._is_cancelled:
            return
        self._is_cancelled = True
        logger.info(f"Cancellation requested for task: {self.task_name}")
        for callback in self._cleanup_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in cancellation cleanup callback: {e}")

    def register_cleanup(self, callback: Callable[[], Any]) -> None:
        """Register a cleanup hook (e.g., auto-cancel number on Grizzly for refund)."""
        self._cleanup_callbacks.append(callback)


class TaskManager:
    """Tracks and manages running tasks across Telegram chats."""

    def __init__(self):
        self._active_tokens: dict[int, CancellationToken] = {}
        self._active_async_tasks: dict[int, asyncio.Task] = {}

    def is_running(self, chat_id: int) -> bool:
        """Check if an asynchronous task is active for the chat."""
        task = self._active_async_tasks.get(chat_id)
        return bool(task and not task.done())

    def start_task(self, chat_id: int, task_name: str) -> CancellationToken:
        """Register and start a new task token for a chat."""
        # Stop existing task if any
        self.stop_task(chat_id)
        token = CancellationToken(task_name=f"{task_name}-{chat_id}")
        self._active_tokens[chat_id] = token
        return token

    def attach_async_task(self, chat_id: int, async_task: asyncio.Task) -> None:
        """Attach the asyncio task handle so it can be managed."""
        self._active_async_tasks[chat_id] = async_task

    def stop_task(self, chat_id: int) -> bool:
        """Stop the running task for a chat and invoke all refund callbacks."""
        token = self._active_tokens.pop(chat_id, None)
        stopped = False
        if token and not token.is_cancelled:
            token.cancel()
            stopped = True

        async_task = self._active_async_tasks.pop(chat_id, None)
        if async_task and not async_task.done():
            async_task.cancel()
            stopped = True

        return stopped

    def get_token(self, chat_id: int) -> CancellationToken | None:
        return self._active_tokens.get(chat_id)

    def cleanup(self, chat_id: int) -> None:
        """Remove finished task references."""
        self._active_tokens.pop(chat_id, None)
        self._active_async_tasks.pop(chat_id, None)


# Global singleton instance
task_manager = TaskManager()
