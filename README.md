# anychart

**Automated, cross-platform data visualization charts for Anytype.**

`anychart` queries your local Anytype vault, models object properties on a case-by-case basis, renders high-DPI **Chart.js** graphs (bar, pie, doughnut, line), and updates native **Image blocks** in-place on your Anytype pages—syncing seamlessly across both **Anytype Desktop** and **Anytype Mobile**.

---

## Why `anychart` Exists (The Pitch)

Anytype is built around a **local-first, end-to-end encrypted (E2EE)** architecture. While this guarantees privacy and data ownership, it also means Anytype does not support third-party cloud plugins or browser-style extensions, and native database analytics remain limited:

1. **No Native Collection Analytics Charts:** Anytype's built-in *Graph View* visualizes node-link relationships between objects rather than quantitative bar or pie charts. Grid views only offer basic column footer totals, and Kanban boards only group by a single Select property.
2. **Broken & Desktop-Only `/chart` Embeds:** Anytype's experimental `/chart` embed block is **not supported on Anytype Mobile** (displaying an *"unsupported block"* placeholder) and frequently renders as a blank white canvas on Desktop builds.
3. **Mermaid Limitations:** While `/mermaid` blocks render across Desktop and Mobile, Mermaid lacks universal native bar chart support—forcing awkward Gantt-chart workarounds for basic category counts.
4. **Page Clutter from Manual Exports:** Exporting CSVs to external spreadsheets or generating new Anytype pages on every script run breaks live dashboard workflows.

### How `anychart` Solves This

Instead of relying on fragile embed blocks or external cloud dashboards, `anychart` treats **native Anytype Image blocks** as dynamic chart canvases:

* **True Chart.js Fidelity:** Renders crisp bar, pie, line, and doughnut charts locally or via QuickChart.
* **100% Desktop & Mobile Parity:** Standard Image blocks live inside your encrypted Anytype vault and render natively on macOS, Windows, Linux, iOS, and Android.
* **In-Place Updates:** Locates an existing Image block on a target dashboard page and swaps its file reference (`target_object_id`) in-place—updating your charts with zero duplicate blocks or broken links.
* **Interactive + Automated:** Designed to support both an interactive REPL shell for ad-hoc exploration and saved JSON recipes for hands-free background updates via `anytype serve`.

---

## High-Level Pipeline

```mermaid
flowchart LR
    subgraph Anytype["Local Anytype Vault (:31012 / :31009)"]
        DB[(Spaces, Types & Queries)]
        Page[Target Dashboard Page\nImage Block]
    end

    subgraph Anychart["anychart Pipeline"]
        Fetch["1. Fetcher Layer\n(Query & Schema Discovery)"]
        Model["2. Modeler Layer\n(Group, Count, Sum, Avg)"]
        Render["3. Renderer & Pusher\n(Chart.js PNG + In-Place Swap)"]
        UI["4. Interface Layer\n(Interactive REPL & CLI Recipes)"]
    end

    DB -->|anytype-client| Fetch
    Fetch -->|Raw Objects| Model
    Model -->|Normalized Series| Render
    Render -->|Upload & Replace Block| Page
    UI -.->|Controls| Fetch
    UI -.->|Configures| Model
    UI -.->|Triggers| Render
```

---

## Project Status & Roadmap

| Layer / Component | Module | Status | Description |
| :--- | :--- | :--- | :--- |
| **Chart Renderer & Pusher** | `src/tests/test_chart_push.py` *(to be extracted to `pusher.py`)* | **Working** | Renders Chart.js configs to high-DPI PNGs, authenticates via unscoped `/v1` API key, uploads to space, and replaces existing Image blocks in-place. |
| **Layer 1: Fetcher** | `src/anychart/fetcher.py` | **Next Up** | Wraps client auth, pulls objects from existing Anytype Queries/Collections or Type filters, and inspects available object property schemas. |
| **Layer 2: Modeler** | `src/anychart/modeler.py` | **Planned** | Shapes raw Anytype objects on a case-by-case basis (`count`, `sum`, `avg`, `group_by`, time bucketing) into standardized Chart.js datasets. |
| **Layer 3: Shell & CLI** | `src/anychart/shell.py` & `cli.py` | **Planned** | Interactive `cmd.Cmd` REPL for live querying/modeling, plus `save-recipe` / `run` commands for cron-scheduled automation. |

---

## Repository Structure

```text
anychart/
├── README.md                    # Project overview, pitch, status, and quickstart
├── docs/
│   ├── ARCHITECTURE.md          # Detailed 4-stage pipeline and layer specifications
│   ├── SETUP_AND_BOT.md         # Headless daemon, bot account invite, and /v1 API auth guide
│   └── WORKFLOWS.md             # Working push example, REPL transcript, and cron recipes
├── src/
│   ├── anychart/                # Core package (fetcher, modeler, pusher, shell, cli)
│   └── tests/
│       └── test_chart_push.py   # Verified end-to-end Chart.js render & block-swap test
└── .gitignore                   # Excludes __pycache__/, .env, and temporary *.png outputs
```

---

## Quickstart

### Prerequisites

* Python 3.10+
* `anytype-client` (`charlesneimog/anytype-client`) and `requests`
* Either **Anytype Desktop** running locally (`http://127.0.0.1:31009`) or the headless **Anytype CLI** daemon (`anytype serve` on `http://127.0.0.1:31012`)

### Installation

```bash
git clone https://github.com/pennslip-labs/anychart.git
cd anychart
pip install anytype-client requests
```

### Run the Verified Chart Push Test

1. Set your target space, dashboard page ID, and unscoped `/v1` API key (see [`docs/SETUP_AND_BOT.md`](docs/SETUP_AND_BOT.md) for instructions):

```bash
export ANYTYPE_API_URL="http://127.0.0.1:31012"
export ANYTYPE_API_KEY="your_unscoped_v1_api_key"
```

2. Execute the push test script to render a sample Chart.js bar graph and replace the Image block on your target page:

```bash
python3 src/tests/test_chart_push.py
```

---

## Documentation

* **[Setup & Bot Authentication (`docs/SETUP_AND_BOT.md`)](docs/SETUP_AND_BOT.md):** How to run `anytype serve`, create and invite a dedicated `anychart-bot` account, generate unscoped `/v1` API keys, and handle `anytype-client` authentication quirks.
* **[System Architecture (`docs/ARCHITECTURE.md`)](docs/ARCHITECTURE.md):** Architectural breakdown of the completed push utility and the upcoming Fetcher, Modeler, and Shell/CLI layers.
* **[Workflows & Examples (`docs/WORKFLOWS.md`)](docs/WORKFLOWS.md):** Code examples for the current push pipeline, planned interactive shell sessions, and automated recipe execution.
