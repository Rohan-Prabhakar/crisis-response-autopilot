import streamlit as st
import streamlit.components.v1 as components

# ── Config ────────────────────────────────────────────────────────────────
MISTRAL_API_KEY = "Fc8xV6GKnoyQ4vxaJenqINgwr1EfwTUz"
# ─────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Crisis Response Autopilot",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body { font-family: 'Inter', sans-serif !important; background: #0d1117 !important; }
.stApp, .main, section[data-testid="stMain"],
[data-testid="stAppViewContainer"] { background: #0d1117 !important; }

/* Force Inter everywhere — but NOT on Material Icons spans (they need their own font) */
.stApp *:not([data-testid="stIconMaterial"]):not(.material-icons) {
    font-family: 'Inter', sans-serif !important;
}

/* ── Expander — fix Material Icons arrow showing as text ── */
/* The arrow icon lives in a <span> with font-family: Material Icons.
   We must NOT override that span's font-family or the icon disappears.
   We only override the label text, not the icon span itself. */
div[data-testid="stExpander"] { 
    border: 1px solid #21262d !important; 
    border-radius: 8px !important; 
    background: #161b22 !important;
}
div[data-testid="stExpander"] summary {
    cursor: pointer !important;
    padding: 0.6rem 0.8rem !important;
    list-style: none !important;
}
div[data-testid="stExpander"] summary::-webkit-details-marker { display: none; }
/* Label text inside expander summary — target the p tag only */
div[data-testid="stExpander"] summary p {
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
    color: #8b949e !important;
    font-weight: 500 !important;
    margin: 0 !important;
}
/* The icon span — let it keep Material Icons font, just control size */
div[data-testid="stExpander"] summary svg {
    width: 16px !important;
    height: 16px !important;
    color: #6e7681 !important;
}

/* Body text */
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li {
    font-size: 15px !important;
    color: #c9d1d9 !important;
    line-height: 1.7 !important;
}
[data-testid="stMarkdownContainer"] span {
    font-size: inherit !important;
    color: inherit !important;
}
section[data-testid="stMain"] h1, section[data-testid="stMain"] [data-testid="stMarkdownContainer"] h1 { font-size: 1.6rem !important; color: #f0f6fc !important; font-weight: 700 !important; }
section[data-testid="stMain"] h2, section[data-testid="stMain"] [data-testid="stMarkdownContainer"] h2 { font-size: 1.2rem !important; color: #f0f6fc !important; font-weight: 600 !important; margin: 1.2rem 0 0.5rem !important; }
section[data-testid="stMain"] h3, section[data-testid="stMain"] [data-testid="stMarkdownContainer"] h3 { font-size: 1.0rem !important; color: #e6edf3 !important; font-weight: 600 !important; margin: 1rem 0 0.4rem !important; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] { background: transparent !important; border-bottom: 1px solid #21262d !important; gap: 0 !important; }
.stTabs [data-baseweb="tab"] { font-size: 13px !important; font-weight: 500 !important; color: #6e7681 !important; padding: 0.65rem 1.4rem !important; background: transparent !important; border: none !important; border-bottom: 2px solid transparent !important; }
.stTabs [data-baseweb="tab"][aria-selected="true"] { color: #f0f6fc !important; border-bottom: 2px solid #58a6ff !important; }
.stTabs [data-baseweb="tab"]:hover { color: #c9d1d9 !important; }
.stTabs [data-baseweb="tab-panel"] { padding-top: 1.4rem !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] { background: #010409 !important; border-right: 1px solid #21262d !important; }
/* Sidebar text — 12px, keep specificity high */
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { font-size: 12px !important; color: #8b949e !important; line-height: 1.5 !important; }
[data-testid="stSidebar"] label { font-size: 12px !important; color: #8b949e !important; }
[data-testid="stSidebar"] input { font-size: 13px !important; }
[data-testid="stSidebar"] button { font-size: 12px !important; }
[data-testid="stSidebar"] [data-baseweb="tag"] span { font-size: 12px !important; color: #c9d1d9 !important; }
/* Sidebar expander labels specifically */
[data-testid="stSidebar"] div[data-testid="stExpander"] summary p { font-size: 12px !important; color: #8b949e !important; }
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p { font-size: 11px !important; color: #6e7681 !important; }

/* ── Sidebar collapse/expand toggle button — must be visible ── */
[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarCollapsedControl"] button,
button[kind="headerNoPadding"],
[data-testid="collapsedControl"] {
    background: #161b22 !important;
    border: 1px solid #30363d !important;
    color: #c9d1d9 !important;
    opacity: 1 !important;
    visibility: visible !important;
}
/* The > arrow icon inside the toggle */
[data-testid="stSidebarCollapsedControl"] svg,
[data-testid="collapsedControl"] svg {
    color: #c9d1d9 !important;
    fill: #c9d1d9 !important;
}

/* ── Metric cards ── */
.metric-card { background: #161b22 !important; border: 1px solid #21262d !important; border-radius: 8px !important; padding: 1.2rem 1rem !important; text-align: center !important; }
.metric-card h3 { font-size: 1.8rem !important; font-weight: 700 !important; margin: 0 0 0.3rem 0 !important; letter-spacing: -0.02em !important; }
.metric-card p { font-size: 11px !important; color: #8b949e !important; margin: 0 !important; text-transform: uppercase !important; letter-spacing: 0.07em !important; font-weight: 500 !important; }

/* ── Inputs ── */
[data-testid="stTextInput"] input { font-size: 14px !important; color: #e6edf3 !important; background: #161b22 !important; border: 1px solid #30363d !important; border-radius: 6px !important; }
[data-testid="stTextInput"] input::placeholder { color: #6e7681 !important; }
[data-testid="stTextInput"] input:focus { border-color: #58a6ff !important; box-shadow: 0 0 0 3px rgba(88,166,255,0.12) !important; }

/* ── Buttons ── */
.stButton button { font-size: 14px !important; font-weight: 500 !important; border-radius: 6px !important; }

/* ── Multiselect ── */
[data-baseweb="tag"] { background: #21262d !important; }
[data-baseweb="tag"] span { font-size: 12px !important; color: #c9d1d9 !important; }

/* ── Dataframe ── */
[data-testid="stDataFrame"] { border: 1px solid #21262d !important; border-radius: 8px !important; }

/* ── Caption ── */
[data-testid="stCaptionContainer"] p { font-size: 12px !important; color: #6e7681 !important; }

/* ── Location bar ── */
.loc-bar { display:flex; align-items:center; gap:10px; padding:12px 14px; background:#161b22; border:1px solid #21262d; border-radius:8px; margin-bottom:1rem; }
.loc-dot { width:9px; height:9px; border-radius:50%; background:#3fb950; box-shadow:0 0 7px #3fb95060; flex-shrink:0; }
.loc-dot.pending { background:#30363d; box-shadow:none; animation:pulse 1.5s infinite; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
.loc-label { font-size:11px !important; color:#6e7681 !important; text-transform:uppercase; letter-spacing:0.08em; display:block; }
.loc-name  { font-size:13px !important; color:#f0f6fc !important; font-weight:600 !important; display:block; margin-top:2px; }

/* ── Sidebar section label ── */
.sidebar-label { font-size:11px !important; font-weight:600 !important; letter-spacing:0.1em !important; text-transform:uppercase !important; color:#6e7681 !important; margin:1.2rem 0 0.4rem; display:block; }

#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
/* header intentionally NOT hidden — contains sidebar collapse button */
</style>
""", unsafe_allow_html=True)

# ── Geolocation — inject JS that writes to query params and reloads once ──
# Uses window.parent because Streamlit embeds content in iframes.
# sessionStorage guards against infinite reload loops.
components.html("""
<script>
(function() {
    try {
        var done = window.parent.sessionStorage.getItem('_geo_done');
        if (done) return;
        if (!window.parent.navigator.geolocation) {
            window.parent.sessionStorage.setItem('_geo_done','1');
            return;
        }
        window.parent.navigator.geolocation.getCurrentPosition(
            function(pos) {
                window.parent.sessionStorage.setItem('_geo_done','1');
                var lat = pos.coords.latitude.toFixed(6);
                var lon = pos.coords.longitude.toFixed(6);
                var url = new URL(window.parent.location.href);
                if (url.searchParams.get('_lat') !== lat || url.searchParams.get('_lon') !== lon) {
                    url.searchParams.set('_lat', lat);
                    url.searchParams.set('_lon', lon);
                    window.parent.location.replace(url.toString());
                }
            },
            function() { window.parent.sessionStorage.setItem('_geo_done','1'); },
            { timeout: 8000, maximumAge: 300000, enableHighAccuracy: false }
        );
    } catch(e) {}
})();
</script>
""", height=0)

# ── Read coords from query params set by JS above ─────────────────────────
from components.location_picker import reverse_geocode, geocode_city

qp = st.query_params
if "_lat" in qp and "_lon" in qp:
    try:
        raw_lat = float(qp["_lat"])
        raw_lon = float(qp["_lon"])
        cached  = st.session_state.get("user_location", {})
        if abs(cached.get("lat", 0) - raw_lat) > 0.001 or abs(cached.get("lon", 0) - raw_lon) > 0.001:
            with st.spinner("Detecting your location..."):
                geo = reverse_geocode(raw_lat, raw_lon)
            st.session_state["user_location"] = {
                "lat": raw_lat, "lon": raw_lon,
                "state":   geo.get("state") or "All States",
                "display": geo.get("display", "Your location"),
                "source":  "browser"
            }
    except Exception:
        pass

if "user_location" not in st.session_state:
    st.session_state["user_location"] = {
        "lat": 39.8283, "lon": -98.5795,
        "state": "All States",
        "display": "Not set — pick on map",
        "source": "default"
    }

user_loc     = st.session_state["user_location"]
state_filter = user_loc.get("state") or "All States"

# Clear stale geo cache once per session (version bump forces re-geocoding)
if st.session_state.get("_geo_cache_version") != "v2":
    st.session_state.pop("fema_geo_cache", None)
    st.session_state["_geo_cache_version"] = "v2"

# ── Header ─────────────────────────────────────────────────────────────────
st.markdown("""
<div style="padding:1.6rem 0 1.2rem;border-bottom:1px solid #21262d;margin-bottom:1.8rem;
            display:flex;align-items:center;gap:1.4rem">
  <span style="font-size:1.35rem;font-weight:700;color:#f0f6fc;letter-spacing:-0.025em">
    Crisis Response Autopilot
  </span>
  <span style="font-size:11px;color:#6e7681;letter-spacing:0.08em;text-transform:uppercase;font-weight:500">
    Multi-Agent &nbsp;&middot;&nbsp; CrewAI &nbsp;&middot;&nbsp; Mistral
  </span>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    import folium
    from streamlit_folium import st_folium

    is_set    = user_loc.get("source") != "default"
    dot_cls   = "loc-dot" if is_set else "loc-dot pending"
    loc_label = "Current location" if user_loc.get("source") == "browser" else \
                "Selected location" if is_set else "Location not set"

    st.markdown(
        f'<div class="loc-bar">'
        f'<div class="{dot_cls}"></div>'
        f'<div style="flex:1;min-width:0">'
        f'<span class="loc-label">{loc_label}</span>'
        f'<span class="loc-name">{user_loc["display"]}</span>'
        f'</div></div>',
        unsafe_allow_html=True
    )

    with st.expander("Set location", expanded=not is_set):
        st.caption("Click the map or search to update your location.")

        m = folium.Map(
            location=[user_loc["lat"], user_loc["lon"]],
            zoom_start=4 if not is_set else 8,
            tiles="CartoDB dark_matter", prefer_canvas=True
        )
        if is_set:
            folium.CircleMarker(
                location=[user_loc["lat"], user_loc["lon"]],
                radius=9, color="#3fb950", fill=True,
                fill_color="#3fb950", fill_opacity=0.9, weight=2,
                tooltip=user_loc["display"]
            ).add_to(m)
            folium.CircleMarker(
                location=[user_loc["lat"], user_loc["lon"]],
                radius=20, color="#3fb950", fill=False, weight=1, opacity=0.3
            ).add_to(m)

        map_result = st_folium(m, width=None, height=240,
                               returned_objects=["last_clicked"], key="loc_picker_map")

        clicked = (map_result or {}).get("last_clicked")
        if clicked and isinstance(clicked, dict):
            nlat, nlng = clicked.get("lat"), clicked.get("lng")
            if nlat and nlng:
                with st.spinner("Finding location..."):
                    geo = reverse_geocode(nlat, nlng)
                st.session_state["user_location"] = {
                    "lat": nlat, "lon": nlng,
                    "state":   geo.get("state") or "All States",
                    "display": geo.get("display", f"{nlat:.2f}, {nlng:.2f}"),
                    "source":  "map_click"
                }
                st.session_state.pop("area_alerts_cache", None)
                st.rerun()

        col_s, col_b = st.columns([3, 1])
        with col_s:
            city_q = st.text_input("city", placeholder="e.g. Miami, FL",
                                   label_visibility="collapsed", key="city_search")
        with col_b:
            if st.button("Go", use_container_width=True, key="city_go"):
                if city_q.strip():
                    with st.spinner("Searching..."):
                        res = geocode_city(city_q.strip())
                    if res:
                        st.session_state["user_location"] = res
                        st.session_state.pop("area_alerts_cache", None)
                        st.rerun()
                    else:
                        st.error("Location not found.")

    st.markdown('<span class="sidebar-label">Severity filter</span>', unsafe_allow_html=True)
    severity_filter = st.multiselect(
        "sev", ["Extreme", "Severe", "Moderate", "Minor"],
        default=["Extreme", "Severe", "Moderate", "Minor"],
        label_visibility="collapsed"
    )

    # Show reset button only when a location is set
    if is_set:
        st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)
        if st.button("View all US alerts", use_container_width=True, key="reset_location"):
            st.session_state["user_location"] = {
                "lat": 39.8283, "lon": -98.5795,
                "state": "All States",
                "display": "All United States",
                "source": "default"
            }
            st.session_state.pop("area_alerts_cache", None)
            st.session_state.pop("selected_idx", None)
            st.session_state.pop("incident_result", None)
            st.session_state.pop("active_panel", None)
            st.rerun()

# ── Tabs ───────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["Live Feed", "Historical Archive", "Safety Chat"])

with tab1:
    from tabs.live_feed import render_live_feed
    render_live_feed(state_filter, severity_filter, user_loc, MISTRAL_API_KEY)

with tab2:
    from tabs.historical import render_historical
    render_historical(state_filter, severity_filter)

with tab3:
    from tabs.safety_chat import render_safety_chat
    render_safety_chat(MISTRAL_API_KEY)
