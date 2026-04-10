"""Tab 3: Agent Processing — hierarchical CrewAI workflow with structured JSON output."""

import streamlit as st
import json
import time
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


AGENT_DESCRIPTIONS = {
 "Emergency Response Controller": ("", "Orchestrates all agents, delegates tasks, handles failures"),
 "Alert Aggregator":    ("", "Fetches NOAA + FEMA data via federal APIs"),
 "Weather & Hazard Analyst":  ("", "Analyzes severity, geography, compound risks"),
 "Shelter Coordinator":   ("", "Identifies accessible shelters with services"),
 "Evacuation Route Planner":  ("", "Plans safe evacuation routes and transport"),
 "Emergency Contact Liaison":  ("", "Compiles 911, FEMA, 211, accessibility contacts"),
 "Guidance Generator":   ("", "Synthesizes plain-language accessible guidance"),
}

TASK_STEPS = [
 (" Fetching NOAA + FEMA data...",   "Alert Aggregator",   2.0),
 (" Applying geo-filter to alerts...",  "Weather & Hazard Analyst", 1.5),
 (" Identifying shelters...",    "Shelter Coordinator",  1.5),
 (" Planning evacuation routes...",   "Evacuation Route Planner", 1.5),
 (" Compiling emergency contacts...",  "Emergency Contact Liaison", 1.0),
 (" Generating accessibility guidance...", "Guidance Generator",  2.0),
]


def simulate_agent_run(state, user_lat, user_lon, accessibility_needs, user_context):
 """Run agents with real tools, no LLM needed for demo mode."""
 from tools.crisis_tools import (NOAAAlertFetcher, FEMADisasterFetcher,
          GeoFilter, CrisisSignalAmplifier, ReportFormatter,
          MOCK_NOAA_ALERTS)
 results = {}

 # Step 1: Fetch NOAA
 noaa = NOAAAlertFetcher()
 raw_noaa = noaa._run(state=state if state != "All States" else None)
 noaa_data = json.loads(raw_noaa)
 results["noaa"] = noaa_data

 # Step 2: FEMA
 fema = FEMADisasterFetcher()
 raw_fema = fema._run(state=state if state != "All States" else None, limit=5)
 fema_data = json.loads(raw_fema)
 results["fema"] = fema_data

 # Step 3: Geo filter
 geo = GeoFilter()
 raw_geo = geo._run(alerts_json=raw_noaa, user_lat=user_lat, user_lon=user_lon, radius_km=500)
 geo_data = json.loads(raw_geo)
 results["geo"] = geo_data

 # Step 4: Amplify
 amp = CrisisSignalAmplifier()
 raw_amp = amp._run(
  alert_json=json.dumps(geo_data.get("nearby_alerts", MOCK_NOAA_ALERTS[:3])),
  accessibility_needs=accessibility_needs or None,
  user_context=user_context or None
 )
 amp_data = json.loads(raw_amp)
 results["amplified"] = amp_data

 # Step 5: Format report
 fmt = ReportFormatter()
 raw_report = fmt._run(amplified_json=raw_amp, format_type="structured")
 try:
  report = json.loads(raw_report)
 except:
  report = {"report": raw_report}
 results["report"] = report

 return results


def render_agent_processing(mistral_key, user_loc=None):
 st.markdown("## Agent Processing Workflow")
 st.markdown("Hierarchical CrewAI workflow: Controller → 6 Specialized Agents")

 # Agent roster
 with st.expander("Agent Roster", expanded=False):
  cols = st.columns(2)
  for i, (name, (icon, desc)) in enumerate(AGENT_DESCRIPTIONS.items()):
   with cols[i % 2]:
    is_controller = name == "Emergency Response Controller"
    border = "#e94560" if is_controller else "#0f3460"
    st.markdown(
     f'<div style="border:1px solid {border};border-radius:8px;padding:10px;margin:4px 0">'
     f'<b>{icon} {name}</b><br><small style="color:#a8b2d8">{desc}</small></div>',
     unsafe_allow_html=True
    )

 st.markdown("---")

 # Configuration
 default_lat = user_loc["lat"] if user_loc and user_loc.get("source") != "default" else 32.77
 default_lon = user_loc["lon"] if user_loc and user_loc.get("source") != "default" else -96.79
 default_state_raw = user_loc.get("state", "TX") if user_loc else "TX"
 state_options = ["TX", "FL", "CA", "NY", "LA", "WA", "OR", "NC", "GA", "AL", "IL", "MA", "AZ", "CO", "GA"]
 default_state = default_state_raw if default_state_raw in state_options else "TX"

 with st.form("agent_config"):
  st.markdown("### Run Configuration")
  if user_loc and user_loc.get("source") != "default":
      st.caption(f"Using your location: {user_loc.get('display','')}")
  col1, col2 = st.columns(2)
  with col1:
   state = st.selectbox("Target State", state_options,
                        index=state_options.index(default_state))
   user_lat = st.number_input("User Latitude", value=default_lat, format="%.4f")
   user_lon = st.number_input("User Longitude", value=default_lon, format="%.4f")
  with col2:
   accessibility_needs = st.multiselect(
    "Accessibility Needs",
    ["mobility", "visual", "hearing", "cognitive", "medical"],
    help="Select all that apply for tailored guidance"
   )
   user_context = st.text_input("User Context", placeholder="e.g. 'has car, elderly, with pets'")
   run_mode = st.radio("Run Mode", ["Demo (no LLM key needed)", "Full CrewAI (Mistral required)"], index=0)

  submitted = st.form_submit_button("Run Agent Workflow", type="primary")

 if submitted:
  needs_str = ",".join(accessibility_needs) if accessibility_needs else ""

  if run_mode == "Full CrewAI (Mistral required)" and not mistral_key:
   st.error("Mistral API key required for full CrewAI mode. Enter it in the sidebar or use Demo mode.")
   return

  # Workflow progress display
  st.markdown("---")
  st.markdown("### Workflow Execution")

  progress_bar = st.progress(0)
  status_container = st.empty()
  log_container = st.empty()
  logs = []

  def log(msg):
   logs.append(msg)
   log_container.markdown(
    '<div style="background:#0f3460;padding:10px;border-radius:6px;'
    'font-family:monospace;font-size:12px;max-height:200px;overflow-y:auto">' +
    "<br>".join(logs[-12:]) + '</div>',
    unsafe_allow_html=True
   )

  log(" Controller Agent: Initializing hierarchical workflow...")
  log(f" Target: {state} | Coords: ({user_lat:.2f}, {user_lon:.2f})")
  if needs_str:
   log(f" Accessibility needs: {needs_str}")

  results = None

  if run_mode == "Demo (no LLM key needed)":
   for i, (step_msg, agent_name, delay) in enumerate(TASK_STEPS):
    progress_bar.progress((i + 1) / len(TASK_STEPS))
    status_container.markdown(
     f'<div style="background:#16213e;padding:8px 12px;border-left:3px solid #e94560;'
     f'border-radius:4px;margin:4px 0"><b>{step_msg}</b> → {agent_name}</div>',
     unsafe_allow_html=True
    )
    log(f"→ {agent_name}: {step_msg}")
    time.sleep(delay * 0.5) # Speed up for demo

   with st.spinner("Running tool pipeline..."):
    results = simulate_agent_run(state, user_lat, user_lon, needs_str, user_context)
   log(" All agents completed successfully.")

  else:
   try:
    from agents.crew import build_crew
    log(" Building CrewAI crew with Mistral LLM...")

    for i, (step_msg, agent_name, _) in enumerate(TASK_STEPS):
     progress_bar.progress((i + 1) / len(TASK_STEPS))
     status_container.markdown(f"**{step_msg}**")
     log(f"→ {agent_name}: {step_msg}")

    with st.spinner("Running full hierarchical CrewAI workflow... (this may take 1-2 min)"):
     crew = build_crew(
      mistral_api_key=mistral_key,
      state=state,
      user_lat=user_lat,
      user_lon=user_lon,
      accessibility_needs=needs_str,
      user_context=user_context
     )
     crew_result = crew.kickoff()
     results = {"crew_output": str(crew_result)}
    log(" CrewAI workflow completed.")
   except Exception as e:
    st.error(f"CrewAI error: {e}")
    log(f" Error: {e}")
    log(" Falling back to demo mode...")
    results = simulate_agent_run(state, user_lat, user_lon, needs_str, user_context)

  progress_bar.progress(1.0)
  status_container.success(" Workflow complete!")

  # Store results in session state for Safety Chat
  st.session_state["last_run_results"] = results
  st.session_state["last_run_state"] = state

  # Results display
  st.markdown("---")
  st.markdown("### Agent Output")

  if "amplified" in results:
   amp = results["amplified"]
   alerts_out = amp.get("amplified_alerts", [])

   if alerts_out:
    st.markdown("#### Priority-Scored Action Guidance")
    for alert in alerts_out:
     priority = alert.get("priority_score", 0)
     confidence = alert.get("confidence_score", 0)
     sev = alert.get("severity", "Unknown")
     color = {"Extreme": "#ff1744", "Severe": "#ff6d00",
        "Moderate": "#ffd600", "Minor": "#00e676"}.get(sev, "#9e9e9e")

     with st.expander(
      f"[{priority}/100] {alert.get('event_type','')} — {alert.get('area','')[:40]}"
     ):
      c1, c2, c3 = st.columns(3)
      with c1:
       st.metric("Priority Score", f"{priority}/100")
      with c2:
       st.metric("Confidence", f"{confidence:.0%}")
      with c3:
       st.markdown(f"**Severity:**<span style='color:{color}'>{sev}</span>", unsafe_allow_html=True)

      st.markdown(f"**{alert.get('time_sensitivity','')}**")
      st.markdown("**Immediate Actions:**")
      for j, step in enumerate(alert.get("immediate_actions", []), 1):
       st.markdown(f"{j}. {step}")

      if alert.get("accessibility_adaptations") and alert["accessibility_adaptations"] != ["No specific accessibility adaptations required"]:
       st.markdown("**Accessibility Adaptations:**")
       for ad in alert["accessibility_adaptations"]:
        st.markdown(f"• {ad}")

      if alert.get("context_notes"):
       st.markdown("**Context Notes:**")
       for note in alert["context_notes"]:
        st.markdown(f"• {note}")

      shelters = alert.get("nearest_shelters", [])
      if shelters:
       st.markdown("**Nearest Shelters:**")
       for sh in shelters:
        acc = " Accessible" if sh.get("accessible") else ""
        services = ", ".join(sh.get("services", []))
        st.markdown(f"• **{sh['name']}**{acc} — Capacity: {sh.get('capacity',0):,} — Services: {services}")

  # Raw JSON output
  with st.expander("Raw JSON Output"):
   st.json(results)
