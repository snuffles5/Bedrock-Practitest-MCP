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

