"""Render a chart, save it locally, and push it to an Anytype page.

Configure ANYTYPE_API_KEY and ANYTYPE_PAGE_ID in the environment, then run
``python src/chart_push.py``. Set ANYTYPE_SPACE_ID to skip space selection.
"""

import os
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

if __package__:
    from .fetcher import choose_space, fetch_interactively, groupable_property_names
    from .image_block import build_image_operation, get_page_blocks, has_image_block
else:
    from fetcher import choose_space, fetch_interactively, groupable_property_names
    from image_block import build_image_operation, get_page_blocks, has_image_block

API_URL = os.environ.get("ANYTYPE_API_URL", "http://127.0.0.1:31012")
OUTPUT_FILENAME = "sample_chartjs.png"


def resolve_export_path(
    export_directory: str,
    downloads_directory: Path | None = None,
    filename: str = OUTPUT_FILENAME,
) -> Path:
    """Resolve the export folder, defaulting to the user's Downloads directory."""
    downloads_directory = downloads_directory or (Path.home() / "Downloads")
    export_directory = export_directory.strip()
    directory = (
        Path(export_directory).expanduser()
        if export_directory
        else downloads_directory
    )
    return (directory / filename).resolve()


def build_output_filename(
    source_name: str,
    property_name: str | None,
    created_at: datetime | None = None,
) -> str:
    """Create a filesystem-safe name describing the source, grouping, and date."""
    created_at = created_at or datetime.now()
    source_slug = _slugify(source_name)
    property_slug = _slugify(property_name or "object type")
    date_tag = created_at.strftime("%d-%m-%y")
    return f"{source_slug}_by_{property_slug}_{date_tag}.png"


def build_chart_config(
    objects: list,
    property_name: str | None = None,
    source_name: str = "Objects",
    created_at: datetime | None = None,
) -> dict:
    """Build a bar chart counting objects by property or by object type."""
    counts: Counter[str] = Counter()
    if property_name:
        for obj in objects:
            properties = getattr(obj, "properties", {})
            prop = (
                properties.get(property_name)
                if isinstance(properties, dict)
                else None
            )
            value = getattr(prop, "value", None) if prop is not None else None
            values = value if isinstance(value, (list, tuple, set)) else [value]
            for item in values:
                label = getattr(item, "name", item)
                counts[str(label) if label not in (None, "") else "Uncategorized"] += 1
        group_label = property_name
    else:
        for obj in objects:
            object_type = getattr(obj, "type", None)
            label = getattr(object_type, "name", None) or getattr(
                obj, "type_key", None
            )
            counts[str(label or "Objects")] += 1
        group_label = "object type"

    if not counts:
        raise ValueError("No chartable values were found in the fetched objects.")

    created_at = created_at or datetime.now()
    date_tag = created_at.strftime("%d-%m-%y")
    chart_title = f"{source_name} by {group_label} ({date_tag})"
    return {
        "type": "bar",
        "data": {
            "labels": list(counts),
            "datasets": [
                {
                    "label": f"Objects by {group_label}",
                    "data": list(counts.values()),
                    "backgroundColor": [
                        (
                            "#4CAF50",
                            "#2196F3",
                            "#FF9800",
                            "#9C27B0",
                            "#00ACC1",
                            "#F44336",
                        )[index % 6]
                        for index in range(len(counts))
                    ],
                    "borderRadius": 6,
                }
            ],
        },
        "options": {
            "plugins": {
                "legend": {"display": False},
                "title": {
                    "display": True,
                    "text": chart_title,
                    "font": {"size": 18},
                },
            },
            "scales": {"y": {"beginAtZero": True}},
        },
    }


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    return slug or "chart"


def choose_group_property(
    objects: list,
    input_fn=input,
    print_fn=print,
) -> str | None:
    """Ask which discovered object property should be used for chart grouping."""
    properties = groupable_property_names(objects)
    if not properties:
        print_fn("No groupable properties found; counting objects by type.")
        return None

    print_fn("Available properties to graph:")
    print_fn("  [0] Count objects by type")
    for index, name in enumerate(properties, start=1):
        print_fn(f"  [{index}] {name}")
    while True:
        answer = input_fn(f"Select a property [0-{len(properties)}]: ").strip()
        try:
            index = int(answer)
        except ValueError:
            index = -1
        if index == 0:
            return None
        if 1 <= index <= len(properties):
            return properties[index - 1]
        print_fn(f"Enter a number from 0 to {len(properties)}.")


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
    import requests
    from anytype import Anytype
    from anytype.api import API_CONFIG

    print("1. Connecting to Anytype local API...")
    API_CONFIG["apiUrl"] = f"{API_URL.rstrip('/')}/v1"
    client = Anytype()
    client.auth(persist_token=False, api_key=api_key)

    space = choose_space(client, space_id)
    print(f"   -> Using space {space.name!r} ({space.id})")
    objects, source_name = fetch_interactively(space)
    property_name = choose_group_property(objects)
    created_at = datetime.now()
    chart_config = build_chart_config(
        objects, property_name, source_name, created_at
    )
    output_filename = build_output_filename(
        source_name, property_name, created_at
    )

    default_directory = Path.home() / "Downloads"
    export_directory = input(
        f"Chart export folder [leave empty for {default_directory}]: "
    )
    output_path = resolve_export_path(
        export_directory, default_directory, output_filename
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    api_headers = {"Authorization": f"Bearer {api_key}"}
    page_url = f"{API_URL.rstrip('/')}/v2/spaces/{space.id}/objects/{page_id}"
    print("2. Retrieving target page blocks...")
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

    print("3. Rendering Chart.js PNG via QuickChart...")
    render_response = requests.post(
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
    render_response.raise_for_status()
    output_path.write_bytes(render_response.content)
    print(f"   -> Saved chart export: {output_path}")

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
