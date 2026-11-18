"""Render a chart, save it locally, and push it to an Anytype page.

Configure ANYTYPE_API_KEY, ANYTYPE_SPACE_ID, and ANYTYPE_PAGE_ID in the
environment, then run ``python src/chart_push.py``.
"""

import os
from pathlib import Path

if __package__:
    from .image_block import build_image_operation, get_page_blocks, has_image_block
else:
    from image_block import build_image_operation, get_page_blocks, has_image_block

API_URL = os.environ.get("ANYTYPE_API_URL", "http://127.0.0.1:31012")
OUTPUT_FILENAME = "sample_chartjs.png"

CHART_CONFIG = {
    "type": "bar",
    "data": {
        "labels": ["Done", "In Progress", "To Do"],
        "datasets": [
            {
                "label": "Sample Tasks",
                "data": [95, 32, 44],
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


def resolve_export_path(
    export_directory: str, downloads_directory: Path | None = None
) -> Path:
    """Resolve the export folder, defaulting to the user's Downloads directory."""
    downloads_directory = downloads_directory or (Path.home() / "Downloads")
    export_directory = export_directory.strip()
    directory = (
        Path(export_directory).expanduser()
        if export_directory
        else downloads_directory
    )
    return (directory / OUTPUT_FILENAME).resolve()


def main() -> None:
    api_key = os.environ.get("ANYTYPE_API_KEY")
    page_id = os.environ.get("ANYTYPE_PAGE_ID")
    space_id = os.environ.get("ANYTYPE_SPACE_ID")
    if not api_key:
        raise RuntimeError(
            "Set the ANYTYPE_API_KEY environment variable before running this script."
        )
    if not page_id:
        raise RuntimeError(
            "Set the ANYTYPE_PAGE_ID environment variable before running this script."
        )
    if not space_id:
        raise RuntimeError(
            "Set the ANYTYPE_SPACE_ID environment variable before running this script."
        )

    default_directory = Path.home() / "Downloads"
    export_directory = input(
        f"Chart export folder [leave empty for {default_directory}]: "
    )
    output_path = resolve_export_path(export_directory, default_directory)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    import requests
    from anytype import Anytype
    from anytype.api import API_CONFIG

    print("1. Rendering Chart.js PNG via QuickChart...")
    render_response = requests.post(
        "https://quickchart.io/chart",
        json={
            "chart": CHART_CONFIG,
            "width": 800,
            "height": 450,
            "devicePixelRatio": 2,
            "backgroundColor": "white",
        },
        timeout=15,
    )
    render_response.raise_for_status()
    output_path.write_bytes(render_response.content)
    print(f"   -> Saved chart export: {output_path}")

    print("2. Connecting to Anytype local API...")
    API_CONFIG["apiUrl"] = f"{API_URL.rstrip('/')}/v1"
    client = Anytype()
    client.auth(persist_token=False, api_key=api_key)

    spaces = client.get_spaces()
    if not spaces:
        raise RuntimeError(
            "The bot can access no spaces. Invite its account to the target space, then retry."
        )
    space = next((candidate for candidate in spaces if candidate.id == space_id), None)
    if space is None:
        available_spaces = ", ".join(
            f"{candidate.name!r} ({candidate.id})" for candidate in spaces
        )
        raise RuntimeError(
            f"Space {space_id!r} is not accessible to this bot. "
            f"Visible spaces: {available_spaces}. Invite the bot to the target space."
        )

    api_headers = {"Authorization": f"Bearer {api_key}"}
    page_url = f"{API_URL.rstrip('/')}/v2/spaces/{space_id}/objects/{page_id}"
    print("3. Retrieving target page blocks...")
    page_response = requests.get(page_url, headers=api_headers, timeout=15)
    if not page_response.ok:
        raise RuntimeError(
            f"Could not retrieve page {page_id!r} through the Anytype v2 API "
            f"(HTTP {page_response.status_code}): {page_response.text}"
        )
    page_document = page_response.json()
    try:
        blocks = get_page_blocks(page_document, page_id)
    except ValueError as error:
        raise RuntimeError(
            f"Could not read blocks for page {page_id!r}: {error}. "
            f"Response keys: {sorted(page_document)}"
        ) from error

    print("4. Uploading chart to Anytype...")
    uploaded_file = space.upload_file(str(output_path))
    file_id = uploaded_file.get("object_id") or uploaded_file.get("id")
    if not file_id:
        raise RuntimeError(
            "Unexpected upload response; expected a file object ID, "
            f"got keys: {sorted(uploaded_file)}"
        )

    operation, replaced_image = build_image_operation(
        blocks, file_id, output_path.name
    )
    patch_headers = api_headers.copy()
    etag = page_response.headers.get("ETag") or page_document.get("etag")
    if etag:
        patch_headers["If-Match"] = etag

    update_response = requests.patch(
        page_url,
        headers=patch_headers,
        json={"ops": [operation]},
        timeout=15,
    )
    if not update_response.ok:
        raise RuntimeError(
            f"Could not update page {page_id!r} through the Anytype v2 API "
            f"(HTTP {update_response.status_code}): {update_response.text}"
        )

    verify_response = requests.get(page_url, headers=api_headers, timeout=15)
    if not verify_response.ok:
        raise RuntimeError(
            f"Could not verify page {page_id!r} through the Anytype v2 API "
            f"(HTTP {verify_response.status_code}): {verify_response.text}"
        )
    try:
        verified_blocks = get_page_blocks(verify_response.json(), page_id)
    except ValueError as error:
        raise RuntimeError(
            f"Could not verify blocks for page {page_id!r}: {error}"
        ) from error
    if not has_image_block(verified_blocks, file_id):
        raise RuntimeError(
            f"Anytype accepted the update, but uploaded image {file_id!r} "
            f"is not present on page {page_id!r}."
        )

    if replaced_image:
        print("   -> Replaced the first image block on the target page.")
    else:
        print("   -> Added a new image block to the target page.")
    print("Done! Check your page in Anytype.")


if __name__ == "__main__":
    main()
