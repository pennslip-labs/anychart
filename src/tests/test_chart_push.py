import os
import requests
from anytype import Anytype
from anytype.api import API_CONFIG
from image_block import build_image_operation, get_page_blocks, has_image_block

# This integration script renders a chart image, uploads it to Anytype, then
# patches the target page so the file appears as an image block. The script
# intentionally fails early if required configuration is missing.

PAGE_ID = os.environ.get("ANYTYPE_PAGE_ID")
SPACE_ID = os.environ.get("ANYTYPE_SPACE_ID")
API_KEY = os.environ.get("ANYTYPE_API_KEY")
API_URL = os.environ.get("ANYTYPE_API_URL", "http://127.0.0.1:31012")
OUTPUT_PNG = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "sample_chartjs.png")
)

# QuickChart uses this config to generate a simple sample bar chart for the page
# test. It stays small and deterministic so the upload workflow is easy to reason
# about.
chart_config = {
    "type": "bar",
    "data": {
        "labels": ["Done", "In Progress", "To Do"],
        "datasets": [
            {
                "label": "Sample Tasks",
                "data": [14, 32, 44],
                "backgroundColor": ["#4CAF50", "#2196F3", "#FF9800"],
                "borderRadius": 6,
            }
        ],
    },
    "options": {
        "plugins": {
            "legend": {"display": False},
            "title": {
                "display": True,
                "text": "Anytype Test Chart (Chart.js via QuickChart)",
                "font": {"size": 18},
            },
        },
        "scales": {"y": {"beginAtZero": True}},
    },
}

if not API_KEY:
    raise RuntimeError("Set the ANYTYPE_API_KEY environment variable before running this test.")
if not PAGE_ID:
    raise RuntimeError("Set the ANYTYPE_PAGE_ID environment variable before running this test.")

# Reuse a local PNG when available so the script does not need to call the chart
# renderer every time the end-to-end flow is run.
if os.path.isfile(OUTPUT_PNG):
    print(f"1. Using existing chart image: {OUTPUT_PNG}")
else:
    print("1. Rendering Chart.js PNG via QuickChart...")
    response = requests.post(
        "https://quickchart.io/chart",
        json={
            "chart": chart_config,
            "width": 800,
            "height": 450,
            "devicePixelRatio": 2,
            "backgroundColor": "white",
        },
        timeout=15,
    )
    response.raise_for_status()

    with open(OUTPUT_PNG, "wb") as image_file:
        image_file.write(response.content)
    print(f"   -> Saved local test image: {OUTPUT_PNG}")

# Phase 2: authenticate and resolve the target space. The script intentionally
# requires a specific space id so it cannot accidentally update the wrong page.
print("2. Connecting to Anytype local API...")
API_CONFIG["apiUrl"] = f"{API_URL.rstrip('/')}/v1"
client = Anytype()
client.auth(persist_token=False, api_key=API_KEY)

spaces = client.get_spaces()
if not spaces:
    raise RuntimeError(
        "The bot can access no spaces. Invite its account to the target space, then retry."
    )

if not SPACE_ID:
    available_spaces = ", ".join(f"{space.name!r} ({space.id})" for space in spaces)
    raise RuntimeError(
        "Set ANYTYPE_SPACE_ID to the ID of the space containing the target page. "
        f"Spaces currently visible to this bot: {available_spaces}"
    )

space = next((space for space in spaces if space.id == SPACE_ID), None)
if space is None:
    available_spaces = ", ".join(f"{space.name!r} ({space.id})" for space in spaces)
    raise RuntimeError(
        f"Space {SPACE_ID!r} is not accessible to this bot. "
        f"Visible spaces: {available_spaces}. Invite the bot to the target space."
    )

api_headers = {"Authorization": f"Bearer {API_KEY}"}
# The actual token is intentionally hidden in these comments because this file is
# more about the workflow than credential handling.
page_url = f"{API_URL.rstrip('/')}/v2/spaces/{SPACE_ID}/objects/{PAGE_ID}"
print("3. Retrieving target page blocks through the Anytype v2 API...")
page_response = requests.get(page_url, headers=api_headers, timeout=15)
if not page_response.ok:
    raise RuntimeError(
        f"Could not retrieve page {PAGE_ID!r} through the Anytype v2 API "
        f"(HTTP {page_response.status_code}): {page_response.text}"
    )
page_document = page_response.json()
try:
    blocks = get_page_blocks(page_document, PAGE_ID)
except ValueError as error:
    raise RuntimeError(
        f"Could not read blocks for page {PAGE_ID!r}: {error}. "
        f"Response keys: {sorted(page_document)}"
    ) from error

# Phase 4: upload the static chart image to Anytype and capture its file object
# id so the page patch can point to the exact uploaded asset.
print("4. Uploading PNG to Anytype space...")
uploaded_file = space.upload_file(OUTPUT_PNG)
file_id = uploaded_file.get("object_id") or uploaded_file.get("id")
if not file_id:
    raise RuntimeError(
        f"Unexpected upload response; expected a file object ID, got keys: {sorted(uploaded_file)}"
    )

operation, replaced_image = build_image_operation(
    blocks, file_id, os.path.basename(OUTPUT_PNG)
)
patch_headers = api_headers.copy()
etag = page_response.headers.get("ETag") or page_document.get("etag")
if etag:
    # ETag check prevents a stale page write from clobbering newer content.
    patch_headers["If-Match"] = etag

update_response = requests.patch(
    page_url,
    headers=patch_headers,
    json={"ops": [operation]},
    timeout=15,
)
if not update_response.ok:
    raise RuntimeError(
        f"Could not update page {PAGE_ID!r} through the Anytype v2 API "
        f"(HTTP {update_response.status_code}): {update_response.text}"
    )

# Verify the patch by re-reading the page and checking that the file id actually
# appears in the final block list.
verification_response = requests.get(page_url, headers=api_headers, timeout=15)
if not verification_response.ok:
    raise RuntimeError(
        f"Could not verify page {PAGE_ID!r} through the Anytype v2 API "
        f"(HTTP {verification_response.status_code}): {verification_response.text}"
    )
verification_document = verification_response.json()
try:
    verification_blocks = get_page_blocks(verification_document, PAGE_ID)
except ValueError as error:
    raise RuntimeError(
        f"Could not verify blocks for page {PAGE_ID!r}: {error}. "
        f"Response keys: {sorted(verification_document)}"
    ) from error
if not has_image_block(verification_blocks, file_id):
    raise RuntimeError(
        f"Anytype accepted the update, but the uploaded image {file_id!r} "
        f"is not present on page {PAGE_ID!r}."
    )

if replaced_image:
    print("   -> Replaced the first image block on the target page!")
else:
    print("   -> No existing image block found; created a new one.")

print("Done! Check your test page on Anytype Desktop and Mobile.")
