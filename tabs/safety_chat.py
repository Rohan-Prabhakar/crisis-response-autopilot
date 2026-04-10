"""Tab 3: Safety Chat — context-aware chat using location, active area alerts, and selected incident."""

import streamlit as st
import requests
import json
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"

BASE_SYSTEM_PROMPT = """You are the emergency preparedness assistant built into Crisis Response Autopilot — a real-time emergency intelligence platform. You have direct access to live NOAA weather alerts, FEMA data, local emergency contacts, and shelter information for the user's location.

Your role is to be the complete solution. You help users:
- Understand exactly what active alerts mean for their specific location
- Know precisely what actions to take right now
- Find shelters, evacuation routes, and local emergency contacts
- Prepare emergency kits and family communication plans
- Navigate emergencies with accessibility needs

CRITICAL RULES — never break these:
1. NEVER recommend external apps (FEMA App, Weather.gov app, local alert apps, Citizen app, etc.)
2. NEVER tell users to "sign up" for any external alert system or service
3. NEVER direct users away from this platform to get information
4. ALL the information they need is available here — live alerts, contacts, shelters, guidance
5. If no alerts are active, say so clearly and reassuringly — this is the system working correctly
6. Keep responses focused and actionable — no filler, no generic disclaimers

When there are no active alerts: confirm clearly that their area is all clear right now, and optionally offer to help them prepare for future events. Do not suggest they go elsewhere to verify.

Tone: calm, direct, confident. You are the trusted source — act like it.
If someone describes an active life-threatening emergency, tell them to call 911 before anything else."""

QUICK_PROMPTS = [
    "What should I do right now?",
    "What goes in an emergency go-bag?",
    "How do I shelter in place?",
    "Evacuation checklist",
    "Preparing with limited mobility",
    "Emergency plan for my family",
]


def build_context() -> tuple[str, list[dict]]:
    """
    Returns (context_string, context_badges, has_alerts, loc_set).
    Sources: active area alerts + user location only.
    Selected incident is intentionally excluded — that's for the action panel.
    """
    parts  = []
    badges = []

    # ── 2. Active alerts in user's area ──────────────────────────────────
    user_loc = st.session_state.get("user_location", {})
    state    = user_loc.get("state", "")
    loc_name = user_loc.get("display", state or "your area")
    loc_set  = user_loc.get("source") != "default"

    # Use cached alerts from session if available, else fetch
    cached_alerts = st.session_state.get("area_alerts_cache", {})
    if cached_alerts.get("state") == state and "alerts" in cached_alerts:
        area_alerts = cached_alerts["alerts"]
    else:
        try:
            from tools.crisis_tools import NOAAAlertFetcher
            fetcher = NOAAAlertFetcher()
            raw     = fetcher._run(state=state if state and state != "All States" else None)
            area_alerts = json.loads(raw).get("alerts", [])[:8]
            st.session_state["area_alerts_cache"] = {"state": state, "alerts": area_alerts}
        except Exception:
            area_alerts = []

    if area_alerts:
        sev_order = {"Extreme": 0, "Severe": 1, "Moderate": 2, "Minor": 3}
        area_alerts_sorted = sorted(area_alerts, key=lambda a: sev_order.get(a.get("severity",""), 4))
        alert_lines = [
            f"- {a.get('event','')} ({a.get('severity','')}) in {a.get('areaDesc','')} [Urgency: {a.get('urgency','')}]"
            for a in area_alerts_sorted[:5]
        ]
        parts.append(
            f"ACTIVE ALERTS IN {loc_name.upper()}:\n" + "\n".join(alert_lines) + "\n"
            f"Reference these when the user asks what's happening nearby or what they should prepare for."
        )
        extreme_count = sum(1 for a in area_alerts if a.get("severity") == "Extreme")
        severe_count  = sum(1 for a in area_alerts if a.get("severity") == "Severe")
        badge_color   = "#ef4444" if extreme_count else "#f97316" if severe_count else "#3b82f6"
        badges.append({
            "label": f"{len(area_alerts)} active alert{'s' if len(area_alerts) != 1 else ''} nearby",
            "detail": loc_name,
            "color": badge_color
        })
    elif loc_set:
        # Location known but no alerts — explicitly tell the model so it can say all clear
        parts.append(
            f"NO ACTIVE ALERTS for {loc_name.upper()} at this time. "
            f"When the user asks about current conditions, respond with: there are no active weather "
            f"alerts for their area right now, their area is clear, and no immediate action is required. "
            f"Do NOT suggest they download any app, sign up for any service, or visit any external website. "
            f"This platform already monitors their alerts in real time. "
            f"You may offer to help them prepare for future events if they wish."
        )
        badges.append({
            "label": "All clear",
            "detail": loc_name,
            "color": "#3fb950"
        })

    # ── 3. Location context ───────────────────────────────────────────────
    if loc_set:
        state_str = user_loc.get("state", "")
        parts.append(
            f"USER LOCATION: {loc_name}"
            f"{(' (state: ' + state_str + ')') if state_str else ''}. "
            f"Tailor shelter, evacuation route, and resource recommendations to this location."
        )
        if not area_alerts:  # don't double-badge when alerts badge already shows location
            badges.append({"label": "Location", "detail": loc_name, "color": "#3b82f6"})

    context_str = "\n\n".join(parts) if parts else ""
    return context_str, badges, bool(area_alerts), loc_set


def call_mistral(messages: list, api_key: str) -> str:
    try:
        resp = requests.post(
            MISTRAL_API_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": "mistral-small-latest", "messages": messages,
                  "temperature": 0.25, "max_tokens": 800},
            timeout=30
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        return f"API error {resp.status_code} — check your Mistral key in app.py."
    except Exception as e:
        return f"Connection error: {e}"


def _send_message(user_message: str, mistral_key: str, context: str):
    st.session_state["chat_messages"].append({"role": "user", "content": user_message})

    if not mistral_key or mistral_key == "YOUR_MISTRAL_API_KEY_HERE":
        st.session_state["chat_messages"].append({
            "role": "assistant",
            "content": "No API key configured. Edit MISTRAL_API_KEY in app.py to enable AI responses.\n\n"
                       "In any active emergency: call **911**. FEMA: 1-800-621-3362. Crisis text: 741741."
        })
        return

    system = BASE_SYSTEM_PROMPT
    if context:
        system += f"\n\n--- CURRENT CONTEXT ---\n{context}\n-----------------------\n" \
                  f"Use the above context to give location-specific, situation-aware answers. " \
                  f"If the user asks 'what should I do' or 'what's happening near me', " \
                  f"draw directly from this context."

    history      = st.session_state["chat_messages"][-12:]
    api_messages = [{"role": "system", "content": system}] + history
    response     = call_mistral(api_messages, mistral_key)
    st.session_state["chat_messages"].append({"role": "assistant", "content": response})


def render_safety_chat(mistral_key: str):

    context, badges, has_alerts, loc_set = build_context()

    # ── Status banner ─────────────────────────────────────────────────────
    if badges:
        badge_html = '<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:1.1rem">'
        for b in badges:
            c = b["color"]
            badge_html += (
                f'<div style="display:flex;align-items:center;gap:8px;padding:7px 13px;'
                f'background:#161b22;border:1px solid {c}30;border-left:3px solid {c};'
                f'border-radius:0 6px 6px 0">'
                f'<span style="font-size:12px;color:{c};font-weight:600;letter-spacing:0.06em;'
                f'text-transform:uppercase">{b["label"]}</span>'
                f'<span style="font-size:13px;color:#8b949e">{b["detail"]}</span>'
                f'</div>'
            )
        badge_html += '</div>'
        st.markdown(badge_html, unsafe_allow_html=True)
    else:
        st.markdown(
            '<div style="padding:9px 14px;background:#161b22;border:1px solid #21262d;'
            'border-radius:6px;margin-bottom:1rem;font-size:13px;color:#6e7681">'
            'Set your location in the sidebar for context-aware answers.</div>',
            unsafe_allow_html=True
        )

    # ── Quick prompts ─────────────────────────────────────────────────────
    st.markdown(
        '<p style="font-size:11px;font-weight:600;letter-spacing:0.1em;'
        'text-transform:uppercase;color:#6e7681;margin-bottom:0.5rem">Quick prompts</p>',
        unsafe_allow_html=True
    )
    cols = st.columns(3)
    for i, prompt in enumerate(QUICK_PROMPTS):
        with cols[i % 3]:
            if st.button(prompt, key=f"qp_{i}", use_container_width=True):
                st.session_state["_pending_prompt"] = prompt

    st.markdown("<div style='margin:0.8rem 0'></div>", unsafe_allow_html=True)

    # ── Chat history ──────────────────────────────────────────────────────
    if "chat_messages" not in st.session_state:
        st.session_state["chat_messages"] = []

    if not st.session_state["chat_messages"]:
        user_loc = st.session_state.get("user_location", {})
        loc_name = user_loc.get("display", "your area")

        if has_alerts:
            welcome = (f"There are active alerts near **{loc_name}**. "
                       "Ask me what they mean, what you should prepare, or how to stay safe.")
        elif loc_set:
            welcome = (f"**No active alerts for {loc_name} right now** — no immediate action required.\n\n"
                       "You can still ask me about emergency preparedness, go-bag checklists, "
                       "family communication plans, or what to do if conditions change.")
        else:
            welcome = ("Set your location in the sidebar and I'll check for active alerts near you.\n\n"
                       "You can also ask me anything about emergency preparedness.")

        with st.chat_message("assistant"):
            st.markdown(welcome)
    else:
        for msg in st.session_state["chat_messages"]:
            if msg["role"] == "user":
                with st.chat_message("user"):
                    st.markdown(
                        f'<div style="font-size:14px;color:#e8eaf0">{msg["content"]}</div>',
                        unsafe_allow_html=True
                    )
            else:
                with st.chat_message("assistant"):
                    # Use st.markdown so bold, lists, numbered steps all render correctly
                    st.markdown(msg["content"])

    # ── Pending quick prompt ──────────────────────────────────────────────
    if "_pending_prompt" in st.session_state:
        prompt = st.session_state.pop("_pending_prompt")
        _send_message(prompt, mistral_key, context)
        st.rerun()
    # ── Input ─────────────────────────────────────────────────────────────
    user_input = st.chat_input("Ask about your alerts, what to do, evacuation...")
    if user_input and user_input.strip():
        _send_message(user_input.strip(), mistral_key, context)
        st.rerun()

    if st.session_state.get("chat_messages"):
        st.markdown("<div style='margin-top:0.5rem'></div>", unsafe_allow_html=True)
        if st.button("Clear conversation", key="clear_chat"):
            st.session_state["chat_messages"] = []
            st.rerun()

    st.markdown(
        '<p style="font-size:13px;color:#6e7681;margin-top:1.5rem;text-align:center">'
        'Active emergency: call 911 &nbsp;·&nbsp; FEMA: 1-800-621-3362 &nbsp;·&nbsp; Crisis text: 741741</p>',
        unsafe_allow_html=True
    )
