import sys
import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.chart_push import (
    OUTPUT_FILENAME,
    build_chart_config,
    build_output_filename,
    choose_group_property,
    resolve_export_path,
)


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

    def test_dynamic_filename_includes_source_property_and_creation_date(self):
        created_at = datetime(2026, 11, 20, 10, 17)

        filename = build_output_filename(
            "Query / Collection: Sprint Tasks",
            "Status / Type",
            created_at,
        )

        self.assertEqual(
            filename, "query_collection_sprint_tasks_by_status_type_20-11-26.png"
        )


class DynamicChartTests(unittest.TestCase):
    def test_chart_counts_values_from_selected_property(self):
        objects = [
            SimpleObject({"Status": SimpleProperty("select", "Done")}),
            SimpleObject({"Status": SimpleProperty("select", "Done")}),
            SimpleObject({"Status": SimpleProperty("select", "To Do")}),
        ]

        chart = build_chart_config(objects, "Status")

        self.assertEqual(chart["data"]["labels"], ["Done", "To Do"])
        self.assertEqual(chart["data"]["datasets"][0]["data"], [2, 1])
        self.assertEqual(chart["data"]["datasets"][0]["label"], "Objects by Status")

    def test_chart_title_includes_source_property_and_creation_date(self):
        objects = [SimpleObject({"Status": SimpleProperty("select", "Done")})]

        chart = build_chart_config(
            objects,
            "Status",
            "type 'Task'",
            datetime(2026, 11, 20, 10, 17),
        )

        self.assertEqual(
            chart["options"]["plugins"]["title"]["text"],
            "type 'Task' by Status (20-11-26)",
        )

    def test_chart_counts_each_value_of_multi_select_property(self):
        objects = [
            SimpleObject(
                {"Tags": SimpleProperty("multi_select", ["Work", "Urgent"])}
            ),
            SimpleObject({"Tags": SimpleProperty("multi_select", ["Work"])}),
        ]

        chart = build_chart_config(objects, "Tags")

        self.assertEqual(chart["data"]["labels"], ["Work", "Urgent"])
        self.assertEqual(chart["data"]["datasets"][0]["data"], [2, 1])

    def test_chart_can_count_objects_by_type(self):
        objects = [
            SimpleObject({}, object_type=SimpleNamespace(name="Task")),
            SimpleObject({}, object_type=SimpleNamespace(name="Note")),
            SimpleObject({}, object_type=SimpleNamespace(name="Task")),
        ]

        chart = build_chart_config(objects)

        self.assertEqual(chart["data"]["labels"], ["Task", "Note"])
        self.assertEqual(chart["data"]["datasets"][0]["data"], [2, 1])

    def test_property_selection_can_choose_type_count_fallback(self):
        objects = [SimpleObject({"Status": SimpleProperty("select", "Done")})]

        result = choose_group_property(
            objects, input_fn=lambda _: "0", print_fn=lambda _: None
        )

        self.assertIsNone(result)


class SimpleProperty:
    def __init__(self, value_format, value):
        self.format = value_format
        self.value = value


class SimpleObject:
    def __init__(self, properties, object_type=None, type_key="task"):
        self.properties = properties
        self.type = object_type
        self.type_key = type_key


if __name__ == "__main__":
    unittest.main()
