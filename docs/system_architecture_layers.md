# System Architecture & Layer Specifications

`anychart` is designed around a decoupled, four-stage data pipeline. Separating **data retrieval**, **data modeling**, **chart rendering/pushing**, and **user interfaces** ensures that the exact same core logic powers both interactive terminal sessions and unattended background cron jobs.

---

## End-to-End Component Architecture

```mermaid
flowchart TD
    subgraph Interfaces["Layer 3: User Interfaces (Planned)"]
        REPL["shell.py\nInteractive cmd.Cmd REPL"]
        CLI["cli.py\nOne-Shot & Recipe Runner"]
        Recipe[("recipes/*.json\nSaved Chart Configs")]
        REPL -->|save-recipe| Recipe
        Recipe -->|load| CLI
    end

    subgraph Fetch["Layer 1: Fetcher (Implemented)"]
        Client["Anytype Client Wrapper\n(Unscoped /v1 Auth)"]
        QFetch["Query / Collection Reader\nspace.get_listviews()"]
        TFetch["Dynamic Type Filter\nspace.get_objects()"]
        Schema["Schema Inspector\ninspect_properties()"]
        Client --> QFetch
        Client --> TFetch
        QFetch --> Schema
        TFetch --> Schema
    end

    subgraph Model["Layer 2: Modeler (Planned)"]
        Norm["Property Normalizer\n(Select, Multi-Select, Date, Number)"]
        Agg["Aggregation Engine\n(Count, Sum, Avg, Time Bucket)"]
        Sort["Sorter & Top-N Limiter"]
        Norm --> Agg --> Sort
    end

    subgraph Push["Completed: Renderer & Pusher"]
        Builder["Chart.js Config Builder"]
        Quick["QuickChart API Renderer"]
        Play["Offline Playwright Renderer\n(Optional Local Chromium)"]
        Uploader["Anytype File Uploader\nspace.upload_file()"]
        Swapper["In-Place Block Updater\nblock.target_object_id"]
        Builder --> Quick
        Builder -.-> Play
        Quick --> Uploader --> Swapper
        Play -.-> Uploader
    end

    REPL --> Fetch
    CLI --> Fetch
    Schema -->|Raw Objects| Norm
    Sort -->|"{labels, values}"| Builder
```

---

## Completed Foundation: Chart Renderer & In-Place Pusher

**Current Location:** `src/chart_push.py` with data retrieval in `src/fetcher.py`.

The bottom of the pipeline is built and verified:
1. **Data-Driven Chart.js Payload Construction:** Counts fetched objects by a selected property or object type and builds a standard Chart.js configuration dictionary (`type`, `data.labels`, `data.datasets`, `options`).
2. **High-DPI PNG Rendering:**
   * **Primary (`QuickChart`):** POSTs the Chart.js JSON payload to `https://quickchart.io/chart` at `devicePixelRatio: 2` (`800x450` logical pixels $\rightarrow$ `1600x900` crisp output).
   * **Offline Alternative (`Playwright`):** Renders an HTML `<canvas>` loading local `chart.umd.min.js` in headless Chromium and screenshots `#c` to PNG with zero external network calls.
3. **Vault Upload & In-Place Block Replacement:**
   * Uploads the rendered PNG into the target Anytype space via `space.upload_file(png_path)`.
   * Iterates over `page.blocks` on the target `PAGE_ID` to locate an existing `image` block (`getattr(block, "type", None) == "image"`).
   * Updates `block.target_object_id = uploaded_file.id` and commits via `page.update_block(block)` (falling back to `page.add_image(uploaded_file)` if the page has no Image block yet).

> **Multi-Chart Dashboard Scaling:** When extending dashboards to hold multiple charts on a single page, target specific blocks by matching `block.id` from a recipe mapping rather than overwriting the first `image` block encountered.

---

## Layer 1: Fetching & Source Selection (`fetcher.py`) — *Implemented*

The fetcher is shared by the chart-push script and scopes every read to the selected Anytype space. `ANYTYPE_SPACE_ID` can select that space non-interactively; otherwise the script prompts when multiple spaces are accessible. It supports two data sources:

### 1. Query / Collection Retrieval

The script lists discovered Sets and Collections, allows entering an ID when one is not listed, and selects a view before reading its objects through `get_listviews()` and `get_objectsinlistview()`.

### 2. Type Table Retrieval

For ad-hoc selection, the script lists the space's object types and fetches matching objects with `space.get_objects(filters={"type": type_key})`. Both strategies retrieve in pages, up to 500 objects per run.

After fetching, the chart-push script offers discovered object properties for a count-by-property chart; choosing the fallback counts objects by type. Numeric aggregation and time bucketing remain part of the planned Modeler layer.

---

## Layer 2: Case-by-Case Modeler (`modeler.py`) — *Roadmap Step 2*

The modeler decouples Anytype's raw object structures from Chart.js dataset formatting:

* **Property Normalization:** Safely extracts values whether stored as direct object attributes (`getattr(obj, key)`) or inside `obj.properties[key]`. Unwraps `Select` / tag objects via `.name`, expands `Multi-select` lists across multiple buckets, and maps `None` values to a configurable fallback (e.g., `"Uncategorized"`).
* **Aggregation Modes:**
  * `count`: Frequency count per category (`group_by`).
  * `sum`: Total of a numeric `value_field` grouped by `group_by` (e.g., expenses summed by category).
  * `avg`: Mean of a numeric `value_field` grouped by `group_by`.
  * `timeseries`: Buckets `Date` properties by day, week, or month.
* **Standardized Output Contract:**
  ```python
  {
      "labels": ["Done", "In Progress", "To Do"],
      "values": [18, 9, 15],
      "meta": {"mode": "count", "group_by": "status", "total_objects": 42}
  }
  ```

---

## Layer 3: Interactive Shell & Recipe CLI (`shell.py` & `cli.py`) — *Roadmap Step 3*

To make case-by-case data modeling intuitive without sacrificing background automation, Layer 3 provides two entry points over the same core modules:

1. **Interactive REPL (`shell.py` via `cmd.Cmd`):**
   * Maintains session state (`current_space`, `loaded_objects`, `modeled_data`, `chart_config`).
   * Commands: `spaces`, `use <space>`, `types`, `fetch`, `props`, `model`, `chart`, `preview`, `push <page_id>`, and `save-recipe <path>`.
2. **Non-Interactive CLI (`cli.py`):**
   * Executes saved JSON recipes (`anychart run recipes/sprint_tasks.json`) for hands-free updates via `cron` or systemd timers.