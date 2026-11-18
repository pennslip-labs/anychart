import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.chart_push import OUTPUT_FILENAME, resolve_export_path


class ExportPathTests(unittest.TestCase):
    def test_empty_input_defaults_to_downloads_folder(self):
        home = Path("/home/test-user")
        downloads = home / "Downloads"

        with patch("src.chart_push.Path.home", return_value=home):
            result = resolve_export_path("  ")

        self.assertEqual(result, downloads / OUTPUT_FILENAME)

    def test_custom_export_folder_is_expanded_and_receives_chart_filename(self):
        with TemporaryDirectory() as temporary_directory:
            result = resolve_export_path(temporary_directory)

            self.assertEqual(
                result, Path(temporary_directory).resolve() / OUTPUT_FILENAME
            )


if __name__ == "__main__":
    unittest.main()
