"""
Reliance Jio Carrier Validation, Active Status Check, & Gemini 18-Month Activation Engine.
Emulates Pixel 10 Pro mobile identity to interface with Jio Selfcare APIs.
"""
from __future__ import annotations
import re
import html
import logging
from urllib.parse import unquote
from typing import Any
import time
import requests

from config import (
    JIO_CHECK_NUMBER_URL,
    JIO_SEND_OTP_URL,
    JIO_VERIFY_OTP_URL,
    JIO_AUTH_URL,
    JIO_NAVIGATE_URL,
    JIO_ACTIVATE_URL,
    JIO_GOOGLE_URL,
    JIO_SUBMIT_URL,
    JIO_GOOGLE_PAGE,
    COMMON_JIO_HEADERS,
    PROXY,
)
from logger import log_api_req, log_api_res, log_carrier_check, log_bot_info, log_bot_warn, log_bot_err

logger = logging.getLogger(__name__)

ACTIVATION_URL_PATTERN = re.compile(
    r"https?://serviceactivation[.]google[.]com/subscription/new/"
    r"(?P<token>[A-Za-z0-9_-]{50,})(?P<padding>={0,2})",
    re.IGNORECASE,
)


class JioServiceEngine:
    """Manages carrier checks, active subscription checks, OTP sessions, and Gemini claiming."""

    def __init__(self, proxy: str | None = None):
        self.proxy = (proxy or PROXY).strip()
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update(COMMON_JIO_HEADERS)
        if self.proxy:
            session.proxies = {"http": self.proxy, "https": self.proxy}
        return session

    def reset_session(self) -> None:
        """Create a fresh session with cleared cookies and storage."""
        self.session = self._create_session()

    @staticmethod
    def normalize_mobile(raw_number: str) -> str | None:
        """Normalize phone number to clean 10-digit Indian mobile format."""
        digits = re.sub(r"\D", "", str(raw_number or ""))
        if len(digits) > 10 and digits.startswith("91"):
            digits = digits[-10:]
        if len(digits) == 10 and digits[0] in "6789":
            return digits
        return None

    def check_carrier_and_plan(self, mobile: str) -> tuple[bool, bool, dict[str, Any], str]:
        """
        Check whether number is an authentic Reliance Jio number AND actively provisioned.
        Returns: (is_jio, is_active, details_dict, message)
        """
        clean_mobile = self.normalize_mobile(mobile)
        if not clean_mobile:
            return False, False, {}, "Invalid mobile number format."

        headers = {
            **COMMON_JIO_HEADERS,
            "Referer": "https://www.jio.com/selfcare/recharge/mobility/",
        }
        url = JIO_CHECK_NUMBER_URL.format(mobile=clean_mobile)
        log_api_req("JIO", "GET", f"recharge/mobility/number/{clean_mobile}", f"Testing Reliance Jio carrier status")
        t0 = time.monotonic()

        try:
            resp = self.session.get(url, headers=headers, timeout=15)
            elapsed_ms = (time.monotonic() - t0) * 1000
            try:
                data = resp.json()
            except ValueError:
                data = {}

            # 1. Non-Jio detection
            error_msg = str(data.get("errorMessage") or data.get("error") or data.get("message") or "")
            log_api_res("JIO", resp.status_code, elapsed_ms, f"Carrier response: {error_msg or 'OK'}")

            if "not a jio number" in error_msg.lower() or not resp.ok:
                reason = f"Not a Jio number: {error_msg or 'Carrier rejection'}"
                log_carrier_check(clean_mobile, is_jio=False, is_active=False, detail=reason)
                return False, False, data, reason

            # 2. Check for primaryService presence
            primary_service = data.get("primaryService") or data.get("serviceId")
            if not primary_service and not data.get("circle"):
                reason = "No active Jio mobility service detected."
                log_carrier_check(clean_mobile, is_jio=False, is_active=False, detail=reason)
                return False, False, data, reason

            # 3. Active status check
            # Verify subscriber status (ACTIVE vs SUSPENDED, DEACTIVATED, EXPIRED)
            status_field = str(
                data.get("subscriberStatus")
                or data.get("serviceStatus")
                or data.get("status")
                or ""
            ).upper()

            # If explicitly suspended/deactivated
            if any(term in status_field for term in ("SUSPENDED", "INACTIVE", "DEACTIVATED", "DISCONNECTED", "TERMINATED")):
                reason = f"Jio number exists but is inactive ({status_field})."
                log_carrier_check(clean_mobile, is_jio=True, is_active=False, detail=reason)
                return True, False, data, reason

            # Valid active Jio number!
            circle = data.get("circle") or "India"
            service_type = data.get("serviceType") or "Prepaid"
            reason = f"Confirmed Active Jio {service_type} ({circle})"
            log_carrier_check(clean_mobile, is_jio=True, is_active=True, detail=reason)
            return True, True, data, reason

        except requests.RequestException as e:
            elapsed_ms = (time.monotonic() - t0) * 1000
            log_api_res("JIO", 500, elapsed_ms, f"Network error: {e}")
            return False, False, {}, f"Network error checking Jio mobility carrier: {e}"

    def send_otp(self, mobile: str) -> tuple[bool, str]:
        """Send login OTP to Jio number."""
        clean_mobile = self.normalize_mobile(mobile)
        if not clean_mobile:
            return False, "Invalid mobile number"

        headers = {
            **COMMON_JIO_HEADERS,
            "Referer": "https://www.jio.com/selfcare/login/",
        }
        payload = {
            "mobileNumber": clean_mobile,
            "loginFlowType": "MOBILE",
            "alternateNumber": "",
        }

        log_api_req("JIO", "POST", "login/sendOtp", f"mobile={clean_mobile}")
        t0 = time.monotonic()
        try:
            resp = self.session.post(JIO_SEND_OTP_URL, json=payload, headers=headers, timeout=20)
            elapsed_ms = (time.monotonic() - t0) * 1000
            try:
                data = resp.json()
            except ValueError:
                data = {}

            status_str = str(data.get("status", ""))
            log_api_res("JIO", resp.status_code, elapsed_ms, f"Status: {status_str or 'OK'}")

            if resp.ok and not data.get("errorMessage") and status_str.lower() != "failed":
                return True, "OTP successfully dispatched by Jio."

            err = data.get("errorMessage") or data.get("message") or "Failed to send OTP"
            return False, str(err)

        except requests.RequestException as e:
            elapsed_ms = (time.monotonic() - t0) * 1000
            log_api_res("JIO", 500, elapsed_ms, f"Network error: {e}")
            return False, f"Network error sending OTP: {e}"

    def verify_otp(self, mobile: str, otp: str) -> tuple[bool, str]:
        """Validate 6-digit OTP code on Jio and establish authenticated session."""
        clean_mobile = self.normalize_mobile(mobile)
        headers = {
            **COMMON_JIO_HEADERS,
            "Referer": "https://www.jio.com/selfcare/login/",
        }
        payload = {
            "mobileNumber": clean_mobile,
            "otp": otp.strip(),
        }

        log_api_req("JIO", "POST", "login/validateOtp", f"mobile={clean_mobile}, otp={otp.strip()}")
        t0 = time.monotonic()
        try:
            resp = self.session.post(JIO_VERIFY_OTP_URL, json=payload, headers=headers, timeout=20)
            elapsed_ms = (time.monotonic() - t0) * 1000
            try:
                data = resp.json()
            except ValueError:
                data = {}

            status_str = str(data.get("status", ""))
            log_api_res("JIO", resp.status_code, elapsed_ms, f"Status: {status_str or 'OK'}")

            if resp.ok and not data.get("errorMessage") and status_str.lower() != "failed":
                return True, "OTP verified successfully. Authenticated session created."

            err = data.get("errorMessage") or data.get("message") or "Invalid OTP verification response"
            return False, str(err)

        except requests.RequestException as e:
            elapsed_ms = (time.monotonic() - t0) * 1000
            log_api_res("JIO", 500, elapsed_ms, f"Network error: {e}")
            return False, f"Network error verifying OTP: {e}"

    @staticmethod
    def extract_activation_url(text_data: str) -> str:
        """Extract and clean Google One / Gemini tokenized activation link."""
        text = html.unescape(text_data or "")
        for _ in range(4):
            decoded = unquote(text)
            if decoded == text:
                break
            text = decoded

        match = ACTIVATION_URL_PATTERN.search(text)
        if match:
            return f"https://serviceactivation.google.com/subscription/new/{match.group('token')}{match.group('padding')}"
        return ""

    def claim_gemini_18mo(self) -> tuple[bool, str, str]:
        """
        Execute OTT activation pipeline for Google Gemini 18-Month Plan (Z0241).
        Returns: (success, activation_url, message)
        """
        dashboard_headers = {
            **COMMON_JIO_HEADERS,
            "Referer": "https://www.jio.com/selfcare/dashboard/",
        }
        offer_headers = {
            **COMMON_JIO_HEADERS,
            "Referer": JIO_GOOGLE_PAGE,
        }

        try:
            # 1. Verify session authentication
            log_api_req("JIO", "GET", "authenticate/authJsonData", "Checking authenticated session")
            t0 = time.monotonic()
            auth_resp = self.session.get(JIO_AUTH_URL, headers=dashboard_headers, timeout=15)
            elapsed_ms = (time.monotonic() - t0) * 1000
            try:
                auth_data = auth_resp.json()
            except ValueError:
                auth_data = {}

            login_flag = str(auth_data.get("loginFlag", "")).lower()
            log_api_res("JIO", auth_resp.status_code, elapsed_ms, f"loginFlag={login_flag}")

            if not auth_resp.ok or login_flag != "true":
                return False, "", "Jio session is not authenticated or expired."

            # 2. Handshake navigate Z0241
            log_api_req("JIO", "GET", "ott/subscription/navigate/Z0241", "Handshake Z0241 SKU")
            t0 = time.monotonic()
            try:
                nav_resp = self.session.get(JIO_NAVIGATE_URL, headers=dashboard_headers, timeout=15)
                elapsed_ms = (time.monotonic() - t0) * 1000
                log_api_res("JIO", nav_resp.status_code, elapsed_ms, "Navigate OK")
            except requests.RequestException as e:
                log_api_res("JIO", 500, 0, f"Navigate error: {e}")

            # 3. Activate Z0241 subscription
            log_api_req("JIO", "GET", "ott/subscription/activate/Z0241?source=JIO", "Requesting Z0241 activation")
            t0 = time.monotonic()
            activate_resp = self.session.get(JIO_ACTIVATE_URL, headers=offer_headers, timeout=20)
            elapsed_ms = (time.monotonic() - t0) * 1000
            try:
                activate_data = activate_resp.json()
            except ValueError:
                activate_data = {}

            log_api_res("JIO", activate_resp.status_code, elapsed_ms, f"Activate response: {str(activate_data)[:60]}")

            # Check if offer is already availed/active on this number
            act_msg = str(activate_data.get("errorMessage") or activate_data.get("responseMessage") or "").lower()
            if any(phrase in act_msg for phrase in ("already active", "already redeemed", "already claimed", "already availed", "already in use")):
                return False, "", "Google Gemini offer has already been redeemed on this Jio number."

            # 4. Fetch Google AI activation link
            log_api_req("JIO", "GET", "ott/subscription/google-ai", "Fetching Google Gemini activation token URL")
            t0 = time.monotonic()
            google_resp = self.session.get(JIO_GOOGLE_URL, headers=offer_headers, timeout=20)
            elapsed_ms = (time.monotonic() - t0) * 1000
            try:
                google_data = google_resp.json()
            except ValueError:
                google_data = {}

            log_api_res("JIO", google_resp.status_code, elapsed_ms, f"Google-AI response: {str(google_data)[:60]}")

            raw_url = str(google_data.get("redirectionURL") or google_data.get("url") or "")
            claim_url = self.extract_activation_url(raw_url)

            if not claim_url:
                err = google_data.get("errorMessage") or google_data.get("message") or "No redirection URL returned"
                return False, "", f"Could not generate Google AI link: {err}"

            # 5. Finalize submission
            log_api_req("JIO", "GET", "ott/submission/submit", "Finalizing OTT submission")
            t0 = time.monotonic()
            try:
                sub_resp = self.session.get(JIO_SUBMIT_URL, headers=offer_headers, timeout=15)
                elapsed_ms = (time.monotonic() - t0) * 1000
                log_api_res("JIO", sub_resp.status_code, elapsed_ms, "Submission completed")
            except requests.RequestException as e:
                log_api_res("JIO", 500, 0, f"Submit error: {e}")

            return True, claim_url, "Successfully claimed 18-Month Google Gemini Pro Offer!"

        except requests.RequestException as e:
            return False, "", f"Error during Gemini activation flow: {e}"


# Global singleton instance
jio_service = JioServiceEngine()

