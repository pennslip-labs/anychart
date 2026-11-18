"""Helpers for reading and updating image blocks on an Anytype page."""


def get_page_blocks(document: dict, expected_page_id: str) -> list[dict]:
    """Return a page's blocks after validating the page identity."""
    returned_page_id = document.get("id")
    if returned_page_id != expected_page_id:
        raise ValueError(
            f"Anytype returned object {returned_page_id!r}, expected {expected_page_id!r}"
        )

    blocks = document.get("blocks", [])
    if not isinstance(blocks, list):
        raise ValueError("Anytype page blocks must be a list")
    return blocks


def build_image_operation(
    blocks: list[dict], image_id: str, image_name: str
) -> tuple[dict, bool]:
    """Build an update or insert operation for the page's first image block."""
    existing_image = next(
        (
            block
            for block in blocks
            if block.get("type") == "image" and block.get("id")
        ),
        None,
    )
    if existing_image:
        return (
            {
                "op": "update_block",
                "id": existing_image["id"],
                "set": {"object_id": image_id, "name": image_name},
            },
            True,
        )

    return (
        {
            "op": "insert_blocks",
            "blocks": [{"type": "image", "object_id": image_id, "name": image_name}],
        },
        False,
    )


def has_image_block(blocks: list[dict], image_id: str) -> bool:
    """Return whether the page includes the given uploaded image object ID."""
    return any(
        block.get("type") == "image" and block.get("object_id") == image_id
        for block in blocks
    )
