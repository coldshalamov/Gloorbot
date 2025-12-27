"""
Quick HTML inspection to understand Lowe's product page structure
"""
import requests
from bs4 import BeautifulSoup

# Test a known category URL
url = "https://www.lowes.com/pl/Power-tools-Tools/4294612503"

print(f"Fetching: {url}\n")

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

response = requests.get(url, headers=headers, timeout=10)
print(f"Status: {response.status_code}\n")

if response.status_code == 200:
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Check for various product selectors
    selectors_to_try = [
        ('data-test="product-pod"', '[data-test="product-pod"]'),
        ('data-test="productPod"', '[data-test="productPod"]'),
        ('class contains "product"', '[class*="product"]'),
        ('class contains "ProductCard"', '[class*="ProductCard"]'),
        ('class contains "Grid"', '[class*="Grid"]'),
    ]
    
    print("Testing product selectors:")
    print("="*60)
    
    for desc, selector in selectors_to_try:
        elements = soup.select(selector)
        print(f"{desc}: {len(elements)} found")
        if elements and len(elements) > 0:
            print(f"  First element: {elements[0].name} {elements[0].get('class', [])[:3]}")
    
    print("\n" + "="*60)
    print("Searching for 'Pickup' or 'Get It Today' text:")
    print("="*60)
    
    pickup_text = soup.find_all(string=lambda text: text and ('pickup' in text.lower() or 'get it today' in text.lower()))
    print(f"Found {len(pickup_text)} instances of pickup-related text")
    if pickup_text:
        for i, text in enumerate(pickup_text[:5]):
            print(f"  {i+1}. {text.strip()[:60]}")
    
    print("\n" + "="*60)
    print("Looking for product grid/list containers:")
    print("="*60)
    
    # Common container patterns
    containers = [
        soup.find('div', {'id': 'products'}),
        soup.find('div', {'class': lambda x: x and 'product-list' in str(x).lower()}),
        soup.find('div', {'class': lambda x: x and 'grid' in str(x).lower()}),
    ]
    
    for i, container in enumerate(containers):
        if container:
            print(f"Container {i+1} found: {container.name} with classes {container.get('class', [])[:3]}")
    
    # Save a snippet for manual inspection
    with open("lowes_page_sample.html", "w", encoding="utf-8") as f:
        f.write(response.text[:50000])  # First 50KB
    
    print("\n✅ Saved first 50KB of HTML to: lowes_page_sample.html")
    print("You can inspect this file to see the actual page structure")

else:
    print(f"❌ Failed to fetch page: {response.status_code}")
