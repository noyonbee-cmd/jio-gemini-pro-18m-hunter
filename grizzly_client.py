"""
Grizzly SMS API Client Module.
Handles balance checking, number acquisition, cancellation & refund, and 6-digit OTP polling.
"""
from __future__ import annotations
import re
import time
import logging
from typing import Any, Callable
import requests

from config import (
    GRIZZLY_BASE_URL,
    GRIZZLY_API_KEY,
    DEFAULT_SERVICE_CODE,
    DEFAULT_COUNTRY_ID,
    DEFAULT_MAX_PRICE,
    PROXY,
    save_env_variable,
)
from task_manager import CancellationToken
from logger import log_api_req, log_api_res, log_refund, log_otp

logger = logging.getLogger(__name__)



class GrizzlySMSClient:
    """SDK for Grizzly SMS Activation API (https://grizzlysms.com/)."""

    def __init__(self, api_key: str | None = None, proxy: str | None = None):
        self.api_key = (api_key or GRIZZLY_API_KEY).strip()
        self.proxy = (proxy or PROXY).strip()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
        })
        if self.proxy:
            self.session.proxies = {"http": self.proxy, "https": self.proxy}

    def test_and_save_api_key(self, candidate_key: str) -> tuple[bool, float, str]:
        """
        Validate candidate API key against Grizzly SMS getBalance before saving.
        If valid, updates runtime client and permanently writes to .env.
        Returns: (is_valid, balance, message)
        """
        clean_key = candidate_key.strip()
        if not clean_key:
            return False, 0.0, "API key cannot be empty."

        url = f"{GRIZZLY_BASE_URL}?action=getBalance&api_key={clean_key}"
        log_api_req("GRIZZLY", "GET", "handler_api.php?action=getBalance", f"Testing Key: {clean_key[:6]}...")
        t0 = time.monotonic()
        try:
            resp = self.session.get(url, timeout=15)
            elapsed_ms = (time.monotonic() - t0) * 1000
            text = resp.text.strip()
            log_api_res("GRIZZLY", resp.status_code, elapsed_ms, f"Body: {text}")

            match = re.match(r"^ACCESS_BALANCE:(-?\d+(?:\.\d+)?)$", text)
            if match:
                balance = float(match.group(1))
                self.api_key = clean_key
                save_env_variable("GRIZZLY_API_KEY", clean_key)
                logger.info(f"Grizzly SMS API key verified and saved to .env! Balance: ${balance:.2f}")
                return True, balance, f"API key is active and verified! Current balance: ${balance:.2f} USD"

            if text in ("BAD_KEY", "NO_KEY", "ERROR_KEY", "WRONG_KEY"):
                return False, 0.0, "Invalid Grizzly SMS API Key. Please check your key at https://grizzlysms.com/"

            return False, 0.0, f"Grizzly SMS returned unexpected response: {text}"
        except requests.RequestException as e:
            return False, 0.0, f"Network error testing API key with Grizzly SMS: {e}"

    def set_api_key(self, api_key: str) -> None:
        """Update API key dynamically."""
        self.api_key = api_key.strip()
        save_env_variable("GRIZZLY_API_KEY", self.api_key)


    def set_proxy(self, proxy: str) -> None:
        """Update proxy dynamically."""
        self.proxy = proxy.strip()
        if self.proxy:
            self.session.proxies = {"http": self.proxy, "https": self.proxy}
        else:
            self.session.proxies = {}

    def get_balance(self) -> tuple[bool, float, str]:
        """
        Query current wallet balance.
        Returns: (success, balance_float, message)
        """
        if not self.api_key:
            return False, 0.0, "API key not configured. Use /set_api_key."

        url = f"{GRIZZLY_BASE_URL}?action=getBalance&api_key={self.api_key}"
        log_api_req("GRIZZLY", "GET", "handler_api.php?action=getBalance")
        t0 = time.monotonic()
        try:
            resp = self.session.get(url, timeout=15)
            elapsed_ms = (time.monotonic() - t0) * 1000
            text = resp.text.strip()
            log_api_res("GRIZZLY", resp.status_code, elapsed_ms, f"Balance: {text}")
            
            match = re.match(r"^ACCESS_BALANCE:(-?\d+(?:\.\d+)?)$", text)
            if match:
                balance = float(match.group(1))
                return True, balance, f"${balance:.2f} USD"
            
            if text in ("BAD_KEY", "NO_KEY", "ERROR_KEY", "WRONG_KEY"):
                return False, 0.0, "Invalid Grizzly SMS API Key. Please check your key at https://grizzlysms.com/"
            
            return False, 0.0, f"Unexpected balance response: {text}"

        except requests.RequestException as e:
            return False, 0.0, f"Network error contacting Grizzly SMS: {e}"

    @staticmethod
    def normalize_service_code(service: str) -> str:
        """
        Map common user service names to official Grizzly SMS service codes.
        Allows any raw service code (e.g. 'jio', 'mjo', 'jii', 'vi', 'air', 'go', etc.)
        without mangling.
        """
        clean = (service or "").strip().lower()
        mapping = {
            "myjio": "jio",
            "my_jio": "jio",
            "my-jio": "jio",
            "my jio": "jio",
            "reliance": "jio",
            "reliance_jio": "jio",
        }
        return mapping.get(clean, clean)

    def get_number(
        self,
        service: str = DEFAULT_SERVICE_CODE,
        country: int = DEFAULT_COUNTRY_ID,
        max_price: float | None = DEFAULT_MAX_PRICE,
        provider_ids: str | None = None,
    ) -> tuple[bool, dict[str, Any], str]:
        """
        Purchase a virtual Indian number for MyJio 6-digit OTP delivery.
        Automatically maps service aliases ('myjio' -> 'jio') to avoid BAD_ACTION errors.
        Returns: (success, order_dict, message)
        """
        if not self.api_key:
            return False, {}, "API key not configured. Please use /set_api_key."

        clean_service = self.normalize_service_code(service)
        params = {
            "action": "getNumberV2",
            "api_key": self.api_key,
            "service": clean_service,
            "country": str(country),
        }
        if max_price is not None and max_price > 0:
            params["maxPrice"] = f"{max_price:.2f}"
        if provider_ids:
            params["providerIds"] = provider_ids

        log_api_req("GRIZZLY", "GET", "handler_api.php?action=getNumberV2", f"svc={clean_service}, cty={country}, maxPrice={max_price}")
        t0 = time.monotonic()
        try:
            resp = self.session.get(GRIZZLY_BASE_URL, params=params, timeout=20)
            elapsed_ms = (time.monotonic() - t0) * 1000
            text = resp.text.strip()
            log_api_res("GRIZZLY", resp.status_code, elapsed_ms, f"Body: {text[:80]}")

            # Attempt JSON parse (getNumberV2 standard)
            try:
                data = resp.json()
                if isinstance(data, dict):
                    if "activationId" in data and "phoneNumber" in data:
                        raw_phone = str(data["phoneNumber"]).lstrip("+")
                        cost = float(data.get("activationCost", 0.0))
                        order = {
                            "activation_id": int(data["activationId"]),
                            "phone_number": raw_phone,
                            "cost": cost,
                            "service": clean_service,
                            "country": country,
                            "purchased_epoch": time.time(),
                        }
                        return True, order, f"Acquired number: +{raw_phone} (${cost:.2f})"
                    if "error" in data:
                        return False, {}, f"Grizzly SMS Error: {data.get('error')}"
            except ValueError:
                pass

            # Fallback to plain text getNumber response
            match = re.match(r"^ACCESS_NUMBER:(\d+):(\+?\d+)$", text)
            if match:
                act_id = int(match.group(1))
                phone = match.group(2).lstrip("+")
                order = {
                    "activation_id": act_id,
                    "phone_number": phone,
                    "cost": max_price or 0.10,
                    "service": clean_service,
                    "country": country,
                    "purchased_epoch": time.time(),
                }
                return True, order, f"Acquired number: +{phone}"

            # Check for WRONG_MAX_PRICE error
            price_match = re.match(r"^WRONG_MAX_PRICE:([0-9.]+)", text)
            if price_match:
                market_price = float(price_match.group(1))
                return (
                    False,
                    {},
                    f"Market rate for '{clean_service}' is ${market_price:.2f} USD (higher than your max price cap of ${max_price:.2f}). Use /set_price {market_price:.2f}."
                )

            # Known API error conditions
            error_mapping = {
                "NO_NUMBERS": f"No numbers currently available for service '{clean_service}' in India (Country ID: {country}). Try again shortly.",
                "NO_BALANCE": "Insufficient balance in Grizzly SMS account. Please top up funds.",
                "BAD_KEY": "Invalid Grizzly SMS API key.",
                "BAD_ACTION": f"Invalid service code '{service}'. Official Grizzly SMS code for MyJio is 'jio'.",
                "BAD_SERVICE": f"Service code '{clean_service}' is not recognized by Grizzly SMS.",
                "USERS_IP_IS_NOT_ALLOWED": "Grizzly API error: Your IP address is restricted.",
            }
            error_msg = error_mapping.get(text, f"Order failed: {text}")
            return False, {}, error_msg

        except requests.RequestException as e:
            return False, {}, f"Network error during number rental: {e}"

    def set_status(self, activation_id: int, status: int) -> tuple[bool, str]:
        """
        Update status of an activation.
        status=8 -> Cancel and refund immediately
        status=1 -> SMS requested / ready
        status=3 -> Request retry / next SMS
        status=6 -> Complete activation
        """
        if not self.api_key:
            return False, "API key not configured"

        url = (
            f"{GRIZZLY_BASE_URL}?action=setStatus"
            f"&api_key={self.api_key}&id={activation_id}&status={status}"
        )
        status_label = {8: "CANCEL_REFUND", 1: "SMS_REQUESTED", 3: "RETRY", 6: "COMPLETE"}.get(status, str(status))
        log_api_req("GRIZZLY", "GET", f"handler_api.php?action=setStatus", f"id={activation_id}, status={status} ({status_label})")
        t0 = time.monotonic()
        try:
            resp = self.session.get(url, timeout=15)
            elapsed_ms = (time.monotonic() - t0) * 1000
            text = resp.text.strip()
            log_api_res("GRIZZLY", resp.status_code, elapsed_ms, f"Result: {text}")
            
            success_map = {
                8: "ACCESS_CANCEL",
                1: "ACCESS_READY",
                3: "ACCESS_RETRY_GET",
                6: "ACCESS_ACTIVATION",
            }
            expected = success_map.get(status)
            if text == expected or "ACCESS_" in text:
                return True, text
            return False, text
        except requests.RequestException as e:
            return False, str(e)


    def cancel_and_refund(self, activation_id: int) -> tuple[bool, str]:
        """
        Convenience wrapper to cancel activation and refund balance.
        Guarantees zero credit waste.
        """
        log_refund(activation_id, "GRIZZLY", "Auto-Refund Triggered")
        success, msg = self.set_status(activation_id, status=8)
        return success, msg

    def complete_order(self, activation_id: int) -> tuple[bool, str]:
        """Finalize order upon successful claim."""
        return self.set_status(activation_id, status=6)

    def notify_sms_sent(self, activation_id: int) -> tuple[bool, str]:
        """Signal that OTP was dispatched by Jio."""
        return self.set_status(activation_id, status=1)

    def poll_otp(
        self,
        activation_id: int,
        timeout: int = 90,
        poll_interval: int = 3,
        cancellation_token: CancellationToken | None = None,
        progress_callback: Callable[[int, int], Any] | None = None,
    ) -> tuple[bool, str, str]:
        """
        Poll Grizzly SMS for incoming OTP.
        Strictly filters for 6-digit OTP codes (rejects 4-digit codes).
        Respects live cancellation token.
        Returns: (success, otp_code, message)
        """
        deadline = time.monotonic() + timeout
        start_time = time.monotonic()

        while time.monotonic() < deadline:
            # Check for live stop/cancel from user
            if cancellation_token and cancellation_token.is_cancelled:
                self.cancel_and_refund(activation_id)
                return False, "", "Operation aborted by user. Order cancelled & refunded."

            elapsed = int(time.monotonic() - start_time)
            if progress_callback:
                try:
                    progress_callback(elapsed, timeout)
                except Exception:
                    pass

            url = f"{GRIZZLY_BASE_URL}?action=getStatus&api_key={self.api_key}&id={activation_id}"
            t0 = time.monotonic()
            try:
                # Log polling request periodically (every 6s) or on first poll
                should_log_poll = (elapsed % 6 == 0) or (elapsed == 0)
                if should_log_poll:
                    log_api_req("GRIZZLY", "GET", f"handler_api.php?action=getStatus", f"id={activation_id} ({elapsed}s/{timeout}s)")

                resp = self.session.get(url, timeout=12)
                elapsed_ms = (time.monotonic() - t0) * 1000
                text = resp.text.strip()

                if should_log_poll or text.startswith("STATUS_OK:"):
                    log_api_res("GRIZZLY", resp.status_code, elapsed_ms, f"Result: {text}")

                if text.startswith("STATUS_OK:"):
                    raw_code = text.split(":", 1)[1].strip()
                    # User requirement: Strictly match 6-digit OTP
                    six_digit_match = re.search(r"\b(\d{6})\b", raw_code)
                    if six_digit_match:
                        otp = six_digit_match.group(1)
                        log_otp(f"Act#{activation_id}", otp)
                        return True, otp, "Valid 6-digit OTP received!"
                    else:
                        logger.warning(f"Received non-6-digit code ({raw_code}). Waiting for authentic 6-digit MyJio OTP...")

                elif text == "STATUS_CANCEL":
                    return False, "", "Activation was cancelled on Grizzly SMS panel."

            except requests.RequestException as e:
                elapsed_ms = (time.monotonic() - t0) * 1000
                log_api_res("GRIZZLY", 500, elapsed_ms, f"Polling error: {e}")

            time.sleep(poll_interval)

        # Timeout reached: automatically cancel to trigger refund
        self.cancel_and_refund(activation_id)
        return False, "", f"OTP wait timed out after {timeout} seconds. Number cancelled & balance refunded."

    def get_active_activations(self) -> list[dict[str, Any]]:
        """Retrieve all currently active activations from Grizzly SMS."""
        if not self.api_key:
            return []
        url = f"{GRIZZLY_BASE_URL}?action=getActiveActivations&api_key={self.api_key}"
        log_api_req("GRIZZLY", "GET", "handler_api.php?action=getActiveActivations")
        t0 = time.monotonic()
        try:
            resp = self.session.get(url, timeout=15)
            elapsed_ms = (time.monotonic() - t0) * 1000
            data = resp.json()
            items = data if isinstance(data, list) else []
            log_api_res("GRIZZLY", resp.status_code, elapsed_ms, f"Active count: {len(items)}")
            return items
        except Exception as e:
            elapsed_ms = (time.monotonic() - t0) * 1000
            log_api_res("GRIZZLY", 500, elapsed_ms, f"Error: {e}")
            return []


# Global singleton instance
grizzly_client = GrizzlySMSClient()
