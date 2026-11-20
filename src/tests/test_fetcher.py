import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.fetcher import choose_space, fetch_by_type, fetch_interactively


class FetcherTests(unittest.TestCase):
    def test_configured_space_is_selected_without_prompting(self):
        target_space = SimpleNamespace(id="space-1", name="Personal")
        client = Mock()
        client.get_spaces.return_value = [target_space]

        result = choose_space(client, "space-1", input_fn=Mock())

        self.assertIs(result, target_space)

    def test_space_selection_prompts_when_multiple_spaces_are_available(self):
        spaces = [
            SimpleNamespace(id="space-1", name="Personal"),
            SimpleNamespace(id="space-2", name="Work"),
        ]
        client = Mock()
        client.get_spaces.return_value = spaces

        result = choose_space(client, input_fn=lambda _: "2", print_fn=lambda _: None)

        self.assertIs(result, spaces[1])

    def test_fetch_type_uses_selected_type_key(self):
        objects = [SimpleNamespace(name="Task")]
        space = Mock()
        space.get_objects.return_value = objects
        object_type = SimpleNamespace(key="task", name="Task")

        result = fetch_by_type(space, object_type)

        self.assertEqual(result, objects)
        space.get_objects.assert_called_once_with(
            offset=0, limit=100, filters={"type": "task"}
        )

    def test_interactive_type_selection_fetches_matching_objects(self):
        objects = [SimpleNamespace(name="Task 1")]
        object_type = SimpleNamespace(id="type-1", key="task", name="Task")
        space = Mock()
        space.get_types.return_value = [object_type]
        space.get_objects.return_value = objects
        answers = iter(("t",))

        result, source = fetch_interactively(
            space, input_fn=lambda _: next(answers), print_fn=lambda _: None
        )

        self.assertEqual(result, objects)
        self.assertEqual(source, "type 'Task'")
        space.get_types.assert_called_once_with(limit=500)
        space.get_objects.assert_called_once_with(
            offset=0, limit=100, filters={"type": "task"}
        )

    def test_interactive_query_fetches_selected_view_objects(self):
        fetched_objects = [SimpleNamespace(name="Task 1"), SimpleNamespace(name="Task 2")]
        view = SimpleNamespace(
            id="view-1",
            name="All tasks",
            get_objectsinlistview=Mock(return_value=fetched_objects),
        )
        query = SimpleNamespace(
            id="query-1",
            name="Sprint tasks",
            type_key="set",
            layout="",
        )
        space = Mock()
        space.get_objects.return_value = [query]
        space.get_listviews.return_value = [view]
        answers = iter(("q", "1"))

        result, source = fetch_interactively(
            space, input_fn=lambda _: next(answers), print_fn=lambda _: None
        )

        self.assertEqual(result, fetched_objects)
        self.assertEqual(source, "query/collection 'Sprint tasks'")
        space.get_listviews.assert_called_once_with("query-1")
        view.get_objectsinlistview.assert_called_once_with(offset=0, limit=100)

    def test_query_source_can_be_entered_when_none_are_discovered(self):
        view = SimpleNamespace(
            id="view-1",
            name="Default",
            get_objectsinlistview=Mock(return_value=[SimpleNamespace(name="Item")]),
        )
        space = Mock()
        space.get_objects.return_value = []
        space.get_listviews.return_value = [view]
        answers = iter(("q", "1", "query-id"))

        objects, source = fetch_interactively(
            space, input_fn=lambda _: next(answers), print_fn=lambda _: None
        )

        self.assertEqual(len(objects), 1)
        self.assertEqual(source, "query/collection 'query-id'")
        space.get_listviews.assert_called_once_with("query-id")


if __name__ == "__main__":
    unittest.main()
