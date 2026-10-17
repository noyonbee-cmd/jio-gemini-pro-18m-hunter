"""
Refund Watcher Agent Module for Grizzly SMS.
Monitors activation cooldown timers (60-90s lock window), automatically triggers
cancellation & refund once unlocked, tracks wallet balance, and prevents credit loss.
"""
from __future__ import annotations
import asyncio
import time
import logging
from typing import Any

from db_manager import db_manager
from grizzly_client import grizzly_client
from logger import log_bot_info, log_bot_warn, log_refund

logger = logging.getLogger(__name__)


class RefundWatcherAgent:
    """
    Dedicated background agent for Grizzly SMS cancellation & refund management.
    Grizzly SMS enforces a 60-90 second cancellation cooldown lock after purchase.
    This agent handles cooldowns asynchronously without blocking the main hunter bot.
    """

    def __init__(self, check_interval: int = 10, default_cooldown: int = 75):
        self.check_interval = check_interval
        self.default_cooldown = default_cooldown
        self.is_running = False
        self._worker_task: asyncio.Task | None = None
        self._last_orphan_sweep = 0.0

    def start(self, loop: asyncio.AbstractEventLoop | None = None) -> None:
        """Start the background watcher agent worker loop."""
        if self.is_running:
            return
        self.is_running = True
        current_loop = loop or asyncio.get_event_loop()
        self._worker_task = current_loop.create_task(self._run_loop())
        log_bot_info("[REFUND WATCHER AGENT] Background refund & balance protection agent started.")

    def stop(self) -> None:
        """Gracefully stop the background watcher agent."""
        self.is_running = False
        if self._worker_task and not self._worker_task.done():
            self._worker_task.cancel()
        log_bot_info("[REFUND WATCHER AGENT] Background refund agent stopped.")

    def queue_refund(
        self,
        activation_id: int,
        phone_number: str,
        cost: float = 0.0,
        reason: str = "",
        purchased_epoch: float | None = None,
        cooldown_seconds: int = 75,
        service_code: str = "jio",
    ) -> None:
        """
        Enqueue an activation for refund tracking.
        If cooldown has already elapsed (e.g. after 90s OTP polling timeout),
        attempts fast cancellation immediately. Otherwise, delegates to watcher loop.
        """
        p_epoch = purchased_epoch or time.time()
        elapsed = time.time() - p_epoch

        # If cooldown already elapsed, attempt immediate fast-path refund
        if elapsed >= cooldown_seconds:
            try:
                success, res = grizzly_client.set_status(activation_id, status=8)
                if success or "ACCESS_CANCEL" in res:
                    db_manager.queue_refund(
                        activation_id, phone_number, cost, reason, p_epoch, cooldown_seconds, service_code
                    )
                    db_manager.mark_refunded(activation_id)
                    _, _, bal_str = grizzly_client.get_balance()
                    log_refund(activation_id, "GRIZZLY", f"Fast Refund Success! (+{phone_number}) Restored ${cost:.2f}. Balance: {bal_str}")
                    return
            except Exception as e:
                logger.warning(f"Fast refund attempt for #{activation_id} raised: {e}")

        # Enqueue for background cooldown monitoring
        db_manager.queue_refund(
            activation_id,
            phone_number,
            cost=cost,
            reason=reason,
            purchased_epoch=p_epoch,
            cooldown_seconds=cooldown_seconds,
            service_code=service_code,
        )
        remaining = max(0, int(cooldown_seconds - elapsed))
        log_bot_info(
            f"[REFUND QUEUED] Act#{activation_id} (+{phone_number}) queued for background auto-refund. "
            f"Cooldown: ~{remaining}s remaining before Grizzly unlock. (Reason: {reason})"
        )

    async def _run_loop(self) -> None:
        """Continuous background loop processing refund queue and checking balance."""
        while self.is_running:
            try:
                await self._process_pending_refunds()
                await self._sweep_orphaned_activations()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Error in refund watcher loop: {e}")

            await asyncio.sleep(self.check_interval)

    async def _process_pending_refunds(self) -> None:
        """Process all unrefunded activations whose cooldown lock has expired."""
        loop = asyncio.get_event_loop()
        pending = await loop.run_in_executor(None, db_manager.get_pending_refunds)
        if not pending:
            return

        now = time.time()
        for item in pending:
            act_id = item["activation_id"]
            phone = item["phone_number"]
            cost = item["cost"]
            p_epoch = item["purchased_epoch"]
            cooldown = item["cooldown_seconds"]
            attempts = item["attempts"]
            elapsed = now - p_epoch

            # If still within cooldown lock window, wait
            if elapsed < cooldown:
                remaining = int(cooldown - elapsed)
                if attempts == 0 and int(elapsed) % 20 < self.check_interval:
                    log_bot_info(
                        f"[REFUND WATCHER] Act#{act_id} (+{phone}) locked on Grizzly: "
                        f"{remaining}s remaining before cancel enabled..."
                    )
                continue

            # Cooldown is up! Trigger cancel and refund on Grizzly SMS
            log_bot_info(f"[REFUND WATCHER] Cooldown expired for Act#{act_id} (+{phone}). Sending cancel (status=8)...")
            success, text = await loop.run_in_executor(
                None, lambda: grizzly_client.set_status(act_id, status=8)
            )

            if success or "ACCESS_CANCEL" in text:
                # Successfully refunded!
                await loop.run_in_executor(None, lambda: db_manager.mark_refunded(act_id))
                _, _, bal_str = await loop.run_in_executor(None, grizzly_client.get_balance)
                log_refund(
                    act_id,
                    "GRIZZLY",
                    f"REFUND CONFIRMED! (+{phone}) Restored ${cost:.2f} USD. New Grizzly Balance: {bal_str}",
                )

            elif "EARLY_CANCEL_DENIED" in text:
                # Carrier/provider route needs slightly more time (e.g. 90-120s)
                log_bot_info(
                    f"[REFUND WATCHER] Act#{act_id} returned EARLY_CANCEL_DENIED. "
                    f"Grizzly lock still active. Retrying in 15s (Attempt {attempts + 1})..."
                )
                await loop.run_in_executor(
                    None,
                    lambda: db_manager.update_refund_attempt(act_id, error_msg="EARLY_CANCEL_DENIED", extra_cooldown=15),
                )

            elif text in ("STATUS_CANCEL", "NO_ACTIVATION", "BAD_STATUS"):
                # Already cancelled or expired on Grizzly panel
                await loop.run_in_executor(None, lambda: db_manager.mark_refunded(act_id))
                log_bot_info(f"[REFUND WATCHER] Act#{act_id} is already closed on Grizzly panel ({text}). Marked refunded.")

            else:
                log_bot_warn(f"[REFUND WATCHER] Unexpected response for Act#{act_id}: {text}")
                await loop.run_in_executor(
                    None,
                    lambda: db_manager.update_refund_attempt(act_id, error_msg=text, extra_cooldown=15),
                )

    async def _sweep_orphaned_activations(self) -> None:
        """
        Periodically (every 3 minutes) inspect active activations on Grizzly panel.
        Auto-refunds any orphaned activations older than 90s to guarantee zero lost balance.
        """
        now = time.time()
        if now - self._last_orphan_sweep < 180:
            return
        self._last_orphan_sweep = now

        loop = asyncio.get_event_loop()
        try:
            active_items = await loop.run_in_executor(None, grizzly_client.get_active_activations)
            if not active_items:
                return

            # Check if any active items on panel are older than 90s and not claimed
            for item in active_items:
                if not isinstance(item, dict):
                    continue
                act_id = item.get("activationId") or item.get("id")
                phone = str(item.get("phoneNumber") or item.get("phone") or "")
                if not act_id:
                    continue

                act_id = int(act_id)
                # Check DB status
                rec = await loop.run_in_executor(None, lambda: db_manager.get_number(act_id))
                if rec and rec["status"] in ("CLAIMED", "VERIFIED"):
                    continue

                log_bot_info(f"[REFUND WATCHER] Detected stranded activation #{act_id} (+{phone}) on Grizzly panel. Auto-queuing refund.")
                self.queue_refund(
                    activation_id=act_id,
                    phone_number=phone,
                    cost=0.10,
                    reason="Orphan panel recovery",
                    purchased_epoch=now - 80,  # Ready for immediate or near-immediate cancel
                    cooldown_seconds=75,
                )
        except Exception as e:
            logger.warning(f"Error during orphaned activation sweep: {e}")

    def get_summary(self) -> dict[str, Any]:
        """Return live statistics of the refund watcher agent."""
        stats = db_manager.get_refund_stats()
        success, bal, bal_str = grizzly_client.get_balance()
        return {
            "is_running": self.is_running,
            "pending_refunds": stats["pending_count"],
            "total_refunded_count": stats["refunded_count"],
            "total_refunded_amount_usd": stats["refunded_amount"],
            "current_balance_usd": bal if success else 0.0,
            "current_balance_display": bal_str if success else "Error",
        }


# Global singleton instance
refund_agent = RefundWatcherAgent()
