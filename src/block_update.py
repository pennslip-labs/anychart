from anytype import Anytype

# This script summarizes the objects in the first Anytype space and writes the
# result into a Mermaid pie chart block on a target page. It is a quick
# dashboard helper: count per object type, render a chart, and then overwrite or
# create the Mermaid block in place.

client = Anytype()
client.auth()

# 1. Target Page ID and Space setup
# The script assumes you are updating one specific page in the first available
# Anytype space. In a real project, this is usually replaced with a config value
# or environment-driven selector instead of a hard-coded constant.
PAGE_ID = "YOUR_PAGE_ID_HERE"
space = client.get_spaces()[0]

# 2. Compute your updated dataset counts
# Anytype objects are grouped by their type so the generated chart reflects the
# current content of the space rather than a static hard-coded example.
objects = space.get_objects(limit=200)
counts = {}
for obj in objects:
    obj_type = getattr(obj, "type", "Uncategorized")
    counts[obj_type] = counts.get(obj_type, 0) + 1

# 3. Format updated Mermaid payload
# Mermaid expects a simple text payload; the generated chart is a pie chart whose
# slices correspond to object categories and counts.
mermaid_body = "pie title Updated Collection Distribution\n"
for category, count in counts.items():
    mermaid_body += f'    "{category}" : {count}\n'

# 4. Fetch the target page object
# Once the page is loaded, we can inspect the blocks list and find the chart block
# that should be replaced.
page = space.get_object(PAGE_ID)

# 5. Locate and update the target Mermaid code block
# The page can already contain a Mermaid snippet; if so, replace it in place.
# Otherwise, create a new Mermaid snippet block at the end.
updated = False
for block in page.blocks:
    if block.type == "code" and block.format.get("language") == "mermaid":
        # Overwrite the existing chart content so the page stays in sync with the
        # current Anytype inventory without creating duplicate blocks.
        block.text = mermaid_body
        page.update_block(block)
        updated = True
        print(f"Updated Mermaid block {block.id} successfully!")
        break

# Optional Fallback: If no Mermaid block exists yet on the page, append one
# This keeps the script resilient when the page was never initialized with a chart
# block, but it also means the code is not strictly idempotent across page states.
if not updated:
    page.add_codeblock(mermaid_body, language="mermaid")
    space.update_object(page)
    print("No existing Mermaid block found; appended a new one to the page.")
