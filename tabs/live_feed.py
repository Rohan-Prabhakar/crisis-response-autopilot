"""
Tab 1: Live Feed
- Map shows all active NOAA alerts
- Click a marker to select it — shows two action buttons: What to Do / Contact Help
- Each button runs the agent tool chain and renders targeted info
"""

import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import json
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.crisis_tools import NOAAAlertFetcher, MOCK_NOAA_ALERTS

SEVERITY_COLORS = {
    "Extreme":  "#ef4444",
    "Severe":   "#f97316",
    "Moderate": "#eab308",
    "Minor":    "#22c55e",
    "Unknown":  "#64748b"
}

def sev_pill(sev):
    c = SEVERITY_COLORS.get(sev, "#64748b")
    return (f'<span style="background:{c}18;color:{c};border:1px solid {c}40;'
            f'padding:3px 10px;border-radius:4px;font-size:13px;font-weight:600;'
            f'letter-spacing:0.06em;font-family:monospace">{sev.upper()}</span>')

def section_lbl(text):
    return (f'<p style="font-size:13px;font-weight:600;letter-spacing:0.1em;'
            f'text-transform:uppercase;color:#6e7681;margin:1.4rem 0 0.55rem 0">{text}</p>')

def get_alerts(state_filter, severity_filter):
    fetcher = NOAAAlertFetcher()
    state = state_filter if state_filter != "All States" else None
    try:
        raw  = fetcher._run(state=state)
        alerts = json.loads(raw).get("alerts", [])
    except Exception:
        alerts = list(MOCK_NOAA_ALERTS)
    if severity_filter:
        alerts = [a for a in alerts if a.get("severity", "Unknown") in severity_filter]
    return alerts

def run_tools(alert: dict, user_loc: dict) -> dict:
    """Run tool pipeline — contextual based on user location + FEMA history."""
    from tools.crisis_tools import GeoFilter, CrisisSignalAmplifier, FEMADisasterFetcher, LiveContactFetcher

    user_lat = user_loc.get("lat", 39.8)
    user_lon = user_loc.get("lon", -98.5)
    state    = alert.get("state", "")
    city     = user_loc.get("display", "")
    event    = alert.get("event", "")
    area     = alert.get("areaDesc", "")

    geo = GeoFilter()
    geo_out = geo._run(
        alerts_json=json.dumps({"alerts": [alert]}),
        user_lat=user_lat, user_lon=user_lon, radius_km=5000
    )

    amp = CrisisSignalAmplifier()
    amp_out  = amp._run(
        alert_json=geo_out,
        accessibility_needs=None,
        user_context=f"location: {city}" if city else None
    )
    amp_data = json.loads(amp_out)

    fema      = FEMADisasterFetcher()
    fema_data = json.loads(fema._run(state=state, limit=5))

    # Agent fetches live, location-aware contacts
    contact_fetcher = LiveContactFetcher()
    contacts_data   = json.loads(contact_fetcher._run(
        state=state or "US",
        event_type=event,
        area_desc=area
    ))

    primary = (amp_data.get("amplified_alerts") or [{}])[0]
    nearby  = json.loads(geo_out).get("nearby_alerts", [{}])
    dist_km = nearby[0].get("distance_km") if nearby else None

    primary["_state"]    = state
    primary["_city"]     = city
    primary["_user_lat"] = user_lat
    primary["_user_lon"] = user_lon

    return {
        "alert":       alert,
        "primary":     primary,
        "fema":        fema_data.get("declarations", []),
        "distance_km": dist_km,
        "contacts":    contacts_data,   # from LiveContactFetcher
    }


# ── Panel renderers ──────────────────────────────────────────────────────

def render_what_to_do(result: dict):
    alert = result["alert"]
    p     = result["primary"]
    dist  = result.get("distance_km")
    sev   = alert.get("severity", "Unknown")
    color = SEVERITY_COLORS.get(sev, "#64748b")

    # Incident header
    st.markdown(
        f'<div style="border-left:3px solid {color};padding:8px 0 8px 14px;margin-bottom:1rem">'
        f'<div style="font-size:15px;font-weight:600;color:#e8eaf0">{alert.get("event","")}</div>'
        f'<div style="font-size:13px;color:#64748b;margin-top:2px">{alert.get("areaDesc","")}'
        f'{"&nbsp;·&nbsp;" + str(round(dist)) + " km away" if dist else ""}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # Score row
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown(f'<div class="metric-card"><h3 style="color:{color}">'
                    f'{p.get("priority_score","—")}</h3><p>Priority</p></div>',
                    unsafe_allow_html=True)
    with col_b:
        conf = p.get("confidence_score", 0)
        st.markdown(f'<div class="metric-card"><h3 style="color:#e8eaf0">'
                    f'{conf:.0%}</h3><p>Confidence</p></div>',
                    unsafe_allow_html=True)
    with col_c:
        st.markdown(f'<div class="metric-card"><h3 style="color:{color};font-size:1rem !important">'
                    f'{sev}</h3><p>Severity</p></div>',
                    unsafe_allow_html=True)

    # Time sensitivity banner
    ts = p.get("time_sensitivity", "")
    if ts:
        st.markdown(
            f'<div style="background:#0b0f17;border:1px solid #1c2333;border-left:3px solid {color};'
            f'border-radius:0 6px 6px 0;padding:10px 14px;margin:1rem 0;'
            f'font-size:13px;color:#94a3b8;font-style:italic">{ts}</div>',
            unsafe_allow_html=True
        )

    # Immediate actions
    actions = p.get("immediate_actions", [])
    if actions:
        st.markdown(section_lbl("Immediate Actions"), unsafe_allow_html=True)
        for i, step in enumerate(actions, 1):
            st.markdown(
                f'<div style="display:flex;gap:12px;padding:9px 0;border-bottom:1px solid #21262d;'
                f'align-items:flex-start">'
                f'<span style="color:#6e7681;font-size:13px;font-family:monospace;'
                f'min-width:20px;padding-top:2px">{i:02d}</span>'
                f'<span style="font-size:14px;color:#cbd5e1;line-height:1.55">{step}</span>'
                f'</div>',
                unsafe_allow_html=True
            )

    # Nearest shelters
    shelters = p.get("nearest_shelters", [])
    if shelters:
        st.markdown(section_lbl("Nearest Shelters"), unsafe_allow_html=True)
        for sh in shelters:
            acc = ('<span style="font-size:13px;color:#3b82f6;border:1px solid #3b82f630;'
                   'background:#3b82f610;padding:1px 7px;border-radius:3px;margin-left:6px">'
                   'Accessible</span>' if sh.get("accessible") else "")
            services = " · ".join(sh.get("services", []))
            st.markdown(
                f'<div style="padding:9px 0;border-bottom:1px solid #21262d">'
                f'<div style="font-size:14px;color:#e8eaf0;font-weight:500">{sh["name"]}{acc}</div>'
                f'<div style="font-size:13px;color:#64748b;margin-top:3px">{sh.get("address","")}</div>'
                f'<div style="font-size:13px;color:#6e7681;margin-top:4px;font-family:monospace">'
                f'Capacity: {sh.get("capacity",0):,}&nbsp;·&nbsp;{services}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

    # Plain language summary
    summary = p.get("plain_language_summary", "")
    if summary:
        st.markdown(
            f'<div style="background:#0b0f17;border:1px solid #1c2333;border-radius:6px;'
            f'padding:12px 14px;margin-top:1.2rem;font-size:13px;color:#94a3b8;line-height:1.6">'
            f'{summary}</div>',
            unsafe_allow_html=True
        )


def render_contact_help(result: dict):
    alert    = result["alert"]
    fema     = result["fema"]
    contacts = result.get("contacts", {}).get("contacts", {})
    sev      = alert.get("severity", "Unknown")
    color    = SEVERITY_COLORS.get(sev, "#64748b")
    state    = alert.get("state", "")
    event    = alert.get("event", "")

    # Incident header
    st.markdown(
        f'<div style="border-left:3px solid {color};padding:8px 0 8px 14px;margin-bottom:1.2rem">'
        f'<div style="font-size:15px;font-weight:600;color:#e8eaf0">{event}</div>'
        f'<div style="font-size:13px;color:#8b949e;margin-top:2px">{alert.get("areaDesc","")}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    def contact_row(name, number, desc, highlight=False):
        border = f"border-left:3px solid {color};" if highlight else ""
        num_color = color if highlight else "#8b949e"
        return (
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'padding:11px 14px;background:#161b22;border:1px solid #21262d;{border}'
            f'border-radius:6px;margin-bottom:6px">'
            f'<div style="flex:1;min-width:0">'
            f'<div style="font-size:14px;color:#e6edf3;font-weight:500">{name}</div>'
            f'<div style="font-size:13px;color:#8b949e;margin-top:2px">{desc}</div>'
            f'</div>'
            f'<span style="font-size:14px;color:{num_color};font-family:monospace;'
            f'font-weight:600;margin-left:12px;white-space:nowrap">{number}</span>'
            f'</div>'
        )

    def render_contact(key, highlight=False):
        c = contacts.get(key)
        if c and isinstance(c, dict):
            st.markdown(contact_row(c["name"], c["number"], c["desc"], highlight),
                        unsafe_allow_html=True)

    # ── 1. Immediate ─────────────────────────────────────────────────────
    st.markdown(section_lbl("Immediate Emergency"), unsafe_allow_html=True)
    render_contact("emergency_911", highlight=True)

    # ── 2. Local — state EMA + NWS + 211 ─────────────────────────────────
    st.markdown(section_lbl(f"{state} Local Resources" if state else "Local Resources"),
                unsafe_allow_html=True)
    render_contact("state_ema")
    render_contact("nws_local")
    render_contact("211")

    # ── 3. Incident-specific ─────────────────────────────────────────────
    incident_rows = contacts.get("incident_specific", [])
    if incident_rows:
        st.markdown(section_lbl(f"{event.split()[0]} Specific Hotlines"), unsafe_allow_html=True)
        for c in incident_rows:
            st.markdown(contact_row(c["name"], c["number"], c["desc"]), unsafe_allow_html=True)

    # ── 4. National ───────────────────────────────────────────────────────
    st.markdown(section_lbl("National Resources"), unsafe_allow_html=True)
    render_contact("fema")
    render_contact("red_cross")
    render_contact("crisis_text")

    # ── 5. Accessibility ──────────────────────────────────────────────────
    st.markdown(section_lbl("Accessibility & Special Needs"), unsafe_allow_html=True)
    render_contact("accessibility")
    st.markdown(
        contact_row("211 Access & Functional Needs", "Dial 211",
                    "Request accessible transport, medical equipment, or shelter"),
        unsafe_allow_html=True
    )

    # ── 6. FEMA history ───────────────────────────────────────────────────
    if fema:
        st.markdown(section_lbl(f"Past Disasters — {state or 'This Region'}"),
                    unsafe_allow_html=True)
        for d in fema[:3]:
            aid = d.get("totalObligatedAmountHmgp", 0)
            aid_str = f"${aid/1e6:.0f}M aid" if aid and aid > 0 else ""
            st.markdown(
                f'<div style="padding:9px 0;border-bottom:1px solid #21262d">'
                f'<div style="font-size:14px;color:#c9d1d9">{d.get("declarationTitle","")}</div>'
                f'<div style="font-size:13px;color:#8b949e;margin-top:3px;font-family:monospace">'
                f'{d.get("declarationDate","")[:10]}'
                f'&nbsp;·&nbsp;{d.get("incidentType","")}'
                f'{"&nbsp;·&nbsp;" + aid_str if aid_str else ""}'
                f'</div></div>',
                unsafe_allow_html=True
            )

# ── Main render ──────────────────────────────────────────────────────────

def render_live_feed(state_filter, severity_filter, user_loc=None, mistral_key=""):
    with st.spinner("Fetching alerts..."):
        alerts = get_alerts(state_filter, severity_filter)

    if not alerts:
        st.info("No active alerts matching current filters.")
        return

    # Metric row
    from collections import Counter
    sev_counts = Counter(a.get("severity", "Unknown") for a in alerts)
    cols = st.columns(5)
    for col, (label, sev) in zip(cols, [
        ("Total", None), ("Extreme", "Extreme"), ("Severe", "Severe"),
        ("Moderate", "Moderate"), ("Minor", "Minor")
    ]):
        with col:
            count = len(alerts) if sev is None else sev_counts.get(sev, 0)
            color = SEVERITY_COLORS.get(sev, "#c9545f") if sev else "#c9545f"
            st.markdown(
                f'<div class="metric-card"><h3 style="color:{color}">{count}</h3>'
                f'<p>{label}</p></div>',
                unsafe_allow_html=True
            )

    st.markdown("<div style='margin:1.2rem 0'></div>", unsafe_allow_html=True)

    # Map + detail panel
    col_map, col_detail = st.columns([3, 2], gap="large")

    with col_map:
        # Center map
        if user_loc and user_loc.get("source") != "default":
            center, zoom = [user_loc["lat"], user_loc["lon"]], 7
        elif state_filter != "All States":
            from tabs.historical import STATE_COORDS
            center = list(STATE_COORDS.get(state_filter, (39.5, -98.35)))
            zoom = 6
        else:
            center, zoom = [39.5, -98.35], 4

        m = folium.Map(location=center, zoom_start=zoom,
                       tiles="CartoDB dark_matter", prefer_canvas=True)

        # User marker
        if user_loc and user_loc.get("source") != "default":
            folium.CircleMarker(
                location=[user_loc["lat"], user_loc["lon"]],
                radius=7, color="#3b82f6", fill=True,
                fill_color="#3b82f6", fill_opacity=1.0, weight=2,
                tooltip="Your location"
            ).add_to(m)
            folium.CircleMarker(
                location=[user_loc["lat"], user_loc["lon"]],
                radius=16, color="#3b82f6", fill=False, weight=1, opacity=0.3
            ).add_to(m)

        # Alert markers
        for idx, alert in enumerate(alerts):
            lat  = alert.get("lat", 39.5)
            lon  = alert.get("lon", -98.35)
            sev  = alert.get("severity", "Unknown")
            color = SEVERITY_COLORS.get(sev, "#64748b")
            radius = {"Extreme": 16, "Severe": 13, "Moderate": 10, "Minor": 7}.get(sev, 8)
            tooltip_str = f"{sev.upper()} · {alert.get('event','')} · {alert.get('areaDesc','')[:40]}"

            popup_html = (
                f'<div style="font-family:monospace;font-size:13px;min-width:190px;'
                f'background:#0d1117;padding:12px;border-radius:5px;color:#e8eaf0">'
                f'<div style="color:{color};font-weight:700;margin-bottom:4px;letter-spacing:0.05em">'
                f'{sev.upper()}</div>'
                f'<div style="font-size:13px;font-weight:600;margin-bottom:5px">{alert.get("event","")}</div>'
                f'<div style="color:#64748b;font-size:13px;margin-bottom:8px">{alert.get("areaDesc","")}</div>'
                f'<div style="color:#94a3b8;font-size:13px">'
                f'{alert.get("urgency","")} &nbsp;·&nbsp; {alert.get("certainty","")}</div>'
                f'</div>'
            )

            folium.CircleMarker(
                location=[lat, lon],
                radius=radius, color=color, fill=True,
                fill_color=color, fill_opacity=0.82, weight=1.5,
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=tooltip_str
            ).add_to(m)

            if sev == "Extreme":
                folium.CircleMarker(
                    location=[lat, lon], radius=radius + 8,
                    color=color, fill=False, weight=1, opacity=0.3
                ).add_to(m)

        # Legend
        m.get_root().html.add_child(folium.Element(
            '<div style="position:fixed;bottom:16px;left:14px;background:rgba(8,12,18,0.95);'
            'padding:10px 14px;border-radius:5px;border:1px solid #1c2333;'
            'font-size:13px;color:#64748b;z-index:9999;line-height:2;font-family:monospace">'
            '<div style="color:#94a3b8;font-weight:600;margin-bottom:3px;letter-spacing:0.06em">SEVERITY</div>'
            '<span style="color:#ef4444">&#9679;</span> EXTREME &nbsp;'
            '<span style="color:#f97316">&#9679;</span> SEVERE<br>'
            '<span style="color:#eab308">&#9679;</span> MODERATE &nbsp;'
            '<span style="color:#22c55e">&#9679;</span> MINOR'
            '</div>'
        ))

        st.caption("Click a marker to select an incident.")

        map_data = st_folium(
            m, width=None, height=480,
            returned_objects=["last_object_clicked"],
            key="live_map"
        )

        # Match click to nearest alert by lat/lon proximity
        clicked_obj = (map_data or {}).get("last_object_clicked") or {}
        click_lat = clicked_obj.get("lat")
        click_lng = clicked_obj.get("lng")

        if click_lat and click_lng:
            # Skip if clicked the user location marker
            user_lat = (user_loc or {}).get("lat")
            user_lon = (user_loc or {}).get("lon")
            is_user_marker = (user_lat and abs(click_lat - user_lat) < 0.001
                              and abs(click_lng - user_lon) < 0.001)

            if not is_user_marker:
                # Find closest alert to the clicked point
                best_idx, best_dist = None, float("inf")
                for idx, alert in enumerate(alerts):
                    alat = alert.get("lat", 39.5)
                    alon = alert.get("lon", -98.35)
                    dist = (click_lat - alat) ** 2 + (click_lng - alon) ** 2
                    if dist < best_dist:
                        best_dist = dist
                        best_idx = idx

                if best_idx is not None and best_dist < 1.0:  # within ~100km
                    if st.session_state.get("selected_idx") != best_idx:
                        st.session_state["selected_idx"] = best_idx
                        st.session_state.pop("incident_result", None)
                        st.session_state.pop("active_panel", None)
                        st.rerun()

    # ── Right panel ──────────────────────────────────────────────────────
    with col_detail:
        selected_idx = st.session_state.get("selected_idx")

        if selected_idx is None:
            # Empty state
            st.markdown(
                '<div style="border:1px dashed #1c2333;border-radius:8px;'
                'padding:3rem 1.5rem;text-align:center;margin-top:0.5rem">'
                '<div style="font-size:13px;color:#6e7681;letter-spacing:0.08em;'
                'text-transform:uppercase;margin-bottom:0.6rem">No incident selected</div>'
                '<div style="font-size:14px;color:#6e7681;line-height:1.6">'
                'Click any alert marker<br>on the map to get started</div>'
                '</div>',
                unsafe_allow_html=True
            )
        else:
            selected_alert = alerts[selected_idx]
            sev   = selected_alert.get("severity", "Unknown")
            color = SEVERITY_COLORS.get(sev, "#64748b")

            # Alert title + pill
            st.markdown(
                f'<div style="border-left:3px solid {color};padding:8px 0 8px 14px;margin-bottom:0.8rem">'
                f'<div style="font-size:15px;font-weight:600;color:#e8eaf0">'
                f'{selected_alert.get("event","")}</div>'
                f'<div style="font-size:13px;color:#8b949e;margin-top:3px">'
                f'{selected_alert.get("areaDesc","")}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
            st.markdown(sev_pill(sev), unsafe_allow_html=True)

            # ── Instant summary — no tool run needed ──────────────────────
            urgency   = selected_alert.get("urgency", "")
            certainty = selected_alert.get("certainty", "")
            headline  = selected_alert.get("headline") or selected_alert.get("description", "")
            headline  = headline[:180].rstrip() + ("..." if len(headline) > 180 else "")

            # Quick next-step lookup by event keyword
            EVENT_QUICK = {
                "Tornado":      "Move to the lowest interior room immediately. Stay away from windows.",
                "Hurricane":    "Prepare to evacuate if ordered. Secure your home and go-bag now.",
                "Flood":        "Move to higher ground. Do not drive through flooded roads.",
                "Winter Storm": "Stay indoors. Stock food, water, and medications for 72 hours.",
                "Heat":         "Stay in air-conditioned spaces. Drink water every 20 minutes.",
                "Fire":         "Follow evacuation orders immediately. Do not wait.",
                "Earthquake":   "Drop, cover, hold on. Stay away from windows and heavy objects.",
                "Tsunami":      "Move inland and to higher ground immediately.",
                "Thunderstorm": "Stay indoors. Avoid plumbing and electrical equipment.",
                "Wind":         "Secure loose objects outside. Avoid trees and power lines.",
                "Fog":          "Avoid driving if possible. Use low-beam headlights.",
            }
            event_text = selected_alert.get("event", "")
            quick_step = next(
                (v for k, v in EVENT_QUICK.items() if k.lower() in event_text.lower()),
                "Monitor official broadcasts and follow local emergency management instructions."
            )

            urgency_color = {"Immediate": "#ef4444", "Expected": "#f97316",
                             "Future": "#eab308", "Past": "#6e7681"}.get(urgency, "#6e7681")

            st.markdown(
                f'<div style="background:#161b22;border:1px solid #21262d;border-radius:8px;'
                f'padding:14px 16px;margin:1rem 0">'

                # Urgency + certainty row
                f'<div style="display:flex;gap:8px;margin-bottom:10px">'
                f'<span style="font-size:12px;font-weight:600;color:{urgency_color};'
                f'background:{urgency_color}18;border:1px solid {urgency_color}30;'
                f'padding:2px 8px;border-radius:3px;letter-spacing:0.05em">{urgency.upper()}</span>'
                f'<span style="font-size:12px;color:#6e7681;background:#21262d;'
                f'padding:2px 8px;border-radius:3px">{certainty}</span>'
                f'</div>'

                # Headline / description
                f'<div style="font-size:14px;color:#c9d1d9;line-height:1.6;margin-bottom:10px">'
                f'{headline}</div>'

                # Quick next step
                f'<div style="border-top:1px solid #21262d;padding-top:10px;margin-top:2px">'
                f'<span style="font-size:11px;font-weight:600;letter-spacing:0.08em;'
                f'text-transform:uppercase;color:#6e7681">Next step &nbsp;</span>'
                f'<span style="font-size:14px;color:#e6edf3;font-weight:500">{quick_step}</span>'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True
            )

            # ── Action buttons ────────────────────────────────────────────
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                what_clicked = st.button(
                    "What to Do",
                    key="btn_what",
                    type="primary",
                    use_container_width=True
                )
            with btn_col2:
                contact_clicked = st.button(
                    "Contact Help",
                    key="btn_contact",
                    use_container_width=True
                )

            # Trigger tool run on button click
            if what_clicked:
                st.session_state["active_panel"] = "what"
                st.session_state.pop("incident_result", None)
            if contact_clicked:
                st.session_state["active_panel"] = "contact"
                st.session_state.pop("incident_result", None)

            # Run tools if panel selected but result not yet cached
            active_panel = st.session_state.get("active_panel")
            result       = st.session_state.get("incident_result")

            # Invalidate cache if alert changed
            if result and result.get("alert", {}).get("id") != selected_alert.get("id"):
                result = None
                st.session_state.pop("incident_result", None)

            if active_panel and result is None:
                with st.spinner("Running agents..."):
                    result = run_tools(selected_alert, user_loc or {})
                    st.session_state["incident_result"] = result

            # Render the appropriate panel
            if active_panel == "what" and result:
                st.markdown("<div style='margin:0.6rem 0'></div>", unsafe_allow_html=True)
                render_what_to_do(result)

            elif active_panel == "contact" and result:
                st.markdown("<div style='margin:0.6rem 0'></div>", unsafe_allow_html=True)
                render_contact_help(result)

    # ── Alert list — read-only info cards, map click selects ─────────────
    st.markdown("---")
    st.markdown(
        '<p style="font-size:13px;font-weight:600;letter-spacing:0.1em;'
        'text-transform:uppercase;color:#6e7681;margin-bottom:0.8rem">All Active Alerts</p>',
        unsafe_allow_html=True
    )

    for idx, alert in enumerate(alerts):
        sev         = alert.get("severity", "Unknown")
        color       = SEVERITY_COLORS.get(sev, "#64748b")
        is_selected = st.session_state.get("selected_idx") == idx
        label       = f"{sev.upper()} — {alert.get('event','')}  ·  {alert.get('areaDesc','')[:50]}"

        with st.expander(label, expanded=is_selected):
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f"**Urgency**  \n{alert.get('urgency','—')}")
            with c2:
                st.markdown(f"**Certainty**  \n{alert.get('certainty','—')}")
            with c3:
                issued = str(alert.get("sent",""))[:16].replace("T"," ")
                st.markdown(f"**Issued**  \n{issued}")

            desc = alert.get("description") or alert.get("headline","")
            if desc:
                st.markdown(f"_{desc[:220]}{'...' if len(desc) > 220 else ''}_")
