import pandas as pd
import streamlit as st

from utils.auth import require_login, current_user, log_in, log_out, validate_phone
from utils.data_store import update_user_profile, get_buyer_rating, format_stars
from utils.geo import request_browser_location, consume_location_query_params, valid_coord

st.set_page_config(page_title="AGR Sutra — Profile Settings", page_icon="⚙️", layout="centered")

user = require_login()

LANGUAGE_OPTIONS = [
    "English", "हिंदी (Hindi)", "मराठी (Marathi)", "தமிழ் (Tamil)",
    "తెలుగు (Telugu)", "বাংলা (Bengali)", "ગુજરાતી (Gujarati)",
]

st.title("⚙️ Profile Settings")

home_page = "pages/1_Seller_Dashboard.py" if user["role"] == "Seller" else "pages/6_Buyer_Home.py"
if st.button("← Back"):
    st.switch_page(home_page)

st.divider()

st.markdown(f"#### {user['full_name']}")
st.caption(f"Role: {user['role']}")

if user["role"] == "Buyer":
    avg_rating, review_count = get_buyer_rating(user["user_id"])
    if review_count > 0:
        st.markdown(f"{format_stars(avg_rating)} **{avg_rating}** buyer rating · rated by {review_count} seller{'s' if review_count != 1 else ''}")
    else:
        st.caption("☆☆☆☆☆ No seller ratings yet")

st.divider()

# -------------------- Edit profile --------------------
st.markdown("#### Edit Details")

full_name = st.text_input("Full Name", value=user.get("full_name", ""))
phone = st.text_input("Mobile Number", value=user.get("phone", ""), placeholder="9876543210 or +919876543210")
email = st.text_input("Email", value=user.get("email", ""))
pin_code = st.text_input("Pin Code", value=user.get("pin_code", ""))

st.divider()
st.markdown("#### 📍 Location")

# Pick up lat/lon once the browser redirects back with them in the URL
updated_user = consume_location_query_params(user["user_id"])
if updated_user:
    log_in(updated_user)  # refresh session with the latest profile data
    user = updated_user
    st.success("Location saved!")
    st.rerun()

existing_lat = valid_coord(user.get("latitude"))
existing_lon = valid_coord(user.get("longitude"))

if existing_lat is not None and existing_lon is not None:
    st.caption(f"Current saved location: {existing_lat:.5f}, {existing_lon:.5f}")
    st.map(pd.DataFrame({"lat": [existing_lat], "lon": [existing_lon]}))
else:
    st.caption("No location saved yet.")

if st.button("📍 Use My Current Location", use_container_width=True):
    request_browser_location()

st.divider()

current_language = user.get("language", "English")
lang_index = LANGUAGE_OPTIONS.index(current_language) if current_language in LANGUAGE_OPTIONS else 0
language = st.selectbox("Preferred Language", LANGUAGE_OPTIONS, index=lang_index)

if st.button("💾 Save Changes", type="primary", use_container_width=True):
    if not full_name.strip():
        st.warning("Full name cannot be empty.")
    elif not phone.strip() and not email.strip():
        st.warning("Please provide at least a mobile number or email.")
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
            updated = update_user_profile(
                user["user_id"],
                full_name=full_name.strip(),
                phone=cleaned_phone,
                email=email.strip(),
                pin_code=pin_code.strip(),
                language=language,
            )
            if updated:
                log_in(updated)  # refresh session with the latest profile data
                st.success("Profile updated successfully!")
                st.rerun()
            else:
                st.error("Couldn't update your profile — please try again.")

st.divider()

if st.button("Log out", use_container_width=True):
    log_out()
    st.switch_page("home.py")