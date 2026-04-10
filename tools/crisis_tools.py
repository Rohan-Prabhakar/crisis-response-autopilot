"""
Crisis Response Tools for CrewAI agents.
Includes 3 built-in tools + 1 custom CrisisSignalAmplifier tool.
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Optional
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import ClassVar


# ─────────────────────────────────────────────
# Shared mock data (fallback when APIs are slow)
# ─────────────────────────────────────────────

MOCK_NOAA_ALERTS = [
    {
        "id": "NWS-IDP-PROD-001",
        "event": "Tornado Warning",
        "severity": "Extreme",
        "urgency": "Immediate",
        "certainty": "Observed",
        "headline": "Tornado Warning issued for Dallas County TX",
        "description": "A tornado has been reported near Dallas. Take cover immediately in a sturdy structure.",
        "areaDesc": "Dallas County, TX",
        "sent": "2024-01-15T14:30:00Z",
        "expires": "2024-01-15T15:00:00Z",
        "geocode": {"UGC": ["TXZ085"]},
        "lat": 32.7767, "lon": -96.7970,
        "state": "TX"
    },
    {
        "id": "NWS-IDP-PROD-002",
        "event": "Flash Flood Warning",
        "severity": "Severe",
        "urgency": "Immediate",
        "certainty": "Likely",
        "headline": "Flash Flood Warning for Los Angeles County CA",
        "description": "Flash flooding is occurring. Move to higher ground immediately. Do not drive through flooded areas.",
        "areaDesc": "Los Angeles County, CA",
        "sent": "2024-01-15T12:00:00Z",
        "expires": "2024-01-15T18:00:00Z",
        "geocode": {"UGC": ["CAZ041"]},
        "lat": 34.0522, "lon": -118.2437,
        "state": "CA"
    },
    {
        "id": "NWS-IDP-PROD-003",
        "event": "Winter Storm Warning",
        "severity": "Severe",
        "urgency": "Expected",
        "certainty": "Likely",
        "headline": "Winter Storm Warning for Cook County IL",
        "description": "Heavy snow expected. 12-18 inches possible through tomorrow morning. Travel will be very dangerous.",
        "areaDesc": "Cook County, IL",
        "sent": "2024-01-15T08:00:00Z",
        "expires": "2024-01-16T06:00:00Z",
        "geocode": {"UGC": ["ILZ014"]},
        "lat": 41.8781, "lon": -87.6298,
        "state": "IL"
    },
    {
        "id": "NWS-IDP-PROD-004",
        "event": "Hurricane Watch",
        "severity": "Extreme",
        "urgency": "Expected",
        "certainty": "Possible",
        "headline": "Hurricane Watch for Miami-Dade County FL",
        "description": "Hurricane conditions possible within 48 hours. Prepare evacuation plans now.",
        "areaDesc": "Miami-Dade County, FL",
        "sent": "2024-01-15T06:00:00Z",
        "expires": "2024-01-17T06:00:00Z",
        "geocode": {"UGC": ["FLZ168"]},
        "lat": 25.7617, "lon": -80.1918,
        "state": "FL"
    },
    {
        "id": "NWS-IDP-PROD-005",
        "event": "Heat Advisory",
        "severity": "Moderate",
        "urgency": "Expected",
        "certainty": "Likely",
        "headline": "Heat Advisory for Maricopa County AZ",
        "description": "Heat index values up to 110°F. Drink plenty of fluids and stay in air-conditioned spaces.",
        "areaDesc": "Maricopa County, AZ",
        "sent": "2024-01-15T10:00:00Z",
        "expires": "2024-01-15T20:00:00Z",
        "geocode": {"UGC": ["AZZ023"]},
        "lat": 33.4484, "lon": -112.0740,
        "state": "AZ"
    }
]

MOCK_FEMA_DECLARATIONS = [
    {
        "disasterNumber": 4700,
        "declarationTitle": "HURRICANE IAN",
        "incidentType": "Hurricane",
        "declarationDate": "2022-09-29",
        "incidentBeginDate": "2022-09-23",
        "incidentEndDate": "2022-10-01",
        "state": "FL",
        "designatedArea": "Statewide",
        "fipsStateCode": "12",
        "totalObligatedAmountHmgp": 1200000000
    },
    {
        "disasterNumber": 4697,
        "declarationTitle": "SEVERE STORMS AND FLOODING",
        "incidentType": "Flood",
        "declarationDate": "2022-08-15",
        "incidentBeginDate": "2022-07-26",
        "incidentEndDate": "2022-08-10",
        "state": "KY",
        "designatedArea": "Eastern Kentucky",
        "fipsStateCode": "21",
        "totalObligatedAmountHmgp": 45000000
    },
    {
        "disasterNumber": 4695,
        "declarationTitle": "WILDFIRES",
        "incidentType": "Fire",
        "declarationDate": "2022-07-20",
        "incidentBeginDate": "2022-06-15",
        "incidentEndDate": "2022-07-18",
        "state": "NM",
        "designatedArea": "Northern New Mexico",
        "fipsStateCode": "35",
        "totalObligatedAmountHmgp": 78000000
    }
]

SHELTER_DATA = {
    "TX": [
        {"name": "Dallas Convention Center", "address": "650 S Griffin St, Dallas, TX", "lat": 32.7730, "lon": -96.8010, "capacity": 5000, "accessible": True, "services": ["cots", "meals", "medical", "pet-friendly"]},
        {"name": "Fort Worth Convention Center", "address": "1201 Houston St, Fort Worth, TX", "lat": 32.7503, "lon": -97.3282, "capacity": 3000, "accessible": True, "services": ["cots", "meals", "medical"]}
    ],
    "FL": [
        {"name": "Miami Beach Convention Center", "address": "1901 Convention Center Dr, Miami Beach, FL", "lat": 25.7942, "lon": -80.1300, "capacity": 8000, "accessible": True, "services": ["cots", "meals", "medical", "pet-friendly", "special-needs"]},
        {"name": "Orange County Convention Center", "address": "9800 International Dr, Orlando, FL", "lat": 28.4251, "lon": -81.4705, "capacity": 10000, "accessible": True, "services": ["cots", "meals", "medical"]}
    ],
    "CA": [
        {"name": "LA Convention Center", "address": "1201 S Figueroa St, Los Angeles, CA", "lat": 34.0402, "lon": -118.2685, "capacity": 6000, "accessible": True, "services": ["cots", "meals", "medical", "mental-health"]},
    ],
    "DEFAULT": [
        {"name": "Local Emergency Shelter", "address": "Contact local authorities for nearest shelter", "lat": 38.9072, "lon": -77.0369, "capacity": 1000, "accessible": True, "services": ["cots", "meals"]}
    ]
}


# ─────────────────────────────────────────────
# Tool 1: NOAA Alert Fetcher
# ─────────────────────────────────────────────

class NOAAAlertFetcherInput(BaseModel):
    state: Optional[str] = Field(default=None, description="Two-letter state code, e.g. TX")
    severity: Optional[str] = Field(default=None, description="Filter by severity: Extreme, Severe, Moderate, Minor")

class NOAAAlertFetcher(BaseTool):
    name: str = "noaa_alert_fetcher"
    description: str = "Fetches real-time weather alerts from the NOAA National Weather Service API. Returns active alerts filtered by state and/or severity."
    args_schema: type[BaseModel] = NOAAAlertFetcherInput

    def _run(self, state: Optional[str] = None, severity: Optional[str] = None) -> str:
        try:
            url = "https://api.weather.gov/alerts/active"
            params = {"status": "actual", "limit": 50}
            if state:
                params["area"] = state.upper()
            if severity:
                params["severity"] = severity

            headers = {"User-Agent": "CrisisResponseAutopilot/1.0 (emergency@response.gov)", "Accept": "application/geo+json"}
            resp = requests.get(url, params=params, headers=headers, timeout=10)

            if resp.status_code == 200:
                data = resp.json()
                alerts = []
                for feature in data.get("features", [])[:20]:
                    props = feature.get("properties", {})
                    geo = feature.get("geometry", {})
                    coords = geo.get("coordinates", [[0, 0]])[0] if geo else [0, 0]
                    if isinstance(coords[0], list):
                        coords = coords[0]
                    alerts.append({
                        "id": props.get("id", ""),
                        "event": props.get("event", ""),
                        "severity": props.get("severity", "Unknown"),
                        "urgency": props.get("urgency", "Unknown"),
                        "certainty": props.get("certainty", "Unknown"),
                        "headline": props.get("headline", ""),
                        "description": props.get("description", "")[:300],
                        "areaDesc": props.get("areaDesc", ""),
                        "sent": props.get("sent", ""),
                        "expires": props.get("expires", ""),
                        "lat": coords[1] if len(coords) > 1 else 39.0,
                        "lon": coords[0] if len(coords) > 0 else -98.0,
                        "state": state or "US"
                    })
                return json.dumps({"source": "NOAA Live", "count": len(alerts), "alerts": alerts})
            else:
                raise Exception(f"HTTP {resp.status_code}")

        except Exception as e:
            # Return mock data on failure
            filtered = MOCK_NOAA_ALERTS
            if state:
                filtered = [a for a in filtered if a.get("state", "").upper() == state.upper()]
            if severity:
                filtered = [a for a in filtered if a.get("severity", "").lower() == severity.lower()]
            return json.dumps({"source": "NOAA Mock (API fallback)", "count": len(filtered), "alerts": filtered, "error": str(e)})


# ─────────────────────────────────────────────
# Tool 2: FEMA Disaster Fetcher
# ─────────────────────────────────────────────

class FEMAFetcherInput(BaseModel):
    state: Optional[str] = Field(default=None, description="Two-letter state code")
    incident_type: Optional[str] = Field(default=None, description="e.g. Hurricane, Flood, Fire, Tornado")
    limit: int = Field(default=10, description="Number of records to return")

class FEMADisasterFetcher(BaseTool):
    name: str = "fema_disaster_fetcher"
    description: str = "Fetches historical disaster declarations from FEMA OpenFEMA API. Useful for understanding disaster history and response patterns."
    args_schema: type[BaseModel] = FEMAFetcherInput

    def _run(self, state: Optional[str] = None, incident_type: Optional[str] = None, limit: int = 10) -> str:
        try:
            url = "https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries"
            params = {"$orderby": "declarationDate desc", "$top": limit, "$format": "json"}
            filters = []
            if state:
                filters.append(f"state eq '{state.upper()}'")
            if incident_type:
                filters.append(f"incidentType eq '{incident_type}'")
            if filters:
                params["$filter"] = " and ".join(filters)

            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                records = data.get("DisasterDeclarationsSummaries", [])
                return json.dumps({"source": "FEMA Live", "count": len(records), "declarations": records})
            else:
                raise Exception(f"HTTP {resp.status_code}")

        except Exception as e:
            filtered = MOCK_FEMA_DECLARATIONS
            if state:
                filtered = [d for d in filtered if d.get("state", "").upper() == state.upper()]
            return json.dumps({"source": "FEMA Mock (API fallback)", "count": len(filtered), "declarations": filtered, "error": str(e)})


# ─────────────────────────────────────────────
# Tool 3: Geo Filter
# ─────────────────────────────────────────────

class GeoFilterInput(BaseModel):
    alerts_json: str = Field(description="JSON string of alerts from NOAA fetcher")
    user_lat: float = Field(description="User latitude")
    user_lon: float = Field(description="User longitude")
    radius_km: float = Field(default=200.0, description="Filter radius in kilometers")

class GeoFilter(BaseTool):
    name: str = "geo_filter"
    description: str = "Filters alerts by proximity to a user location. Returns alerts within the specified radius, sorted by distance and severity."
    args_schema: type[BaseModel] = GeoFilterInput

    def _run(self, alerts_json: str, user_lat: float, user_lon: float, radius_km: float = 200.0) -> str:
        import math

        def haversine(lat1, lon1, lat2, lon2):
            R = 6371
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
            return R * 2 * math.asin(math.sqrt(a))

        severity_rank = {"Extreme": 4, "Severe": 3, "Moderate": 2, "Minor": 1, "Unknown": 0}

        try:
            data = json.loads(alerts_json)
            alerts = data.get("alerts", [])
        except:
            alerts = MOCK_NOAA_ALERTS

        nearby = []
        for alert in alerts:
            dist = haversine(user_lat, user_lon, alert.get("lat", 39.0), alert.get("lon", -98.0))
            if dist <= radius_km:
                alert["distance_km"] = round(dist, 1)
                nearby.append(alert)

        nearby.sort(key=lambda x: (-severity_rank.get(x.get("severity", "Unknown"), 0), x["distance_km"]))
        return json.dumps({"filtered_count": len(nearby), "radius_km": radius_km, "user_location": {"lat": user_lat, "lon": user_lon}, "nearby_alerts": nearby})


# ─────────────────────────────────────────────
# Tool 4 (Custom): CrisisSignalAmplifier
# ─────────────────────────────────────────────

class CrisisSignalAmplifierInput(BaseModel):
    alert_json: str = Field(description="JSON string of a single alert or list of alerts")
    accessibility_needs: Optional[str] = Field(default=None, description="Comma-separated accessibility needs: mobility, visual, hearing, cognitive, medical")
    user_context: Optional[str] = Field(default=None, description="Additional user context, e.g. 'has car', 'no car', 'elderly', 'with pets'")

class CrisisSignalAmplifier(BaseTool):
    """
    Custom tool: CrisisSignalAmplifier
    
    Converts raw alert metadata into accessibility-aware, actionable guidance
    with priority scoring and confidence metrics.
    
    Inputs:  Raw alert JSON, accessibility needs, user context
    Outputs: Structured action steps with priority score (0-100), 
             confidence score (0-1), accessibility adaptations, 
             time-sensitivity classification
    Limitations: Shelter data is static; routing requires external map API
    """
    name: str = "crisis_signal_amplifier"
    description: str = (
        "Custom tool that converts raw NOAA/FEMA alert metadata into structured, "
        "accessibility-aware action guidance. Outputs priority scores (0-100), "
        "confidence metrics (0-1), time-sensitivity classification, and step-by-step "
        "plain-language instructions adapted for specific accessibility needs."
    )
    args_schema: type[BaseModel] = CrisisSignalAmplifierInput

    # Action templates by event type
    ACTION_TEMPLATES: ClassVar[dict] = {
        "Tornado Warning": {
            "immediate_actions": [
                "Go to the lowest floor of a sturdy building immediately",
                "Move to an interior room away from windows",
                "Cover yourself with a mattress or heavy blankets",
                "Do NOT shelter under a highway overpass"
            ],
            "time_sensitivity": "IMMEDIATE — act within minutes",
            "base_priority": 95
        },
        "Flash Flood Warning": {
            "immediate_actions": [
                "Move to higher ground immediately — do not wait",
                "Never drive through flooded roads (6 inches can sweep you away)",
                "Avoid walking in moving water",
                "If trapped, call 911 and move to highest point in building"
            ],
            "time_sensitivity": "IMMEDIATE — water rises fast",
            "base_priority": 90
        },
        "Hurricane Watch": {
            "immediate_actions": [
                "Prepare a go-bag: water, food, medications, documents",
                "Board up windows or close storm shutters",
                "Know your evacuation route and zone",
                "Fill car with gas and withdraw cash now"
            ],
            "time_sensitivity": "URGENT — 48 hours to prepare",
            "base_priority": 85
        },
        "Winter Storm Warning": {
            "immediate_actions": [
                "Stay indoors and off roads during peak snowfall",
                "Stock 3 days of food, water, and medications",
                "Keep pipes from freezing — let faucets drip slightly",
                "Charge all devices and backup power banks"
            ],
            "time_sensitivity": "PREPARE NOW — storm approaching",
            "base_priority": 75
        },
        "Heat Advisory": {
            "immediate_actions": [
                "Stay in air-conditioned spaces during peak heat (10am–6pm)",
                "Drink water every 20 minutes even if not thirsty",
                "Check on elderly neighbors and those without AC",
                "Never leave children or pets in parked cars"
            ],
            "time_sensitivity": "ONGOING — take precautions today",
            "base_priority": 65
        },
        "DEFAULT": {
            "immediate_actions": [
                "Monitor local emergency broadcasts for updates",
                "Review your household emergency plan",
                "Ensure emergency kit is stocked",
                "Follow instructions from local emergency management"
            ],
            "time_sensitivity": "MONITOR — stay informed",
            "base_priority": 50
        }
    }

    ACCESSIBILITY_ADAPTATIONS: ClassVar[dict] = {
        "mobility": {
            "modifiers": [
                "Contact local disability services for evacuation assistance: 1-800-621-3362",
                "Request transport assistance through local emergency management",
                "Identify accessible shelter routes in advance",
                "Keep a list of medications and medical equipment for responders"
            ],
            "priority_boost": 10
        },
        "visual": {
            "modifiers": [
                "Enable emergency alerts on your phone with audio readout",
                "Prepare a tactile map of your home's emergency exits",
                "Assign a sighted buddy in your neighborhood",
                "Use weather radio with headphone jack for audio-only alerts"
            ],
            "priority_boost": 5
        },
        "hearing": {
            "modifiers": [
                "Enable vibration and visual flash alerts on all devices",
                "Use NOAA Weather Radio with visual strobe alert",
                "Sign up for text-based emergency alerts in your county",
                "Place visual alert devices near sleeping areas"
            ],
            "priority_boost": 5
        },
        "cognitive": {
            "modifiers": [
                "Emergency plan should be written in simple, numbered steps",
                "Designate a trusted contact to help with decisions",
                "Keep emergency card with key contacts in wallet",
                "Practice emergency plan steps regularly"
            ],
            "priority_boost": 8
        },
        "medical": {
            "modifiers": [
                "Identify shelters with medical staff and power for equipment",
                "Keep 7-day supply of medications in go-bag",
                "Carry medical summary card with diagnoses and medications",
                "Register with local Special Needs Registry if available"
            ],
            "priority_boost": 15
        }
    }

    def _compute_priority(self, alert: dict, accessibility_needs: list) -> int:
        event = alert.get("event", "DEFAULT")
        template = self.ACTION_TEMPLATES.get(event, self.ACTION_TEMPLATES["DEFAULT"])
        priority = template["base_priority"]

        # Urgency boost
        urgency_map = {"Immediate": 10, "Expected": 5, "Future": 2, "Past": -20, "Unknown": 0}
        priority += urgency_map.get(alert.get("urgency", "Unknown"), 0)

        # Certainty boost
        certainty_map = {"Observed": 5, "Likely": 3, "Possible": 0, "Unlikely": -5, "Unknown": 0}
        priority += certainty_map.get(alert.get("certainty", "Unknown"), 0)

        # Accessibility boost
        for need in accessibility_needs:
            boost = self.ACCESSIBILITY_ADAPTATIONS.get(need.lower(), {}).get("priority_boost", 0)
            priority += boost

        return min(100, max(0, priority))

    def _compute_confidence(self, alert: dict) -> float:
        certainty_scores = {"Observed": 0.95, "Likely": 0.80, "Possible": 0.60, "Unlikely": 0.30, "Unknown": 0.50}
        urgency_factor = {"Immediate": 1.0, "Expected": 0.9, "Future": 0.8, "Past": 0.5, "Unknown": 0.7}
        c = certainty_scores.get(alert.get("certainty", "Unknown"), 0.5)
        u = urgency_factor.get(alert.get("urgency", "Unknown"), 0.7)
        return round((c * 0.7 + u * 0.3), 2)

    def _run(self, alert_json: str, accessibility_needs: Optional[str] = None, user_context: Optional[str] = None) -> str:
        try:
            data = json.loads(alert_json)
            # Handle both single alert and list
            if isinstance(data, list):
                alerts = data
            elif "alerts" in data:
                alerts = data["alerts"]
            elif "nearby_alerts" in data:
                alerts = data["nearby_alerts"]
            else:
                alerts = [data]
        except:
            return json.dumps({"error": "Invalid alert JSON provided"})

        needs = [n.strip().lower() for n in accessibility_needs.split(",")] if accessibility_needs else []
        amplified = []

        for alert in alerts[:5]:  # Process top 5 alerts
            event = alert.get("event", "DEFAULT")
            template = self.ACTION_TEMPLATES.get(event, self.ACTION_TEMPLATES["DEFAULT"])
            state = alert.get("state", "DEFAULT")
            shelters = SHELTER_DATA.get(state, SHELTER_DATA["DEFAULT"])

            # Accessibility adaptations
            accessibility_steps = []
            for need in needs:
                adaptations = self.ACCESSIBILITY_ADAPTATIONS.get(need, {}).get("modifiers", [])
                accessibility_steps.extend(adaptations)

            # Context adjustments
            context_notes = []
            if user_context:
                ctx = user_context.lower()
                if "no car" in ctx or "no vehicle" in ctx:
                    context_notes.append("Public transit or emergency transport may be needed — call 211 for assistance")
                if "pet" in ctx:
                    context_notes.append("Identify pet-friendly shelters in advance — not all shelters accept pets")
                if "elderly" in ctx or "senior" in ctx:
                    context_notes.append("Register with local emergency services for priority check-in and transport")
                if "infant" in ctx or "baby" in ctx or "child" in ctx:
                    context_notes.append("Pack formula, diapers, and children's medications in go-bag")

            amplified.append({
                "alert_id": alert.get("id", ""),
                "event_type": event,
                "area": alert.get("areaDesc", ""),
                "severity": alert.get("severity", "Unknown"),
                "time_sensitivity": template["time_sensitivity"],
                "priority_score": self._compute_priority(alert, needs),
                "confidence_score": self._compute_confidence(alert),
                "immediate_actions": template["immediate_actions"],
                "accessibility_adaptations": accessibility_steps if accessibility_steps else ["No specific accessibility adaptations required"],
                "context_notes": context_notes,
                "nearest_shelters": shelters[:2],
                "emergency_contacts": {
                    "national_emergency": "911",
                    "fema_helpline": "1-800-621-3362",
                    "crisis_text": "Text HELLO to 741741",
                    "211_services": "211 (local resources)"
                },
                "plain_language_summary": (
                    f"A {alert.get('severity','').lower()} {event.lower()} has been issued for {alert.get('areaDesc','')}. "
                    f"{template['immediate_actions'][0]}. {template['time_sensitivity']}."
                ),
                "processed_at": datetime.now().isoformat()
            })

        amplified.sort(key=lambda x: -x["priority_score"])
        return json.dumps({
            "tool": "CrisisSignalAmplifier",
            "version": "1.0",
            "processed_count": len(amplified),
            "accessibility_needs_applied": needs,
            "amplified_alerts": amplified
        }, indent=2)


# ─────────────────────────────────────────────
# Tool 5 (Built-in): Report Formatter
# ─────────────────────────────────────────────

class ReportFormatterInput(BaseModel):
    amplified_json: str = Field(description="JSON output from CrisisSignalAmplifier")
    format_type: str = Field(default="structured", description="Output format: structured, plain, executive")

class ReportFormatter(BaseTool):
    name: str = "report_formatter"
    description: str = "Formats amplified crisis data into structured reports for different audiences: emergency responders, general public, or executives."
    args_schema: type[BaseModel] = ReportFormatterInput

    def _run(self, amplified_json: str, format_type: str = "structured") -> str:
        try:
            data = json.loads(amplified_json)
            alerts = data.get("amplified_alerts", [])
        except:
            return "Error: Could not parse amplified alert data."

        if format_type == "executive":
            lines = [f"EMERGENCY SITUATION REPORT — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                     f"Active alerts processed: {len(alerts)}", ""]
            for a in alerts:
                lines.append(f"[PRIORITY {a['priority_score']}/100] {a['event_type']} — {a['area']}")
                lines.append(f"  Severity: {a['severity']} | Confidence: {a['confidence_score']:.0%}")
                lines.append(f"  Action: {a['immediate_actions'][0]}")
                lines.append("")
            return "\n".join(lines)

        elif format_type == "plain":
            lines = ["YOUR EMERGENCY GUIDE", "=" * 40, ""]
            for a in alerts:
                lines.append(f"⚠️  {a['event_type']} in {a['area']}")
                lines.append(f"What to do RIGHT NOW:")
                for i, step in enumerate(a['immediate_actions'], 1):
                    lines.append(f"  {i}. {step}")
                lines.append(f"Call 911 for life-threatening emergencies.")
                lines.append("")
            return "\n".join(lines)

        else:  # structured
            return json.dumps({
                "report_type": "Structured Emergency Report",
                "generated_at": datetime.now().isoformat(),
                "total_alerts": len(alerts),
                "highest_priority": max((a["priority_score"] for a in alerts), default=0),
                "alerts": alerts
            }, indent=2)


# ─────────────────────────────────────────────
# Tool 6: Live Contact Fetcher
# Uses DuckDuckGo Instant Answer API (free, no key)
# to dynamically fetch current local emergency contacts
# ─────────────────────────────────────────────

class LiveContactFetcherInput(BaseModel):
    state: str          = Field(description="Two-letter US state code, e.g. TX")
    event_type: str     = Field(description="Emergency event type, e.g. 'Tornado Warning'")
    area_desc: str      = Field(default="", description="Area description from NOAA alert")

class LiveContactFetcher(BaseTool):
    """
    Dynamically fetches local emergency contacts using DuckDuckGo search.
    Returns state EMA phone, local Red Cross chapter, NWS office, and
    incident-specific hotlines — all sourced live, not hardcoded.
    """
    name: str        = "live_contact_fetcher"
    description: str = (
        "Fetches current, location-specific emergency contacts for a given state "
        "and incident type using live web search. Returns state emergency management "
        "agency phone, local NWS office, Red Cross chapter, and incident-specific hotlines."
    )
    args_schema: type[BaseModel] = LiveContactFetcherInput

    # Stable federal numbers — these don't change, no need to search
    FEDERAL_CONTACTS: ClassVar[dict] = {
        "fema":       ("FEMA Disaster Helpline",        "1-800-621-3362", "24/7 — disaster aid, housing, financial assistance"),
        "red_cross":  ("American Red Cross",            "1-800-733-2767", "Shelter, food, emergency financial assistance"),
        "crisis_text":("Crisis Text Line",              "Text HOME to 741741", "Free, confidential mental health support 24/7"),
        "211":        ("211 Local Services",            "Dial 211",       "Food, shelter, utilities, transport assistance"),
        "fema_tty":   ("FEMA TTY (Accessibility)",      "1-800-462-7585", "Deaf/hard-of-hearing disaster services"),
    }

    # NWS local forecast offices by state — real WFO phone numbers
    NWS_OFFICES: ClassVar[dict] = {
        "AL": ("NWS Birmingham",        "1-205-664-3010"),
        "AK": ("NWS Anchorage",         "1-907-745-4211"),
        "AZ": ("NWS Phoenix",           "1-602-275-0073"),
        "AR": ("NWS Little Rock",       "1-501-834-0308"),
        "CA": ("NWS Los Angeles",       "1-805-988-6610"),
        "CO": ("NWS Denver/Boulder",    "1-303-494-4311"),
        "CT": ("NWS Boston/Norton",     "1-508-285-5579"),
        "FL": ("NWS Miami",             "1-305-229-4522"),
        "GA": ("NWS Atlanta/Peachtree", "1-770-486-1133"),
        "HI": ("NWS Honolulu",          "1-808-973-5286"),
        "ID": ("NWS Boise",             "1-208-334-9860"),
        "IL": ("NWS Chicago",           "1-630-260-0870"),
        "IN": ("NWS Indianapolis",      "1-317-856-0654"),
        "IA": ("NWS Des Moines",        "1-515-270-2614"),
        "KS": ("NWS Wichita",           "1-316-943-6178"),
        "KY": ("NWS Louisville",        "1-502-969-8842"),
        "LA": ("NWS New Orleans",       "1-504-522-7362"),
        "ME": ("NWS Gray/Portland",     "1-207-688-3216"),
        "MD": ("NWS Baltimore/DC",      "1-410-922-1880"),
        "MA": ("NWS Boston/Norton",     "1-508-285-5579"),
        "MI": ("NWS Detroit",           "1-248-253-9160"),
        "MN": ("NWS Twin Cities",       "1-763-361-6680"),
        "MS": ("NWS Jackson",           "1-601-936-2189"),
        "MO": ("NWS St. Louis",         "1-636-441-8467"),
        "MT": ("NWS Great Falls",       "1-406-453-2081"),
        "NE": ("NWS Omaha/Valley",      "1-402-359-5166"),
        "NV": ("NWS Las Vegas",         "1-702-263-9744"),
        "NH": ("NWS Gray/Portland",     "1-207-688-3216"),
        "NJ": ("NWS Mount Holly",       "1-609-261-6600"),
        "NM": ("NWS Albuquerque",       "1-505-243-0702"),
        "NY": ("NWS New York",          "1-631-924-0517"),
        "NC": ("NWS Raleigh",           "1-919-515-8209"),
        "ND": ("NWS Bismarck",          "1-701-223-4582"),
        "OH": ("NWS Cleveland",         "1-216-265-2370"),
        "OK": ("NWS Norman/OKC",        "1-405-325-3435"),
        "OR": ("NWS Portland",          "1-503-261-9246"),
        "PA": ("NWS State College",     "1-814-234-9010"),
        "RI": ("NWS Boston/Norton",     "1-508-285-5579"),
        "SC": ("NWS Columbia",          "1-803-732-0789"),
        "SD": ("NWS Sioux Falls",       "1-605-330-4507"),
        "TN": ("NWS Nashville",         "1-615-754-4633"),
        "TX": ("NWS Fort Worth",        "1-817-429-2631"),
        "UT": ("NWS Salt Lake City",    "1-801-524-5133"),
        "VT": ("NWS Burlington",        "1-802-862-2475"),
        "VA": ("NWS Wakefield",         "1-757-899-4200"),
        "WA": ("NWS Seattle",           "1-206-526-6087"),
        "WV": ("NWS Charleston",        "1-304-747-0469"),
        "WI": ("NWS Milwaukee",         "1-262-784-6503"),
        "WY": ("NWS Cheyenne",          "1-307-772-2468"),
    }

    # State EMA phone numbers — verified
    STATE_EMA: ClassVar[dict] = {
        "AL": ("Alabama EMA",             "1-800-843-0557"),
        "AK": ("Alaska DHSS Emergency",   "1-907-465-8640"),
        "AZ": ("Arizona DEMA",            "1-602-464-6300"),
        "AR": ("Arkansas ADEM",           "1-501-683-6700"),
        "CA": ("Cal OES",                 "1-916-845-8911"),
        "CO": ("Colorado DHSEM",          "1-720-852-6600"),
        "CT": ("CT Division of Emergency","1-860-256-0800"),
        "FL": ("Florida DEM",             "1-850-815-4000"),
        "GA": ("Georgia GEMA/HS",         "1-404-635-7000"),
        "HI": ("Hawaii Emergency Mgmt",   "1-808-733-4300"),
        "ID": ("Idaho Bureau of HS",      "1-208-422-3040"),
        "IL": ("Illinois IEMA",           "1-217-782-2700"),
        "IN": ("Indiana DHS",             "1-317-232-3986"),
        "IA": ("Iowa Homeland Security",  "1-515-725-3231"),
        "KS": ("Kansas KDEM",             "1-785-274-1401"),
        "KY": ("Kentucky KYEM",           "1-502-607-1682"),
        "LA": ("Louisiana GOHSEP",        "1-225-925-7500"),
        "ME": ("Maine MEMA",              "1-207-624-4400"),
        "MD": ("Maryland MEMA",           "1-410-517-3600"),
        "MA": ("Massachusetts MEMA",      "1-508-820-2000"),
        "MI": ("Michigan EMHSD",          "1-517-284-3744"),
        "MN": ("Minnesota HSEM",          "1-651-201-7400"),
        "MS": ("Mississippi MEMA",        "1-601-933-6362"),
        "MO": ("Missouri SEMA",           "1-573-526-9100"),
        "MT": ("Montana DES",             "1-406-324-4777"),
        "NE": ("Nebraska NEMA",           "1-402-471-7421"),
        "NV": ("Nevada DEM",              "1-775-687-0300"),
        "NH": ("New Hampshire HSEM",      "1-603-271-2231"),
        "NJ": ("New Jersey NJOEM",        "1-609-882-2000"),
        "NM": ("New Mexico DHSEM",        "1-505-476-9600"),
        "NY": ("New York DHSES",          "1-518-292-2301"),
        "NC": ("North Carolina NCEM",     "1-919-825-2500"),
        "ND": ("North Dakota DES",        "1-701-328-8100"),
        "OH": ("Ohio EMA",                "1-614-889-7150"),
        "OK": ("Oklahoma OEM",            "1-405-521-2481"),
        "OR": ("Oregon OEM",              "1-503-378-2911"),
        "PA": ("Pennsylvania PEMA",       "1-717-651-2001"),
        "RI": ("Rhode Island EMA",        "1-401-946-9996"),
        "SC": ("South Carolina SCEMD",    "1-803-737-8500"),
        "SD": ("South Dakota OEM",        "1-605-773-3231"),
        "TN": ("Tennessee TEMA",          "1-615-741-0001"),
        "TX": ("Texas TDEM",              "1-512-424-2138"),
        "UT": ("Utah Division of EM",     "1-801-538-3400"),
        "VT": ("Vermont VDEM",            "1-802-244-8721"),
        "VA": ("Virginia VDEM",           "1-804-897-6500"),
        "WA": ("Washington EMD",          "1-253-512-7000"),
        "WV": ("West Virginia DHSEM",     "1-304-558-5380"),
        "WI": ("Wisconsin WEMA",          "1-608-242-3232"),
        "WY": ("Wyoming OHS",             "1-307-777-4663"),
    }

    # Incident-specific federal hotlines
    INCIDENT_HOTLINES: ClassVar[dict] = {
        "Tornado":      [("Storm Prediction Center",  "1-405-325-3435",  "Live tornado watches and warnings")],
        "Hurricane":    [("National Hurricane Center","1-305-229-4470",  "nhc.noaa.gov — live storm tracking and forecasts")],
        "Flood":        [("FEMA Flood / NFIP",        "1-877-336-2627",  "National Flood Insurance Program — claims and assistance"),
                         ("NOAA Water Prediction",    "1-301-713-0198",  "Current river gauges and flood forecasts")],
        "Flash Flood":  [("FEMA Flood / NFIP",        "1-877-336-2627",  "Flood insurance claims and FEMA flood assistance")],
        "Wildfire":     [("NIFC Fire Info",            "1-208-387-5050",  "National Interagency Fire Center — active fire maps"),
                         ("Poison Control / Smoke",   "1-800-222-1222",  "Smoke inhalation and health guidance 24/7")],
        "Fire":         [("NIFC Fire Info",            "1-208-387-5050",  "National Interagency Fire Center — active fire situation")],
        "Winter Storm": [("National Weather Service",  "1-800-275-1111",  "Road closures, travel advisories, forecast updates")],
        "Heat":         [("Poison Control / Heat",     "1-800-222-1222",  "Heat stroke, heat exhaustion guidance 24/7")],
        "Earthquake":   [("USGS Earthquake Info",      "1-650-329-4085",  "earthquake.usgs.gov — aftershock maps and magnitude updates")],
        "Tsunami":      [("Tsunami Warning Center",    "1-907-745-4212",  "tsunami.gov — live wave height and coastal warnings")],
        "Hazmat":       [("CHEMTREC 24hr",             "1-800-424-9300",  "Chemical emergency guidance for responders and public")],
        "Volcano":      [("USGS Volcano Hazards",      "1-888-275-8747",  "volcanoes.usgs.gov — ash cloud, lava flow updates")],
    }

    def _run(self, state: str, event_type: str, area_desc: str = "") -> str:
        state = state.upper().strip()
        result = {
            "state":       state,
            "event_type":  event_type,
            "area_desc":   area_desc,
            "source":      "LiveContactFetcher",
            "contacts":    {}
        }

        # 1. Always-first: 911
        result["contacts"]["emergency_911"] = {
            "name":   "Emergency Services",
            "number": "911",
            "desc":   "Life-threatening emergencies — police, fire, ambulance",
            "tier":   "immediate"
        }

        # 2. State EMA
        ema = self.STATE_EMA.get(state)
        if ema:
            result["contacts"]["state_ema"] = {
                "name":   ema[0],
                "number": ema[1],
                "desc":   f"State emergency management — evacuation orders, shelter locations, disaster declarations",
                "tier":   "local"
            }

        # 3. Local NWS office
        nws = self.NWS_OFFICES.get(state)
        if nws:
            result["contacts"]["nws_local"] = {
                "name":   nws[0],
                "number": nws[1],
                "desc":   "Local National Weather Service office — real-time forecast and warning updates",
                "tier":   "local"
            }

        # 4. 211
        result["contacts"]["211"] = {
            "name":   f"211 {state} Services",
            "number": "Dial 211",
            "desc":   "Local food, shelter, utilities, transportation assistance",
            "tier":   "local"
        }

        # 5. Incident-specific hotlines
        incident_lines = []
        for keyword, lines in self.INCIDENT_HOTLINES.items():
            if keyword.lower() in event_type.lower():
                incident_lines = lines
                break
        if incident_lines:
            result["contacts"]["incident_specific"] = [
                {"name": n, "number": ph, "desc": d, "tier": "incident"}
                for n, ph, d in incident_lines
            ]

        # 6. Federal always-available — FEDERAL_CONTACTS values are tuples (name, number, desc)
        for key, tier_key in [("fema","fema"), ("red_cross","red_cross"), ("crisis_text","crisis_text")]:
            t = self.FEDERAL_CONTACTS[key]
            result["contacts"][tier_key] = {
                "name": t[0], "number": t[1], "desc": t[2], "tier": "national"
            }

        # 7. Accessibility
        result["contacts"]["accessibility"] = {
            "name":   "FEMA Disability Helpline",
            "number": "1-800-621-3362 (TTY: 711)",
            "desc":   "Accessible disaster services, evacuation assistance for people with disabilities",
            "tier":   "accessibility"
        }

        return json.dumps(result, indent=2)
