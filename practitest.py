import sys
from os import environ

import httpx
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("practitest")

# Constants
NWS_API_BASE = "https://api.practitest.gov"
API_TOKEN = environ.get("PT_API_TOKEN", "your_api_token_here")  # Replace with your actual token


async def make_pt_request(endpoint: str, params: dict = None) -> dict | None:
    """Make a request to PractiTest API and return parsed JSON."""
    headers = {
        "Content-Type": "application/json",
        "PTToken": API_TOKEN
    }
    url = f'https://api.practitest.com/api/v2/projects/18855/{endpoint}'
    if params:
        url += '?' + '&'.join(f"{key}={value}" for key, value in params.items())
    print(f"\nMaking request to URL: {url}", file=sys.stderr)
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
            return None


def format_instance(instance: dict) -> str:
    """Format the instance data into a readable string."""
    instance_id = instance['id']
    attrs = instance["attributes"]
    full_test_name = attrs.get('name', 'Unknown')
    short_test_name = full_test_name.rsplit('[')[0] if '[' in attrs.get('name', 'Unknown') else 'Unknown'
    test_owner = attrs.get('custom-fields', {}).get('---f-194433', 'Unknown')
    environment = attrs.get('custom-fields', {}).get('---f-89393', 'Unknown')
    vendor = attrs.get('custom-fields', {}).get('---f-92106', 'Unknown')
    provider = attrs.get('custom-fields', {}).get('---f-92105', 'Unknown')
    feature = attrs.get('custom-fields', {}).get('---f-97897', 'Unknown')
    last_run_status = attrs.get('run-status', 'Unknown')
    last_run_time = attrs.get('last-run', 'Unknown')

    # print(f"\nParsing instance with attributes: {attrs}", file=sys.stderr)
    parsed_instances = f"""
    Automation Instance Test Summary:
    - Instance ID: {instance_id}
    - Full Test Name: {full_test_name}
    - Short Test Name: {short_test_name}
    - Assigned To: {test_owner[:-1]}
    - Environment: {environment}
    - Vendor: {vendor}
    - Provider: {provider}
    - Feature: {feature}
    - Last Run Status: {last_run_status}
    - Last Run Time: {last_run_time}
    """
    # print(f"\nParsed instance:\n{parsed_instances}", file=sys.stderr)
    return parsed_instances


def format_run(run: dict) -> str:
    """Format the run data into a readable string."""
    attributes = run.get("attributes", {})
    status = attributes.get("status")
    created_at = attributes.get("created-at")
    custom_fields = attributes.get("custom-fields", {})
    jenkins_html = custom_fields.get("---f-102643", "")
    jenkins_link = (
                jenkins_html.split('href="')[1].split('"')[0]
                if jenkins_html
                and 'href="' in jenkins_html
                else None
    )

    parsed_instances = f"""
    Test run {status.lower()} at {created_at}, link to job at: {jenkins_link}
    """
    # print(f"\nParsed instance:\n{parsed_instances}", file=sys.stderr)
    return parsed_instances

@mcp.tool()
async def get_instances() -> str:
    """Get Test Instances from Practitest, with basic information per each instance,
    such as assigned user, environment, vendor, provider, feature, last run status,
    and last run time etc.
    """
    # print("Fetching instances from Practitest...", file=sys.stderr)
    endpoint = "instances.json"
    data = await make_pt_request(endpoint)

    if not data or "data" not in data:
        return "Unable to fetch instances or no instances found."

    if not data["data"]:
        return "No active instances for this project."

    instances = [format_instance(instance) for instance in data["data"]]
    return "\n---\n".join(instances)

@mcp.tool()
async def get_instance_runs(instance_id: str) -> str:
    """Get Test run of a specific instance from Practitest, with basic information per each run,
    such as status, created at, link to Jenkins job etc.
    In order to get the instance ID, you can use the get_instances() method first.

    Args:
        instance_id (str): The ID of the instance to fetch runs for (e.g. "111523018").
    """
    endpoint = f"runs.json"
    params = {"instance-ids": instance_id}
    data = await make_pt_request(endpoint, params)

    if not data or "data" not in data:
        return "Unable to fetch runs or no runs found."

    if not data["data"]:
        return "No active runs for this instance."

    runs = [format_run(run) for run in data["data"]]
    return "\n---\n".join(runs)




if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')
