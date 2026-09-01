"""
utils/geo.py
-------------
Shared browser-geolocation capture helper.

Used by both Profile Settings and Add Product so a seller's location can
be captured / refreshed from any page that needs it, using the same
accurate, no-cache GPS request and the same query-param handoff back
into Streamlit. Previously this logic (and a near-identical
`_valid_coord` helper) was duplicated in 11_Profile_Settings.py and
8_Product_Detail.py -- centralizing it here means a fix (like the
high-accuracy options below) only needs to happen once.
"""

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from utils.data_store import update_user_profile


def request_browser_location(height: int = 60):
    """Renders a small JS snippet that asks the browser for the visitor's
    current GPS position and redirects back with ?lat=&lon= in the URL.

    Streamlit's components.html() renders this snippet inside a sandboxed
    iframe that does NOT get an `allow="geolocation"` attribute, so the
    Permissions Policy blocks `navigator.geolocation` on the iframe's own
    `navigator` even though the iframe is same-origin with the app.
    Calling it on `window.parent.navigator` instead reaches the actual
    top-level page, which does have geolocation permission (assuming the
    page is served over HTTPS or localhost and the user grants access).

    enableHighAccuracy=True + maximumAge=0 forces the device to get a
    fresh GPS fix instead of returning a cached / coarse network-based
    location -- without these, `getCurrentPosition` is free to hand back
    a stale or low-precision fix (sometimes several km off, or a location
    from hours earlier), which is the opposite of "current location."
    timeout gives the device enough time to get a real GPS lock
    (especially indoors or on a cold start) before giving up.
    """
    components.html(
        """
        <script>
        const statusEl = document.getElementById('geo-status');
        let settled = false;

        function showError(message) {
            if (settled) return;
            settled = true;
            statusEl.innerText = message;
            statusEl.style.color = 'crimson';
        }

        function handleSuccess(pos) {
            if (settled) return;
            settled = true;
            const lat = pos.coords.latitude;
            const lon = pos.coords.longitude;
            const url = new URL(window.parent.location.href);
            url.searchParams.set('lat', lat);
            url.searchParams.set('lon', lon);
            window.parent.location.href = url.toString();
        }

        // Belt-and-braces timeout: some browser/host combinations can
        // leave getCurrentPosition() hanging with neither callback ever
        // firing (e.g. a permission prompt that never renders). The
        // browser's own `timeout` option in getCurrentPosition does NOT
        // reliably cover this case, so we run our own clock too.
        const watchdog = setTimeout(() => {
            showError(
                'This is taking longer than expected. Your browser may ' +
                'not have shown a permission prompt, or location access ' +
                'is blocked in this context. Please check your browser\\'s ' +
                'address bar for a blocked-permission icon, or enter your ' +
                'location manually.'
            );
        }, 12000);

        try {
            const parentGeo = window.parent && window.parent.navigator
                ? window.parent.navigator.geolocation
                : null;

            if (!parentGeo) {
                clearTimeout(watchdog);
                showError(
                    'Location access isn\\'t available in this context ' +
                    '(the page must be served over HTTPS, or localhost, ' +
                    'for browser location to work). Please enter your ' +
                    'location manually instead.'
                );
            } else {
                parentGeo.getCurrentPosition(
                    (pos) => { clearTimeout(watchdog); handleSuccess(pos); },
                    (err) => {
                        clearTimeout(watchdog);
                        showError(
                            'Could not get location: ' + err.message +
                            ' — please allow location access and try again.'
                        );
                    },
                    {
                        enableHighAccuracy: true,
                        timeout: 10000,
                        maximumAge: 0
                    }
                );
            }
        } catch (e) {
            clearTimeout(watchdog);
            showError(
                'Could not reach the browser\\'s location service from ' +
                'this embedded widget (' + e.message + '). Please enter ' +
                'your location manually instead.'
            );
        }
        </script>
        <p id="geo-status" style="font-family:sans-serif;color:gray;">
            Requesting location permission from your browser...
        </p>
        """,
        height=height,
    )


def consume_location_query_params(user_id: str) -> dict | None:
    """Checks the URL for ?lat=&lon= (set by request_browser_location's
    redirect) and, if present, saves them to the given user's profile.

    Returns the updated user dict if a location was just saved (so the
    caller can refresh the session with log_in(updated) and st.rerun()),
    or None if there was nothing new to consume.
    """
    query_lat = st.query_params.get("lat")
    query_lon = st.query_params.get("lon")
    if not (query_lat and query_lon):
        return None

    updated = update_user_profile(user_id, latitude=query_lat, longitude=query_lon)
    st.query_params.clear()
    return updated


def valid_coord(value) -> float | None:
    """Returns a clean float for a real, non-missing coordinate, or None.
    Handles pandas NaN/pd.NA/None/blank strings -- a plain string check
    misses float NaN, which is what pandas stores for an empty CSV cell.
    Shared by every page that reads a saved lat/lon back out."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    if text == "" or text.lower() == "nan":
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None