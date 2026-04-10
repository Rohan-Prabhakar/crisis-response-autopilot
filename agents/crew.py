"""
CrewAI multi-agent crew for Crisis Response Autopilot.
Hierarchical workflow: Controller → 6 specialized agents.
"""

import os
import json
from crewai import Agent, Task, Crew, Process
from langchain_mistralai import ChatMistralAI
from tools.crisis_tools import (
    NOAAAlertFetcher, FEMADisasterFetcher,
    GeoFilter, CrisisSignalAmplifier, ReportFormatter
)


def build_llm(mistral_api_key: str):
    return ChatMistralAI(
        model="mistral-small-latest",
        mistral_api_key=mistral_api_key,
        temperature=0.1,
        max_tokens=2048
    )


def build_crew(mistral_api_key: str, state: str = "TX", user_lat: float = 32.77, user_lon: float = -96.79,
               accessibility_needs: str = "", user_context: str = ""):
    """Build and return the hierarchical CrewAI crew."""

    llm = build_llm(mistral_api_key)

    # Instantiate tools
    noaa_tool    = NOAAAlertFetcher()
    fema_tool    = FEMADisasterFetcher()
    geo_tool     = GeoFilter()
    amplifier    = CrisisSignalAmplifier()
    formatter    = ReportFormatter()

    # ── Agents ──────────────────────────────────────────────

    controller = Agent(
        role="Emergency Response Controller",
        goal=(
            "Orchestrate a complete emergency analysis workflow. Delegate tasks to specialized agents, "
            "ensure all data is gathered, filtered, analyzed, and synthesized into actionable guidance. "
            "Manage task dependencies and handle failures gracefully."
        ),
        backstory=(
            "You are a seasoned emergency management director with 20 years of experience coordinating "
            "multi-agency disaster response. You excel at rapid information triage and clear delegation. "
            "You ensure no critical alert is missed and every resident gets actionable guidance."
        ),
        llm=llm,
        tools=[noaa_tool, fema_tool],
        verbose=True,
        allow_delegation=True,
        memory=True
    )

    alert_aggregator = Agent(
        role="Alert Aggregator",
        goal=(
            f"Fetch all active emergency alerts from NOAA for state {state}. "
            "Retrieve relevant FEMA historical declarations. Return complete, structured alert data."
        ),
        backstory=(
            "You are a real-time data ingestion specialist who monitors federal emergency APIs 24/7. "
            "Your job is to pull the freshest alert data and ensure nothing is missing."
        ),
        llm=llm,
        tools=[noaa_tool, fema_tool],
        verbose=True,
        memory=True
    )

    weather_analyst = Agent(
        role="Weather & Hazard Analyst",
        goal=(
            "Analyze fetched weather alerts for severity patterns, geographic clusters, "
            "and compound hazard risks. Identify which alerts require immediate escalation."
        ),
        backstory=(
            "You are a meteorologist and hazard analyst who translates complex NWS data into "
            "clear risk assessments. You understand compound events and how they amplify danger."
        ),
        llm=llm,
        tools=[geo_tool],
        verbose=True,
        memory=True
    )

    shelter_coordinator = Agent(
        role="Shelter Coordinator",
        goal=(
            "Identify available emergency shelters relevant to active alerts. "
            "Prioritize accessible shelters and those with medical capabilities. "
            "Return structured shelter data with services and capacity."
        ),
        backstory=(
            "You coordinate emergency shelter logistics for FEMA and have deep knowledge of "
            "accessible shelter networks across all 50 states."
        ),
        llm=llm,
        tools=[amplifier],
        verbose=True,
        memory=True
    )

    route_planner = Agent(
        role="Evacuation Route Planner",
        goal=(
            "Provide evacuation guidance and route considerations for each active alert zone. "
            "Account for road closures common in the alert type, and special transport needs."
        ),
        backstory=(
            "You are a transportation emergency planner who has coordinated evacuations for "
            "major hurricanes and wildfires. You know which routes typically flood or close."
        ),
        llm=llm,
        tools=[geo_tool],
        verbose=True,
        memory=True
    )

    contact_liaison = Agent(
        role="Emergency Contact Liaison",
        goal=(
            "Compile and verify emergency contact information: local emergency management, "
            "211 services, crisis hotlines, and accessibility-specific resources."
        ),
        backstory=(
            "You maintain the national emergency contact database and ensure residents can "
            "reach help through multiple channels including TTY and SMS for accessibility."
        ),
        llm=llm,
        tools=[formatter],
        verbose=True,
        memory=True
    )

    guidance_generator = Agent(
        role="Public Guidance Generator",
        goal=(
            "Synthesize all collected information into clear, plain-language action guidance. "
            "Apply the CrisisSignalAmplifier to produce priority-scored, accessibility-aware "
            f"action steps. Accessibility needs: {accessibility_needs or 'none specified'}. "
            f"User context: {user_context or 'general public'}."
        ),
        backstory=(
            "You specialize in emergency risk communication — translating technical alerts into "
            "guidance that any resident can follow, regardless of literacy level or disability."
        ),
        llm=llm,
        tools=[amplifier, formatter],
        verbose=True,
        memory=True
    )

    # ── Tasks ──────────────────────────────────────────────

    task_fetch_noaa = Task(
        description=(
            f"Use the noaa_alert_fetcher tool to fetch active alerts for state '{state}'. "
            "Then use fema_disaster_fetcher to get recent declarations for the same state. "
            "Return the raw JSON results from both tools."
        ),
        expected_output="JSON containing NOAA alerts and FEMA declarations for the target state.",
        agent=alert_aggregator,
        tools=[noaa_tool, fema_tool]
    )

    task_geo_filter = Task(
        description=(
            f"Take the NOAA alerts from the previous task and apply the geo_filter tool. "
            f"Use user coordinates lat={user_lat}, lon={user_lon}, radius=300km. "
            "Sort results by severity and distance. Return filtered alert JSON."
        ),
        expected_output="Filtered list of nearby alerts sorted by severity and proximity.",
        agent=weather_analyst,
        tools=[geo_tool],
        context=[task_fetch_noaa]
    )

    task_shelter_info = Task(
        description=(
            "Using the filtered alerts from the previous task, run the crisis_signal_amplifier "
            f"tool with accessibility_needs='{accessibility_needs}' and user_context='{user_context}'. "
            "Extract shelter information from the amplified output. Return shelter options with services."
        ),
        expected_output="List of available shelters with capacity, accessibility features, and services.",
        agent=shelter_coordinator,
        tools=[amplifier],
        context=[task_geo_filter]
    )

    task_routes = Task(
        description=(
            "Based on the active alerts and their locations, provide evacuation route guidance. "
            "For each major alert, specify: recommended evacuation direction, roads to avoid, "
            "and transport options for those without vehicles. Keep guidance concise and actionable."
        ),
        expected_output="Evacuation route guidance per alert type with road recommendations.",
        agent=route_planner,
        tools=[geo_tool],
        context=[task_geo_filter]
    )

    task_contacts = Task(
        description=(
            "Compile emergency contact information for the affected state. Include: 911, FEMA helpline, "
            "211 services, crisis text line, and any accessibility-specific resources. "
            "Format as structured JSON."
        ),
        expected_output="Structured emergency contact directory in JSON format.",
        agent=contact_liaison,
        tools=[formatter],
        context=[task_shelter_info]
    )

    task_final_guidance = Task(
        description=(
            "Synthesize ALL outputs from previous tasks into a final comprehensive guidance report. "
            "Use crisis_signal_amplifier on the filtered alerts with full context. "
            "Then use report_formatter with format_type='structured' to produce the final report. "
            "The report must include: priority-scored action steps, accessibility adaptations, "
            "shelter options, evacuation guidance, and emergency contacts. "
            "Output must be valid JSON with all sections populated."
        ),
        expected_output=(
            "Complete structured JSON emergency guidance report with priority scores, "
            "confidence metrics, action steps, shelter info, routes, and contacts."
        ),
        agent=guidance_generator,
        tools=[amplifier, formatter],
        context=[task_geo_filter, task_shelter_info, task_routes, task_contacts]
    )

    # ── Crew ──────────────────────────────────────────────

    crew = Crew(
        agents=[
            controller,
            alert_aggregator,
            weather_analyst,
            shelter_coordinator,
            route_planner,
            contact_liaison,
            guidance_generator
        ],
        tasks=[
            task_fetch_noaa,
            task_geo_filter,
            task_shelter_info,
            task_routes,
            task_contacts,
            task_final_guidance
        ],
        process=Process.hierarchical,
        manager_agent=controller,
        verbose=True,
        memory=True,
        max_rpm=10  # Rate limit for free-tier Mistral
    )

    return crew
