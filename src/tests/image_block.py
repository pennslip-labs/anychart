"""Helpers for reading and updating image blocks on a Anytype page.

These functions model the minimal page-editing behavior used by the integration
script in this repo: validate page payloads, choose an update/insert operation,
then check whether the uploaded image is really present in the page blocks after
patching.
"""


def get_page_blocks(document: dict, expected_page_id: str) -> list[dict]:
    """Return the block list for a page after validating the page identity.

    Anytype page documents can omit the "blocks" key entirely; in that case, we
    treat the page as valid but empty rather than failing the whole edit flow.
    """
    returned_page_id = document.get("id")
    if returned_page_id != expected_page_id:
        raise ValueError(
            f"Anytype returned object {returned_page_id!r}, expected {expected_page_id!r}"
        )

    # A malformed page payload should fail early instead of creating a confusing
    # later error while applying the patch.
    blocks = document.get("blocks", [])
    if not isinstance(blocks, list):
        raise ValueError("Anytype page blocks must be a list")
    return blocks


def build_image_operation(
    blocks: list[dict], image_id: str, image_name: str
) -> tuple[dict, bool]:
    """Create the patch operation needed to ensure one image block is present.

    The function prefers updating the first existing image block rather than
    appending a second image; this keeps a page tidy and preserves the original
    block IDs when possible.
    """
    # Use the first image block we find. The tests expect this to be the one we
    # replace, even when there are multiple images already on the page.
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

    # No image block exists yet, so append a fresh one. This is the safer insert
    # path for a blank page or a page that contains only text blocks.
    return (
        {
            "op": "insert_blocks",
            "blocks": [
                {"type": "image", "object_id": image_id, "name": image_name}
            ],
        },
        False,
    )


def has_image_block(blocks: list[dict], image_id: str) -> bool:
    """Return True when the page includes the given uploaded image object id."""
    return any(
        block.get("type") == "image" and block.get("object_id") == image_id
        for block in blocks
    )
