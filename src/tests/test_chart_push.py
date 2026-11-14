import os
import requests
from anytype import Anytype

# ==========================================
# 1. CONFIGURATION
# ==========================================
PAGE_ID = "YOUR_PAGE_ID_HERE"  # Paste the ID from "Copy Link"
OUTPUT_PNG = "sample_chartjs.png"

# ==========================================
# 2. RENDER SAMPLE CHART.JS IMAGE
# ==========================================
chart_config = {
    "type": "bar",
    "data": {
        "labels": ["Done", "In Progress", "To Do"],
        "datasets": [
            {
                "label": "Sample Tasks",
                "data": [14, 6, 10],
                "backgroundColor": ["#4CAF50", "#2196F3", "#FF9800"],
                "borderRadius": 6,
            }
        ],
    },
    "options": {
        "plugins": {
            "legend": {"display": False},
            "title": {
                "display": True,
                "text": "Anytype Test Chart (Chart.js via QuickChart)",
                "font": {"size": 18},
            },
        },
        "scales": {"y": {"beginAtZero": True}},
    },
}

print("1. Rendering Chart.js PNG via QuickChart...")
res = requests.post(
    "https://quickchart.io/chart",
    json={
        "chart": chart_config,
        "width": 800,
        "height": 450,
        "devicePixelRatio": 2,
        "backgroundColor": "white",
    },
    timeout=15,
)
res.raise_for_status()

with open(OUTPUT_PNG, "wb") as f:
    f.write(res.content)
print(f"   -> Saved local test image: {os.path.abspath(OUTPUT_PNG)}")

# ==========================================
# 3. PUSH TO ANYTYPE VIA ANYTYPE-CLIENT
# ==========================================
print("2. Connecting to Anytype local API...")
client = Anytype()
client.auth()  # Uses saved token or prompts for 4-digit desktop code[cite: 3]

space = client.get_spaces()[0]  #[cite: 3]
page = space.get_object(PAGE_ID)  #[cite: 3]

print("3. Uploading PNG to Anytype space...")
uploaded_file = space.upload_file(OUTPUT_PNG)

# Attempt to overwrite the first existing image block on the page
updated = False
for block in page.blocks:  #[cite: 3]
    if getattr(block, "type", None) == "image":
        block.target_object_id = uploaded_file.id
        page.update_block(block)  #[cite: 3]
        updated = True
        print(f"   -> Replaced existing Image block ({block.id}) in place!")
        break

# Fallback: append a new image block if the page had none yet
if not updated:
    page.add_image(uploaded_file)
    space.update_object(page)  #[cite: 3]
    print("   -> No existing Image block found; appended a new Image block!")

print("Done! Check your test page on Anytype Desktop and Mobile.")
