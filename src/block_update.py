from anytype import Anytype

client = Anytype()
client.auth()

# 1. Target Page ID and Space setup
PAGE_ID = "YOUR_PAGE_ID_HERE"
space = client.get_spaces()[0]

# 2. Compute your updated dataset counts
objects = space.get_objects(limit=200)
counts = {}
for obj in objects:
    obj_type = getattr(obj, "type", "Uncategorized")
    counts[obj_type] = counts.get(obj_type, 0) + 1

# 3. Format updated Mermaid payload
mermaid_body = "pie title Updated Collection Distribution\n"
for category, count in counts.items():
    mermaid_body += f'    "{category}" : {count}\n'

# 4. Fetch the target page object
page = space.get_object(PAGE_ID)

# 5. Locate and update the target Mermaid code block
# (Iterate through page blocks to find the code block marked for mermaid)
updated = False
for block in page.blocks:
    if block.type == "code" and block.format.get("language") == "mermaid":
        # Overwrite text content on the existing block
        block.text = mermaid_body
        page.update_block(block)
        updated = True
        print(f"Updated Mermaid block {block.id} successfully!")
        break

# Optional Fallback: If no Mermaid block exists yet on the page, append one
if not updated:
    page.add_codeblock(mermaid_body, language="mermaid")
    space.update_object(page)
    print("No existing Mermaid block found; appended a new one to the page.")
