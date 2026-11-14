import unittest

from image_block import build_image_operation, get_page_blocks, has_image_block

# These tests lock in the expected behavior for the page-block helper functions.
# They are intentionally small and direct, because the real Anytype API calls are
# managed separately in the integration script.


class ImageBlockOperationTests(unittest.TestCase):
    def test_reads_an_omitted_block_list_as_an_empty_page(self):
        # A page document may legitimately omit "blocks" when it is empty or the
        # response is partial; we treat that as an empty list, not a failure.
        self.assertEqual(
            get_page_blocks({"id": "page-id", "type": "page"}, "page-id"), []
        )

    def test_rejects_a_document_for_a_different_page_id(self):
        # Defensive check: if the server responds with a different page, we should
        # not trust that block list or patch it against the wrong document.
        with self.assertRaisesRegex(ValueError, "expected 'page-id'"):
            get_page_blocks({"id": "another-page-id"}, "page-id")

    def test_rejects_a_malformed_block_list(self):
        # The page payload shape is part of the contract; a None block list is not
        # a valid Anytype page structure and should be rejected early.
        with self.assertRaisesRegex(ValueError, "blocks must be a list"):
            get_page_blocks({"id": "page-id", "blocks": None}, "page-id")

    def test_replaces_first_image_block_in_place(self):
        # The helper is designed to keep the existing image block and update it in
        # place rather than duplicating a second image on the page.
        blocks = [
            {"id": "text-id", "type": "paragraph", "text": "Keep me"},
            {"id": "image-id", "type": "image", "object_id": "old-image"},
            {"id": "another-image-id", "type": "image", "object_id": "other-image"},
        ]

        operation, replaced = build_image_operation(blocks, "new-image", "chart.png")

        self.assertTrue(replaced)
        self.assertEqual(
            operation,
            {
                "op": "update_block",
                "id": "image-id",
                "set": {"object_id": "new-image", "name": "chart.png"},
            },
        )

    def test_inserts_an_image_block_when_page_has_none(self):
        # If the page contains no image blocks, we create the new image block by
        # inserting a fresh block rather than trying to mutate nothing.
        operation, replaced = build_image_operation(
            [{"id": "text-id", "type": "paragraph"}], "new-image", "chart.png"
        )

        self.assertFalse(replaced)
        self.assertEqual(
            operation,
            {
                "op": "insert_blocks",
                "blocks": [
                    {"type": "image", "object_id": "new-image", "name": "chart.png"}
                ],
            },
        )

    def test_detects_the_uploaded_image_by_file_object_id(self):
        # The verification step checks for the uploaded file/object ID, not just the
        # block type, so it can confirm the exact image is present after patching.
        blocks = [{"type": "image", "object_id": "new-image"}]

        self.assertTrue(has_image_block(blocks, "new-image"))
        self.assertFalse(has_image_block(blocks, "different-image"))


if __name__ == "__main__":
    unittest.main()
