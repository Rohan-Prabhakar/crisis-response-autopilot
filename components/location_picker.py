"""Geocoding utilities. No UI — location is handled via browser JS in app.py."""

import requests

STATE_NAME_TO_CODE = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID",
    "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
    "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
    "Wisconsin": "WI", "Wyoming": "WY"
}

def reverse_geocode(lat: float, lon: float) -> dict:
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lon, "format": "json", "addressdetails": 1},
            headers={"User-Agent": "CrisisResponseAutopilot/1.0"},
            timeout=6
        )
        if resp.status_code == 200:
            addr = resp.json().get("address", {})
            state_name = addr.get("state", "")
            city = addr.get("city") or addr.get("town") or addr.get("county", "")
            state_code = STATE_NAME_TO_CODE.get(state_name, "")
            return {
                "state": state_code,
                "state_name": state_name,
                "city": city,
                "display": f"{city}, {state_code}" if city and state_code else state_name or "Unknown"
            }
    except Exception:
        pass
    return {"state": "", "state_name": "", "city": "", "display": "Unknown location"}


def geocode_city(query: str) -> dict | None:
    """Forward geocode a city name → lat/lon/state dict or None."""
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": query + ", USA", "format": "json", "limit": 1, "addressdetails": 1},
            headers={"User-Agent": "CrisisResponseAutopilot/1.0"},
            timeout=6
        )
        if resp.status_code == 200:
            results = resp.json()
            if results:
                r = results[0]
                lat = float(r["lat"])
                lon = float(r["lon"])
                addr = r.get("address", {})
                state_name = addr.get("state", "")
                state_code = STATE_NAME_TO_CODE.get(state_name, "")
                city = addr.get("city") or addr.get("town") or addr.get("county", "")
                return {
                    "lat": lat, "lon": lon,
                    "state": state_code or "All States",
                    "display": f"{city}, {state_code}" if city and state_code else query,
                    "source": "map_click"
                }
    except Exception:
        pass
    return None
