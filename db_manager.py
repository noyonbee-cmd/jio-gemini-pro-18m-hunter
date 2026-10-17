"""
Database and Local State Management module for Jio Gemini Hunter Bot.
Stores active numbers, status, and claimed 18-month Google Gemini activation links.
"""
from __future__ import annotations
import sqlite3
import csv
from datetime import datetime, timezone, timedelta
from typing import Any
from config import DB_FILE, LINKS_FILE, RESULTS_FILE


def get_current_time_str() -> str:
    """Return local readable time string (UTC+5:30 IST / Nepal offset)."""
    utc_now = datetime.now(timezone.utc)
    ist_offset = timedelta(hours=5, minutes=30)
    ist_time = utc_now + ist_offset
    return ist_time.strftime("%Y-%m-%d %I:%M:%S %p")


class DatabaseManager:
    """Manages SQLite storage for active phone numbers and claimed activation links."""

    def __init__(self, db_path=DB_FILE):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Create tables if they do not exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS active_numbers (
                    activation_id INTEGER PRIMARY KEY,
                    phone_number TEXT NOT NULL,
                    service_code TEXT,
                    cost REAL DEFAULT 0.0,
                    carrier_valid INTEGER DEFAULT 0,
                    plan_active INTEGER DEFAULT 0,
                    otp_code TEXT DEFAULT '',
                    status TEXT DEFAULT 'RENTED',
                    claim_url TEXT DEFAULT '',
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS claimed_offers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    activation_id INTEGER,
                    phone_number TEXT NOT NULL,
                    claim_url TEXT NOT NULL UNIQUE,
                    cost REAL DEFAULT 0.0,
                    claimed_at TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS refund_queue (
                    activation_id INTEGER PRIMARY KEY,
                    phone_number TEXT NOT NULL,
                    service_code TEXT DEFAULT 'jio',
                    cost REAL DEFAULT 0.0,
                    reason TEXT DEFAULT '',
                    status TEXT DEFAULT 'PENDING',
                    purchased_epoch REAL DEFAULT 0.0,
                    cooldown_seconds INTEGER DEFAULT 75,
                    attempts INTEGER DEFAULT 0,
                    last_error TEXT DEFAULT '',
                    queued_at TEXT,
                    refunded_at TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS authorized_users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT DEFAULT '',
                    first_name TEXT DEFAULT '',
                    added_by INTEGER DEFAULT 0,
                    notes TEXT DEFAULT '',
                    created_at TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS invite_tokens (
                    token TEXT PRIMARY KEY,
                    created_by INTEGER DEFAULT 0,
                    expires_at TEXT,
                    used_by INTEGER DEFAULT NULL,
                    used_at TEXT DEFAULT NULL,
                    created_at TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tracked_messages (
                    chat_id INTEGER,
                    message_id INTEGER,
                    created_epoch REAL,
                    PRIMARY KEY (chat_id, message_id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bot_profile_meta (
                    meta_key TEXT PRIMARY KEY,
                    meta_value TEXT DEFAULT '',
                    updated_at TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS admin_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER,
                    action TEXT,
                    target_id TEXT DEFAULT '',
                    details TEXT DEFAULT '',
                    created_at TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS runtime_settings (
                    setting_key TEXT PRIMARY KEY,
                    setting_value TEXT,
                    updated_at TEXT
                )
            """)
            conn.commit()

    def add_number(
        self,
        activation_id: int,
        phone_number: str,
        service_code: str = "mjo",
        cost: float = 0.0,
        status: str = "RENTED",
    ) -> None:
        """Add a newly rented number to database."""
        now = get_current_time_str()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO active_numbers 
                (activation_id, phone_number, service_code, cost, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (activation_id, phone_number, service_code, cost, status, now, now),
            )
            conn.commit()

    def update_status(
        self,
        activation_id: int,
        status: str,
        carrier_valid: bool | None = None,
        plan_active: bool | None = None,
        otp_code: str | None = None,
        claim_url: str | None = None,
    ) -> None:
        """Update fields and status of an activation record."""
        now = get_current_time_str()
        fields = ["status = ?", "updated_at = ?"]
        params: list[Any] = [status, now]

        if carrier_valid is not None:
            fields.append("carrier_valid = ?")
            params.append(1 if carrier_valid else 0)
        if plan_active is not None:
            fields.append("plan_active = ?")
            params.append(1 if plan_active else 0)
        if otp_code is not None:
            fields.append("otp_code = ?")
            params.append(otp_code)
        if claim_url is not None:
            fields.append("claim_url = ?")
            params.append(claim_url)

        params.append(activation_id)
        query = f"UPDATE active_numbers SET {', '.join(fields)} WHERE activation_id = ?"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()

    def get_number(self, activation_id: int) -> dict[str, Any] | None:
        """Retrieve number details by activation ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM active_numbers WHERE activation_id = ?", (activation_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_active_numbers(self) -> list[dict[str, Any]]:
        """List all pending or verified active numbers."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM active_numbers WHERE status IN ('RENTED', 'VERIFIED', 'OTP_PENDING') ORDER BY activation_id DESC"
            )
            return [dict(row) for row in cursor.fetchall()]

    def save_claimed_offer(self, activation_id: int, phone_number: str, claim_url: str, cost: float = 0.0) -> None:
        """Save successfully claimed Gemini 18-month link to database, TXT, and CSV."""
        now = get_current_time_str()
        
        # 1. Update SQLite
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR IGNORE INTO claimed_offers 
                (activation_id, phone_number, claim_url, cost, claimed_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (activation_id, phone_number, claim_url, cost, now),
            )
            cursor.execute(
                "UPDATE active_numbers SET status = 'CLAIMED', claim_url = ?, updated_at = ? WHERE activation_id = ?",
                (claim_url, now, activation_id),
            )
            conn.commit()

        # 2. Append to TXT file
        existing_links = set(LINKS_FILE.read_text(encoding="utf-8").splitlines()) if LINKS_FILE.exists() else set()
        if claim_url not in existing_links:
            with LINKS_FILE.open("a", encoding="utf-8") as handle:
                handle.write(claim_url + "\n")

        # 3. Append to CSV file
        csv_exists = RESULTS_FILE.exists() and RESULTS_FILE.stat().st_size > 0
        fieldnames = ["claimed_at", "mobile_number", "activation_id", "cost", "claim_url"]
        with RESULTS_FILE.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            if not csv_exists:
                writer.writeheader()
            writer.writerow({
                "claimed_at": now,
                "mobile_number": phone_number,
                "activation_id": activation_id,
                "cost": cost,
                "claim_url": claim_url,
            })

    def get_claimed_offers(self) -> list[dict[str, Any]]:
        """Return all successfully claimed Gemini offers."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM claimed_offers ORDER BY id DESC")
            return [dict(row) for row in cursor.fetchall()]

    def queue_refund(
        self,
        activation_id: int,
        phone_number: str,
        cost: float = 0.0,
        reason: str = "",
        purchased_epoch: float = 0.0,
        cooldown_seconds: int = 75,
        service_code: str = "jio",
    ) -> None:
        """Enqueue an activation for background cooldown monitoring and cancellation."""
        now = get_current_time_str()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO refund_queue
                (activation_id, phone_number, service_code, cost, reason, status, purchased_epoch, cooldown_seconds, attempts, last_error, queued_at)
                VALUES (?, ?, ?, ?, ?, 'PENDING', ?, ?, 0, '', ?)
                """,
                (activation_id, phone_number, service_code, cost, reason, purchased_epoch, cooldown_seconds, now),
            )
            # Also ensure active_numbers is marked appropriately
            cursor.execute(
                "UPDATE active_numbers SET status = 'REFUND_PENDING', updated_at = ? WHERE activation_id = ?",
                (now, activation_id),
            )
            conn.commit()

    def get_pending_refunds(self) -> list[dict[str, Any]]:
        """Return all activations pending refund."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM refund_queue WHERE status = 'PENDING' ORDER BY purchased_epoch ASC")
            return [dict(row) for row in cursor.fetchall()]

    def mark_refunded(self, activation_id: int) -> None:
        """Mark an activation as successfully cancelled and refunded."""
        now = get_current_time_str()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE refund_queue SET status = 'REFUNDED', refunded_at = ? WHERE activation_id = ?",
                (now, activation_id),
            )
            cursor.execute(
                "UPDATE active_numbers SET status = 'CANCELLED', updated_at = ? WHERE activation_id = ?",
                (now, activation_id),
            )
            conn.commit()

    def update_refund_attempt(
        self,
        activation_id: int,
        error_msg: str = "",
        extra_cooldown: int = 0,
    ) -> None:
        """Update retry state and adjust cooldown if EARLY_CANCEL_DENIED."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE refund_queue 
                SET attempts = attempts + 1, 
                    cooldown_seconds = cooldown_seconds + ?,
                    last_error = ?
                WHERE activation_id = ?
                """,
                (extra_cooldown, error_msg, activation_id),
            )
            conn.commit()

    def get_refund_stats(self) -> dict[str, Any]:
        """Return statistics on refunded activations."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM refund_queue WHERE status = 'PENDING'")
            pending_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*), COALESCE(SUM(cost), 0.0) FROM refund_queue WHERE status = 'REFUNDED'")
            ref_row = cursor.fetchone()
            refunded_count = ref_row[0]
            refunded_amount = float(ref_row[1])

            return {
                "pending_count": pending_count,
                "refunded_count": refunded_count,
                "refunded_amount": refunded_amount,
            }

    def get_stats(self) -> dict[str, int | float]:
        """Return operational summary stats."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM active_numbers")
            total_rented = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM claimed_offers")
            total_claimed = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM active_numbers WHERE status = 'CANCELLED'")
            total_cancelled = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM active_numbers WHERE status IN ('RENTED', 'VERIFIED', 'OTP_PENDING', 'REFUND_PENDING')")
            total_pending = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*), COALESCE(SUM(cost), 0.0) FROM refund_queue WHERE status = 'REFUNDED'")
            ref_row = cursor.fetchone()
            refunded_count = ref_row[0]
            refunded_amount = float(ref_row[1])

            return {
                "total_rented": total_rented,
                "total_claimed": total_claimed,
                "total_cancelled": total_cancelled,
                "total_pending": total_pending,
                "refunded_count": refunded_count,
                "refunded_amount": refunded_amount,
            }

    # ---------------------------------------------------------
    # USER ALLOWLIST & ACCESS MANAGEMENT (PRD §4.4 & §4.5)
    # ---------------------------------------------------------

    def add_authorized_user(
        self,
        user_id: int,
        username: str = "",
        first_name: str = "",
        added_by: int = 0,
        notes: str = "",
    ) -> bool:
        """Add a user ID to the authorized allowlist."""
        now = get_current_time_str()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO authorized_users (user_id, username, first_name, added_by, notes, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name,
                    notes = excluded.notes
                """,
                (user_id, username, first_name, added_by, notes, now),
            )
            conn.commit()
            return True

    def remove_authorized_user(self, user_id: int) -> bool:
        """Remove a user from the authorized allowlist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM authorized_users WHERE user_id = ?", (user_id,))
            conn.commit()
            return cursor.rowcount > 0

    def is_user_authorized(self, user_id: int) -> bool:
        """Check if user exists in authorized allowlist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM authorized_users WHERE user_id = ?", (user_id,))
            return cursor.fetchone() is not None

    def get_authorized_users(self, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        """Retrieve paginated list of authorized users."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT user_id, username, first_name, added_by, notes, created_at
                FROM authorized_users
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_authorized_users_count(self) -> int:
        """Return total count of authorized users."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM authorized_users")
            return cursor.fetchone()[0]

    # ---------------------------------------------------------
    # DEEP-LINK INVITE TOKENS (PRD §4.5)
    # ---------------------------------------------------------

    def create_invite_token(self, token: str, created_by: int, expires_at_iso: str) -> bool:
        """Store a single-use 48-hour invite token."""
        now = get_current_time_str()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO invite_tokens (token, created_by, expires_at, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (token, created_by, expires_at_iso, now),
            )
            conn.commit()
            return True

    def redeem_invite_token(self, token: str, user_id: int) -> bool:
        """
        Atomically redeem an invite token if valid, unredeemed, and not expired.
        """
        now = get_current_time_str()
        utc_now_iso = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE invite_tokens
                SET used_by = ?, used_at = ?
                WHERE token = ? AND used_by IS NULL AND expires_at > ?
                """,
                (user_id, now, token, utc_now_iso),
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_invite_token(self, token: str) -> dict[str, Any] | None:
        """Retrieve token details."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT token, created_by, expires_at, used_by, used_at FROM invite_tokens WHERE token = ?",
                (token,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    # ---------------------------------------------------------
    # MESSAGE TRACKING & CHAT CLEANER (PRD §4.6)
    # ---------------------------------------------------------

    def track_message(self, chat_id: int, message_id: int) -> None:
        """Track message ID and timestamp without saving any message contents."""
        import time
        now_epoch = time.time()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR IGNORE INTO tracked_messages (chat_id, message_id, created_epoch)
                VALUES (?, ?, ?)
                """,
                (chat_id, message_id, now_epoch),
            )
            conn.commit()

    def get_tracked_messages(self, chat_id: int, max_age_seconds: int = 172800) -> list[int]:
        """
        Get message IDs for a chat within max_age (default 48 hours = 172800s).
        Returns IDs in descending order (newest first).
        """
        import time
        min_epoch = time.time() - max_age_seconds
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT message_id FROM tracked_messages
                WHERE chat_id = ? AND created_epoch >= ?
                ORDER BY message_id DESC
                """,
                (chat_id, min_epoch),
            )
            return [row["message_id"] for row in cursor.fetchall()]

    def get_all_tracked_chats(self, limit: int = 25) -> list[int]:
        """Get unique chat IDs with tracked messages."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT DISTINCT chat_id FROM tracked_messages LIMIT ?",
                (limit,),
            )
            return [row["chat_id"] for row in cursor.fetchall()]

    def delete_tracked_messages(self, chat_id: int, message_ids: list[int]) -> None:
        """Remove message IDs from tracked records after deletion."""
        if not message_ids:
            return
        placeholders = ",".join("?" * len(message_ids))
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"DELETE FROM tracked_messages WHERE chat_id = ? AND message_id IN ({placeholders})",
                [chat_id] + message_ids,
            )
            conn.commit()

    def purge_old_tracked_messages(self, days: int = 3) -> int:
        """Purge tracking records older than N days (since Bot API can't delete > 48h)."""
        import time
        cutoff_epoch = time.time() - (days * 86400)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tracked_messages WHERE created_epoch < ?", (cutoff_epoch,))
            conn.commit()
            return cursor.rowcount

    # ---------------------------------------------------------
    # BOT PROFILE METADATA & FILE_ID CACHE (PRD §4.2 & §5.5)
    # ---------------------------------------------------------

    def get_profile_meta(self, key: str) -> str:
        """Retrieve cached hash or file_id."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT meta_value FROM bot_profile_meta WHERE meta_key = ?", (key,))
            row = cursor.fetchone()
            return row["meta_value"] if row else ""

    def set_profile_meta(self, key: str, value: str) -> None:
        """Store or update hash or file_id."""
        now = get_current_time_str()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO bot_profile_meta (meta_key, meta_value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(meta_key) DO UPDATE SET
                    meta_value = excluded.meta_value,
                    updated_at = excluded.updated_at
                """,
                (key, value, now),
            )
            conn.commit()

    # ---------------------------------------------------------
    # ADMIN AUDIT LOGGING (PRD §4.4)
    # ---------------------------------------------------------

    def log_admin_action(
        self,
        admin_id: int,
        action: str,
        target_id: str = "",
        details: str = "",
    ) -> None:
        """Record administrative action into tamper-evident audit log."""
        now = get_current_time_str()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO admin_audit_log (admin_id, action, target_id, details, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (admin_id, action, str(target_id), details, now),
            )
            conn.commit()

    # ---------------------------------------------------------
    # RUNTIME SETTINGS STORE (PRD §4.7)
    # ---------------------------------------------------------

    def get_setting(self, key: str, default: str = "") -> str:
        """Get runtime setting value."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT setting_value FROM runtime_settings WHERE setting_key = ?", (key,))
            row = cursor.fetchone()
            return row["setting_value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        """Set or update runtime setting."""
        now = get_current_time_str()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO runtime_settings (setting_key, setting_value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(setting_key) DO UPDATE SET
                    setting_value = excluded.setting_value,
                    updated_at = excluded.updated_at
                """,
                (key, str(value), now),
            )
            conn.commit()


# Global singleton instance
db_manager = DatabaseManager()

