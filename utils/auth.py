"""
utils/auth.py
--------------
Session-state auth for the demo build:
  - init_session()        : sets safe defaults on first load
  - is_logged_in() / current_user() / log_in() / log_out()
  - require_login()       : page guard, optionally role-restricted
  - validate_phone()      : Indian mobile number format check
  - send_otp_mobile() / send_otp_email() : demo OTP issuance (no real SMS/email)
  - try_login_by_contact(): looks up an existing user so returning users
                             skip re-entering their profile

Everything here is *session-only* (st.session_state) and disappears on
logout / tab close. Permanent user records live in data_store.py.
"""

import random
import re

import streamlit as st

from utils.data_store import get_user_by_contact


# =====================================================================
# Session bootstrapping
# =====================================================================
def init_session():
    """Call once at the top of Home.py before reading any auth_step."""
    st.session_state.setdefault("user", None)
    st.session_state.setdefault("auth_step", "welcome")
    st.session_state.setdefault("otp_mobile", None)
    st.session_state.setdefault("otp_email", None)
    st.session_state.setdefault("pending_phone", "")
    st.session_state.setdefault("pending_email", "")


# =====================================================================
# Session state accessors
# =====================================================================
def is_logged_in() -> bool:
    return st.session_state.get("user") is not None


def current_user() -> dict | None:
    return st.session_state.get("user")


def log_in(user: dict):
    st.session_state["user"] = user


def log_out():
    """Clear everything auth-related and reset to the welcome step."""
    for key in (
        "user", "otp_mobile", "otp_email",
        "pending_phone", "pending_email",
        "profile_draft",
    ):
        st.session_state.pop(key, None)
    st.session_state["auth_step"] = "welcome"


# =====================================================================
# Phone validation
# =====================================================================
# Accepts either:
#   - a plain 10-digit Indian mobile number, e.g. "9876543210"
#   - a "+91" country-code-prefixed number, e.g. "+919876543210"
#     (exactly 13 characters: '+91' + 10 digits)
_PLAIN_PHONE_RE = re.compile(r"^\d{10}$")
_STD_CODE_PHONE_RE = re.compile(r"^\+91\d{10}$")


def validate_phone(phone: str) -> tuple[bool, str]:
    """
    Validates & normalizes a mobile number.

    Returns (True, cleaned_number) on success, where cleaned_number has
    spaces/dashes stripped but is otherwise unchanged (still either
    10 digits, or "+91" + 10 digits).

    Returns (False, error_message) on failure.
    """
    cleaned = re.sub(r"[\s\-()]", "", phone or "")

    if _STD_CODE_PHONE_RE.match(cleaned):
        return True, cleaned
    if _PLAIN_PHONE_RE.match(cleaned):
        return True, cleaned

    return False, (
        "Enter a valid mobile number — either exactly 10 digits "
        "(e.g. 9876543210), or with the country code as +91 followed "
        "by 10 digits (e.g. +919876543210)."
    )


# =====================================================================
# Page guard
# =====================================================================
def require_login(required_role: str | None = None) -> dict:
    """
    Call at the top of any protected page:
        user = require_login(required_role="Seller")

    Stops the page (st.stop()) if the visitor isn't logged in, or is
    logged in as the wrong role. Returns the user dict on success so
    callers can use user["user_id"], user["full_name"], etc.
    """
    if not is_logged_in():
        st.warning("🔒 Please log in to continue.")
        if st.button("Go to Login"):
            st.switch_page("home.py")
        st.stop()

    user = current_user()

    if required_role and user.get("role") != required_role:
        st.error(f"🚫 This page is only available to {required_role}s.")
        st.caption(f"You're logged in as a {user.get('role')}.")
        if st.button("← Back to Home"):
            st.switch_page("home.py")
        st.stop()

    return user


# =====================================================================
# OTP (demo mode — no real SMS/email provider wired up)
# =====================================================================
def _generate_otp() -> str:
    return f"{random.randint(0, 999999):06d}"


def send_otp_mobile(phone: str) -> str:
    otp = _generate_otp()
    st.session_state["otp_mobile"] = otp
    st.session_state["pending_phone"] = phone
    return otp


def send_otp_email(email: str) -> str:
    otp = _generate_otp()
    st.session_state["otp_email"] = otp
    st.session_state["pending_email"] = email
    return otp


# =====================================================================
# Returning-user shortcut
# =====================================================================
def try_login_by_contact(phone: str = "", email: str = "") -> dict | None:
    """
    After OTP verification, check whether this phone/email already
    belongs to a registered user. If so, return their record so
    Home.py can log them straight in and skip the profile-creation
    step. Returns None for first-time users.
    """
    return get_user_by_contact(phone=phone, email=email)