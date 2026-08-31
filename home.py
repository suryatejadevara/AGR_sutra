import streamlit as st

from utils.auth import (
    init_session, is_logged_in, current_user, log_in, log_out,
    send_otp_mobile, send_otp_email, try_login_by_contact, validate_phone,
)
from utils.data_store import create_or_update_user

st.set_page_config(page_title="AGR Sutra", page_icon="🌱", layout="centered")
init_session()

LANGUAGE_OPTIONS = [
    "English", "हिंदी (Hindi)", "मराठी (Marathi)", "தமிழ் (Tamil)",
    "తెలుగు (Telugu)", "বাংলা (Bengali)", "ગુજરાતી (Gujarati)",
]

# -------------------- Already logged in --------------------
if is_logged_in():
    user = current_user()
    st.title("🌱 AGR Sutra")
    st.success(f"Welcome back, **{user['full_name']}**! You're logged in as a **{user['role']}**.")

    col1, col2 = st.columns(2)
    with col1:
        if user["role"] == "Seller":
            if st.button("Go to Seller Dashboard →", type="primary", use_container_width=True):
                st.switch_page("pages/1_Seller_Dashboard.py")
        else:
            if st.button("Go to Buyer Home →", type="primary", use_container_width=True):
                st.switch_page("pages/6_Buyer_Home.py")
    with col2:
        if st.button("Log out", use_container_width=True):
            log_out()
            st.rerun()
    st.stop()

# -------------------- Step: Welcome --------------------
step = st.session_state["auth_step"]

st.markdown(
    "<h1 style='text-align:center;'>🌱 AGR Sutra</h1>"
    "<p style='text-align:center;color:gray;'>AI-Driven Market Linkage & Smart Cataloging"
    "<br>for Marginalized Artisans</p>",
    unsafe_allow_html=True,
)
st.divider()

if step == "welcome":
    st.markdown("#### Tradition meets the Digital World")
    st.write("List your handmade products in minutes, or discover authentic handmade goods from artisans across India.")
    if st.button("Get Started →", type="primary", use_container_width=True):
        st.session_state["auth_step"] = "login"
        st.rerun()

# -------------------- Step: Login / Sign up (choose channel) --------------------
elif step == "login":
    st.markdown("#### Welcome — Login or Sign up to continue")
    tab_mobile, tab_email = st.tabs(["📱 Continue with Mobile", "✉️ Continue with Email"])

    with tab_mobile:
        phone = st.text_input(
            "Mobile Number", placeholder="9876543210 or +919876543210", key="phone_input"
        )
        if st.button("Send OTP", key="send_otp_mobile", type="primary", use_container_width=True):
            if phone.strip():
                is_valid, result = validate_phone(phone)
                if is_valid:
                    otp = send_otp_mobile(result)
                    st.session_state["auth_step"] = "otp_mobile"
                    st.info(f"🔐 DEMO MODE — your OTP is **{otp}** (no real SMS is sent in this build).")
                    st.rerun()
                else:
                    st.warning(result)
            else:
                st.warning("Please enter your mobile number.")

    with tab_email:
        email = st.text_input("Email address", placeholder="name@gmail.com", key="email_input")
        if st.button("Send OTP", key="send_otp_email", type="primary", use_container_width=True):
            if email.strip():
                otp = send_otp_email(email.strip())
                st.session_state["auth_step"] = "otp_email"
                st.info(f"🔐 DEMO MODE — your OTP is **{otp}** (no real email is sent in this build).")
                st.rerun()
            else:
                st.warning("Please enter your email address.")

    if st.button("← Back"):
        st.session_state["auth_step"] = "welcome"
        st.rerun()

# -------------------- Step: OTP verification --------------------
elif step in ("otp_mobile", "otp_email"):
    channel = "phone" if step == "otp_mobile" else "email"
    target = st.session_state.get("pending_phone") if channel == "phone" else st.session_state.get("pending_email")
    otp_key = "otp_mobile" if channel == "phone" else "otp_email"

    st.markdown(f"#### Verify your {'Mobile Number' if channel == 'phone' else 'Email'}")
    st.write(f"Enter the 6-digit code sent to **{target}**")

    entered = st.text_input("6-digit code", max_chars=6, key=f"entered_{otp_key}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Verify", type="primary", use_container_width=True):
            if entered.strip() == st.session_state.get(otp_key):
                # Returning user? Skip profile creation and log them straight in.
                existing = try_login_by_contact(
                    phone=st.session_state.get("pending_phone", ""),
                    email=st.session_state.get("pending_email", ""),
                )
                if existing:
                    log_in(existing)
                    st.rerun()
                else:
                    st.session_state["auth_step"] = "profile"
                    st.success("Verified!")
                    st.rerun()
            else:
                st.error("Incorrect code — please try again.")
    with col2:
        if st.button("Resend OTP", use_container_width=True):
            fresh = send_otp_mobile(target) if channel == "phone" else send_otp_email(target)
            st.info(f"🔐 New OTP: **{fresh}**")

    if st.button("← Back"):
        st.session_state["auth_step"] = "login"
        st.rerun()

# -------------------- Step: Profile setup --------------------
elif step == "profile":
    st.markdown("#### Create your account")
    full_name = st.text_input("Full Name", key="profile_name")
    phone = st.session_state.get("pending_phone", "")
    email = st.session_state.get("pending_email", "")
    phone = st.text_input("Mobile Number", value=phone, placeholder="9876543210 or +919876543210")
    email = st.text_input("Email (optional)", value=email)
    pin_code = st.text_input("Pin Code (optional)")
    language = st.selectbox("Preferred Language", LANGUAGE_OPTIONS)

    if st.button("Continue →", type="primary", use_container_width=True):
        if not full_name.strip() or not (phone.strip() or email.strip()):
            st.warning("Please enter your name and at least one contact method.")
        else:
            cleaned_phone = phone.strip()
            phone_ok = True
            if phone.strip():
                phone_ok, result = validate_phone(phone)
                if phone_ok:
                    cleaned_phone = result
            if not phone_ok:
                st.warning(result)
            else:
                st.session_state["profile_draft"] = {
                    "full_name": full_name.strip(), "phone": cleaned_phone,
                    "email": email.strip(), "pin_code": pin_code.strip(),
                    "language": language,
                }
                st.session_state["auth_step"] = "role"
                st.rerun()

    if st.button("← Back"):
        st.session_state["auth_step"] = "login"
        st.rerun()

# -------------------- Step: Role selection --------------------
elif step == "role":
    st.markdown("#### How will you use AGR Sutra?")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### 🧑‍🎨 Seller / Artisan")
        st.caption("List and sell your handmade products")
        pick_seller = st.button("I am a Seller", use_container_width=True)
    with col2:
        st.markdown("##### 🛒 Buyer")
        st.caption("Discover & buy unique handmade products")
        pick_buyer = st.button("I am a Buyer", use_container_width=True)

    role = None
    if pick_seller:
        role = "Seller"
    elif pick_buyer:
        role = "Buyer"

    if role:
        draft = st.session_state.get("profile_draft", {})
        user = create_or_update_user(
            full_name=draft.get("full_name", "Guest"),
            phone=draft.get("phone", ""),
            email=draft.get("email", ""),
            pin_code=draft.get("pin_code", ""),
            language=draft.get("language", "English"),
            role=role,
        )
        log_in(user)
        st.session_state["auth_step"] = "welcome"
        st.rerun()

    if st.button("← Back"):
        st.session_state["auth_step"] = "profile"
        st.rerun()