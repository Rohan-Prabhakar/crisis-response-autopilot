# 🚨 Crisis Response Autopilot

Multi-agent emergency intelligence system built with CrewAI + Mistral.

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Project Structure

```
emergency_dashboard/
├── app.py                    # Main Streamlit entry point
├── requirements.txt
├── agents/
│   └── crew.py               # CrewAI agents + hierarchical crew
├── tools/
│   └── crisis_tools.py       # All 5 tools (3 built-in + CrisisSignalAmplifier + formatter)
└── tabs/
    ├── historical.py         # Tab 1: FEMA historical archive + map
    ├── live_feed.py          # Tab 2: NOAA live alerts + map
    ├── agent_processing.py   # Tab 3: Hierarchical workflow execution
    └── safety_chat.py        # Tab 4: Mistral-powered preparedness Q&A
```

## Agents

| Agent | Role | Tools |
|-------|------|-------|
| Controller | Orchestrates workflow, delegates tasks | NOAA, FEMA |
| Alert Aggregator | Fetches real-time federal alert data | NOAA, FEMA |
| Weather Analyst | Analyzes severity + geographic clusters | GeoFilter |
| Shelter Coordinator | Finds accessible shelter options | CrisisSignalAmplifier |
| Route Planner | Evacuation route guidance | GeoFilter |
| Contact Liaison | Compiles emergency contacts + accessibility resources | ReportFormatter |
| Guidance Generator | Synthesizes plain-language action steps | CrisisSignalAmplifier, ReportFormatter |

## Custom Tool: CrisisSignalAmplifier

Converts raw NOAA/FEMA metadata into:
- **Priority score** (0–100) based on severity, urgency, certainty, accessibility needs
- **Confidence score** (0–1) 
- **Time-sensitivity classification**
- **Accessibility-aware action steps** for mobility, visual, hearing, cognitive, medical needs
- **Context-aware notes** (no car, pets, elderly, etc.)

## API Keys

- **Mistral**: Required for full CrewAI mode and Safety Chat. Free tier at [console.mistral.ai](https://console.mistral.ai)
- **NOAA/FEMA**: No key required (public APIs).
  
## Run Modes

- **Full CrewAI mode**: Requires Mistral key. Runs complete hierarchical agent workflow.
