import sys
from os import environ

import httpx
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("weather")

# Constants
NWS_API_BASE = "https://api.weather.gov"
USER_AGENT = "weather-app/1.0"
API_TOKEN = environ.get("PT_API_TOKEN", "your_api_token_here")  # Replace with your actual token


async def make_pt_request(url: str) -> dict | None:
    """Make a request to PractiTest API and return parsed JSON."""
    headers = {
        "User-Agent": 'Shield/1.0',
        "Content-Type": "application/json",
        "PTToken": API_TOKEN
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()

            print(f"\n✅ Request successful:", file=sys.stderr)
            print(f"Status: {response.status_code}", file=sys.stderr)
            print(f"URL: {url}", file=sys.stderr)
            print(f"Headers: {headers}", file=sys.stderr)
            print(f"Raw JSON:\n{response.text}\n", file=sys.stderr)

            return response.json()
        except Exception as e:
            print(f"\n❌ Request failed: {e}", file=sys.stderr)
            # print("Debugging info", file=sys.stderr)
            return None


def format_instance(feature: dict) -> str:
    """Format an alert feature into a readable string."""
    #
    # class InstanceAttributes(PracitiBase):
    #     name: str
    #     set_id: str
    #     set_display_id: str
    #     test_id: str
    #     test_display_id: str
    #     custom_fields: dict
    #     display_id: str
    #     last_run: str = None
    #     run_status: str
    props = feature["attributes"]
    return f"""
Full Test Name: {props.get('name', 'Unknown')}
Short Test Name: {props.get('name', 'Unknown').rsplit('[')[0] if '[' in props.get('name', 'Unknown') else 'Unknown'}
Automation Test Owner (PrivateName + first letter of surname): {props.get('custom_fields', {}).get('---f-194433', 'Unknown')}
Environment: {props.get('custom_fields', {}).get('---f-89393', 'Unknown')}
Vendor: {props.get('custom_fields', {}).get('---f-92106', 'Unknown')}
Provider: {props.get('custom_fields', {}).get('---f-92105', 'Unknown')}
Feature: {props.get('custom_fields', {}).get('---f-97897', 'Unknown')}
Last Run Status: {props.get('run-status', 'Unknown')}
Last Run Tune: {props.get('last-run', 'Unknown')}
"""


@mcp.tool()
async def get_instances() -> str:
    """Get Test Instances from Practitest."""
    url = "https://api.practitest.com/api/v2/projects/18855/instances.json"
    data = await make_pt_request(url)

    if not data or "data" not in data:
        return "Unable to fetch instances or no instances found."

    if not data["data"]:
        return "No active instances for this project."

    instances = [format_instance(attribute) for attribute in data["data"]]
    return "\n---\n".join(instances)


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')

# from typing import Any
# import httpx
# from mcp.server.fastmcp import FastMCP
#
# # Initialize FastMCP server
# mcp = FastMCP("weather")
#
# # Constants
# NWS_API_BASE = "https://api.weather.gov"
# USER_AGENT = "weather-app/1.0"
#
# async def make_nws_request(url: str) -> dict[str, Any] | None:
#     """Make a request to the NWS API with proper error handling."""
#     headers = {
#         "User-Agent": USER_AGENT,
#         "Accept": "application/geo+json"
#     }
#     async with httpx.AsyncClient() as client:
#         try:
#             response = await client.get(url, headers=headers, timeout=30.0)
#             response.raise_for_status()
#             return response.json()
#         except Exception:
#             return None
#
# def format_alert(feature: dict) -> str:
#     """Format an alert feature into a readable string."""
#     props = feature["properties"]
#     return f"""
# Event: {props.get('event', 'Unknown')}
# Area: {props.get('areaDesc', 'Unknown')}
# Severity: {props.get('severity', 'Unknown')}
# Description: {props.get('description', 'No description available')}
# Instructions: {props.get('instruction', 'No specific instructions provided')}
# """
#
# @mcp.tool()
# async def get_alerts(state: str) -> str:
#     """Get weather alerts for a US state.
#
#     Args:
#         state: Two-letter US state code (e.g. CA, NY)
#     """
#     url = f"{NWS_API_BASE}/alerts/active/area/{state}"
#     data = await make_nws_request(url)
#
#     if not data or "features" not in data:
#         return "Unable to fetch alerts or no alerts found."
#
#     if not data["features"]:
#         return "No active alerts for this state."
#
#     alerts = [format_alert(feature) for feature in data["features"]]
#     return "\n---\n".join(alerts)
#
# @mcp.tool()
# async def get_forecast(latitude: float, longitude: float) -> str:
#     """Get weather forecast for a location.
#
#     Args:
#         latitude: Latitude of the location
#         longitude: Longitude of the location
#     """
#     # First get the forecast grid endpoint
#     points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
#     points_data = await make_nws_request(points_url)
#
#     if not points_data:
#         return "Unable to fetch forecast data for this location."
#
#     # Get the forecast URL from the points response
#     forecast_url = points_data["properties"]["forecast"]
#     forecast_data = await make_nws_request(forecast_url)
#
#     if not forecast_data:
#         return "Unable to fetch detailed forecast."
#
#     # Format the periods into a readable forecast
#     periods = forecast_data["properties"]["periods"]
#     forecasts = []
#     for period in periods[:5]:  # Only show next 5 periods
#         forecast = f"""
# {period['name']}:
# Temperature: {period['temperature']}°{period['temperatureUnit']}
# Wind: {period['windSpeed']} {period['windDirection']}
# Forecast: {period['detailedForecast']}
# """
#         forecasts.append(forecast)
#
#     return "\n---\n".join(forecasts)

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')
