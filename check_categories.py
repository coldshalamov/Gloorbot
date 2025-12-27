import json
import time

# Categories from main.py
categories = [
    {"name": "Clearance", "url": "https://www.lowes.com/pl/The-back-aisle/2021454685607"},
    {"name": "Lumber", "url": "https://www.lowes.com/pl/Lumber-Building-supplies/4294850532"},
    {"name": "Plywood", "url": "https://www.lowes.com/pl/Plywood-Building-supplies/4294858043"},
    {"name": "Drywall", "url": "https://www.lowes.com/pl/Drywall-Building-supplies/4294857989"},
    {"name": "Power Tools", "url": "https://www.lowes.com/pl/Power-tools-Tools/4294612503"},
    {"name": "Hand Tools", "url": "https://www.lowes.com/pl/Hand-tools-Tools/4294933958"},
    {"name": "Tool Storage", "url": "https://www.lowes.com/pl/Tool-storage-Tools/4294857963"},
    {"name": "Paint", "url": "https://www.lowes.com/pl/Paint-Paint-supplies/4294820090"},
    {"name": "Stains", "url": "https://www.lowes.com/pl/Exterior-stains-waterproofers/4294858026"},
    {"name": "Appliances", "url": "https://www.lowes.com/pl/Appliances/4294857975"},
    {"name": "Washers Dryers", "url": "https://www.lowes.com/pl/Washers-dryers-Appliances/4294857958"},
    {"name": "Refrigerators", "url": "https://www.lowes.com/pl/Refrigerators-Appliances/4294857957"},
    {"name": "Outdoor Power", "url": "https://www.lowes.com/pl/Outdoor-power-equipment-Outdoors/4294857982"},
    {"name": "Grills", "url": "https://www.lowes.com/pl/Grills-grilling-Outdoors/4294821574"},
    {"name": "Patio Furniture", "url": "https://www.lowes.com/pl/Patio-furniture-Outdoors/4294857984"},
    {"name": "Flooring", "url": "https://www.lowes.com/pl/Flooring/4294822454"},
    {"name": "Tile", "url": "https://www.lowes.com/pl/Tile-tile-accessories-Flooring/4294858017"},
    {"name": "Kitchen Faucets", "url": "https://www.lowes.com/pl/Kitchen-faucets-water-dispensers/4294857986"},
    {"name": "Bathroom Vanities", "url": "https://www.lowes.com/pl/Bathroom-vanities-Bathroom/4294819024"},
    {"name": "Lighting", "url": "https://www.lowes.com/pl/Lighting-ceiling-fans/4294857979"},
    {"name": "Electrical", "url": "https://www.lowes.com/pl/Electrical/4294630256"},
    {"name": "Fasteners", "url": "https://www.lowes.com/pl/Fasteners-Hardware/4294857976"},
    {"name": "Door Hardware", "url": "https://www.lowes.com/pl/Door-hardware-Hardware/4294858003"},
]

# Major departments from Lowes.com homepage
all_departments = {
    "Animal & Pet Care": "/c/Animal-pet-care",
    "Appliances": "/c/Appliances",
    "Automotive": "/c/Automotive",
    "Bathroom": "/c/Bathroom",
    "Blinds & Window Treatments": "/c/Window-treatments-Home-decor",
    "Building Supplies": "/c/Building-supplies",
    "Cleaning Supplies": "/c/Cleaning-supplies",
    "Doors & Windows": "/c/Windows-doors",
    "Electrical": "/c/Electrical",
    "Flooring & Rugs": "/c/Flooring",
    "Hardware": "/c/Hardware",
    "Heating & Cooling": "/c/Heating-cooling",
    "Holiday Decorations": "/c/Holiday-decorations",
    "Home Decor & Furniture": "/c/Home-decor",
    "Kitchen": "/c/Kitchen",
    "Lawn & Garden": "/c/Lawn-garden",
    "Lighting & Ceiling Fans": "/c/Lighting-ceiling-fans",
    "Moulding & Millwork": "/c/Moulding-millwork",
    "Outdoor Living & Patio": "/c/Outdoors",
    "Paint": "/c/Paint",
    "Plumbing": "/c/Plumbing",
    "Smart Home, Security & Wi-Fi": "/c/Smart-home-security-wi-fi",
    "Sports & Fitness": "/c/Sports-fitness",
    "Tools": "/c/Tools",
    "Storage & Organization": "/c/Storage-organization",
}

print("=== CATEGORY AUDIT ===\n")
print(f"Current categories: {len(categories)}")
print(f"Major departments on Lowes.com: {len(all_departments)}\n")

# Output for analysis
with open('category_analysis.json', 'w') as f:
    json.dump({
        'current_categories': categories,
        'all_departments': all_departments
    }, f, indent=2)

print("Category data saved to category_analysis.json")
