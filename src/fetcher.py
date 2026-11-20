"""Interactive data-source selection and object retrieval for Anytype spaces."""

from collections.abc import Callable
from typing import Any


PAGE_SIZE = 100
MAX_OBJECTS = 500
QUERY_TYPE_KEYS = {"collection", "set"}


def choose_space(
    client: Any,
    space_id: str | None = None,
    input_fn: Callable[[str], str] = input,
    print_fn: Callable[[str], None] = print,
) -> Any:
    """Return a configured space or interactively select an accessible space."""
    spaces = client.get_spaces(limit=MAX_OBJECTS)
    if not spaces:
        raise RuntimeError(
            "The bot can access no spaces. Invite its account to the target space, then retry."
        )

    if space_id:
        selected = next((space for space in spaces if space.id == space_id), None)
        if selected is None:
            available_spaces = ", ".join(
                f"{space.name!r} ({space.id})" for space in spaces
            )
            raise RuntimeError(
                f"Space {space_id!r} is not accessible to this bot. "
                f"Visible spaces: {available_spaces}. Invite the bot to the target space."
            )
        return selected

    return _choose_item("space", spaces, input_fn, print_fn)


def fetch_interactively(
    space: Any,
    input_fn: Callable[[str], str] = input,
    print_fn: Callable[[str], None] = print,
) -> tuple[list[Any], str]:
    """Ask whether to fetch a saved query/collection or a type table."""
    while True:
        choice = input_fn("Fetch from [q]uery/collection or [t]ype? ").strip().lower()
        if choice in {"q", "query", "collection"}:
            objects, source_name = _fetch_query_interactively(
                space, input_fn, print_fn
            )
            break
        if choice in {"t", "type"}:
            types = space.get_types(limit=MAX_OBJECTS)
            if not types:
                raise RuntimeError("The selected space has no object types.")
            selected_type = _choose_item("type", types, input_fn, print_fn)
            objects = fetch_by_type(space, selected_type)
            source_name = f"type {selected_type.name!r}"
            break
        print_fn("Enter 'q' for a query/collection or 't' for a type.")

    if not objects:
        raise RuntimeError(f"No objects were returned from {source_name}.")
    print_fn(f"Fetched {len(objects)} objects from {source_name}.")
    return objects, source_name


def fetch_by_type(space: Any, object_type: Any, limit: int = MAX_OBJECTS) -> list[Any]:
    """Fetch objects matching an Anytype type key, up to ``limit`` objects."""
    type_key = getattr(object_type, "key", "")
    if not type_key:
        raise ValueError(f"Type {getattr(object_type, 'name', object_type)!r} has no key.")
    return _fetch_pages(
        lambda offset, page_limit: space.get_objects(
            offset=offset,
            limit=page_limit,
            filters={"type": type_key},
        ),
        limit,
    )


def groupable_property_names(objects: list[Any]) -> list[str]:
    """List property names available for grouping across fetched objects."""
    names: list[str] = []
    seen: set[str] = set()
    for obj in objects:
        properties = getattr(obj, "properties", {})
        if not isinstance(properties, dict):
            continue
        for name, prop in properties.items():
            if getattr(prop, "format", "") not in {
                "checkbox",
                "date",
                "multi_select",
                "number",
                "select",
                "text",
            }:
                continue
            if name not in seen:
                names.append(name)
                seen.add(name)
    return names


def _fetch_query_interactively(
    space: Any,
    input_fn: Callable[[str], str],
    print_fn: Callable[[str], None],
) -> tuple[list[Any], str]:
    sources = _query_sources(space)
    print_fn("Available queries and collections:")
    for index, source in enumerate(sources, start=1):
        print_fn(f"  [{index}] {source.name} ({source.id})")
    print_fn(f"  [{len(sources) + 1}] Enter a query/collection ID")

    selected_index = _read_index(
        f"Select a query/collection [1-{len(sources) + 1}]: ",
        len(sources) + 1,
        input_fn,
        print_fn,
    )
    if selected_index == len(sources):
        query_id = input_fn("Query/collection ID: ").strip()
        if not query_id:
            raise ValueError("A query/collection ID is required.")
        source_name = f"query/collection {query_id!r}"
    else:
        source = sources[selected_index]
        query_id = source.id
        source_name = f"query/collection {source.name!r}"

    views = space.get_listviews(query_id)
    if not views:
        raise RuntimeError(f"No views were found for {source_name}.")
    selected_view = _choose_item("view", views, input_fn, print_fn)
    objects = _fetch_pages(
        lambda offset, limit: selected_view.get_objectsinlistview(
            offset=offset, limit=limit
        ),
        MAX_OBJECTS,
    )
    return objects, source_name


def _query_sources(space: Any) -> list[Any]:
    objects = _fetch_pages(
        lambda offset, limit: space.get_objects(offset=offset, limit=limit),
        MAX_OBJECTS,
    )
    return [
        obj
        for obj in objects
        if _type_key(obj) in QUERY_TYPE_KEYS
        or str(getattr(obj, "layout", "")).lower() in QUERY_TYPE_KEYS
    ]


def _type_key(obj: Any) -> str:
    type_key = getattr(obj, "type_key", "")
    if not type_key:
        type_key = getattr(getattr(obj, "type", None), "key", "")
    return str(type_key).lower()


def _choose_item(
    label: str,
    items: list[Any],
    input_fn: Callable[[str], str],
    print_fn: Callable[[str], None],
) -> Any:
    if len(items) == 1:
        item = items[0]
        print_fn(f"Using the only available {label}: {item.name}.")
        return item
    print_fn(f"Available {label}s:")
    for index, item in enumerate(items, start=1):
        print_fn(f"  [{index}] {item.name} ({item.id})")
    return items[
        _read_index(
            f"Select a {label} [1-{len(items)}]: ",
            len(items),
            input_fn,
            print_fn,
        )
    ]


def _read_index(
    prompt: str,
    item_count: int,
    input_fn: Callable[[str], str],
    print_fn: Callable[[str], None],
) -> int:
    while True:
        answer = input_fn(prompt).strip()
        try:
            index = int(answer) - 1
        except ValueError:
            index = -1
        if 0 <= index < item_count:
            return index
        print_fn(f"Enter a number from 1 to {item_count}.")


def _fetch_pages(fetch_page: Callable[[int, int], list[Any]], limit: int) -> list[Any]:
    objects: list[Any] = []
    for offset in range(0, limit, PAGE_SIZE):
        page_limit = min(PAGE_SIZE, limit - offset)
        page = fetch_page(offset, page_limit)
        objects.extend(page)
        if len(page) < page_limit:
            break
    return objects
