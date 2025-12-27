"""
Lowe's Minimal Catalog Link Discovery

Goal:
1. Find the minimal set of links (/pl/) required to cover the entire catalog.
2. Start at /c/Departments.
3. Ignore top-level department links (headers).
4. For /c/ hubs:
   - Prefer "Shop All" /pl/ links.
   - Click "Show More" if it might reveal "Shop All" or more relevant links.
   - If no "Shop All", pick ONE "Shop by..." partition (e.g., Type) and collect /pl/ links.
   - Avoid redundant partitions (Brand, Size, etc.).
5. Use anti-blocking patterns from PARALLEL/scraper.py.
"""

import asyncio
import random
import re
import json
from pathlib import Path
from datetime import datetime
from collections import deque
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright, Page, BrowserContext

# ============================================================================
# CONFIG
# ============================================================================

BASE_URL = "https://www.lowes.com"
START_URL = "https://www.lowes.com/c/Departments"
OUTPUT_FILE = "minimal_catalog_links.txt"
CHECKPOINT_FILE = "discovery_checkpoint.json"

# ============================================================================
# UTILS
# ============================================================================

def norm_url(url: str) -> str:
    if not url: return ""
    if url.startswith("//"): url = "https:" + url
    elif url.startswith("/"): url = BASE_URL + url
    
    # Remove query params except useful ones? Actually, for /pl/ links, params might matter.
    # But usually we want the clean URL.
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

def is_pl(url: str) -> bool:
    return "/pl/" in url

def is_c(url: str) -> bool:
    return "/c/" in url

# ============================================================================
# HUMAN BEHAVIOR (from PARALLEL/scraper.py)
# ============================================================================

async def human_mouse_move(page: Page):
    viewport = page.viewport_size
    width = viewport.get('width', 1440) if viewport else 1440
    height = viewport.get('height', 900) if viewport else 900
    start_x = random.random() * width * 0.3
    start_y = random.random() * height * 0.3
    end_x = width * 0.4 + random.random() * width * 0.4
    end_y = height * 0.4 + random.random() * height * 0.4
    steps = 10 + int(random.random() * 10)
    for i in range(steps + 1):
        progress = i / steps
        eased = 2 * progress * progress if progress < 0.5 else 1 - pow(-2 * progress + 2, 2) / 2
        x = start_x + (end_x - start_x) * eased + (random.random() - 0.5) * 3
        y = start_y + (end_y - start_y) * eased + (random.random() - 0.5) * 3
        await page.mouse.move(x, y)
        await asyncio.sleep(random.uniform(0.01, 0.03))

async def human_scroll(page: Page):
    scroll_amount = 150 + int(random.random() * 200)
    steps = 4 + int(random.random() * 4)
    step_amount = scroll_amount / steps
    for _ in range(steps):
        await page.mouse.wheel(0, step_amount)
        await asyncio.sleep(random.uniform(0.05, 0.15))

async def warmup_session(page: Page):
    print("Warming up session...")
    await page.goto(BASE_URL, wait_until='domcontentloaded', timeout=60000)
    await asyncio.sleep(3)
    await human_mouse_move(page)
    await human_scroll(page)
    await asyncio.sleep(1.5)
    print("Warmup complete")

# ============================================================================
# DISCOVERY LOGIC
# ============================================================================

async def get_departments_sublinks(page: Page):
    """
    On /c/Departments, find the subcategory links under the main headers.
    Skip the headers (a:has(h2)).
    """
    print("Extracting sublinks from Departments page...")
    
    # Heuristic: headers are in cards, sublinks are in lists/flex rows within or after them.
    # The browser subagent identified a.styles__LinkWrapper-RC__sc-b79nda-4 as subcategory links.
    # We can also just get all links and filter out the ones that contain <h2>.
    
    all_links = await page.eval_on_selector_all("a[href]", """
        links => links.map(a => ({
            href: a.getAttribute('href'),
            text: a.innerText.trim(),
            isHeader: a.querySelector('h1, h2, h3') !== null
        }))
    """)
    
    sublinks = []
    for link in all_links:
        href = link['href']
        if not href: continue
        if link['isHeader']: continue # Skip top-level department headers
        
        # Also skip breadcrumbs or common header links if needed, 
        # but usually /c/ or /pl/ links in the main content are what we want.
        url = norm_url(href)
        if (is_c(url) or is_pl(url)) and url != START_URL:
            if url not in [s['url'] for s in sublinks]:
                sublinks.append({"url": url, "text": link['text']})
                
    print(f"Found {len(sublinks)} sublinks on Departments page.")
    return sublinks

async def handle_c_hub(page: Page, url: str):
    """
    Visit a /c/ hub and decide which links to take.
    """
    print(f"Processing hub: {url}")
    try:
        await page.goto(url, wait_until='domcontentloaded', timeout=60000)
    except Exception as e:
        print(f"Failed to load {url}: {e}")
        return [], []

    await asyncio.sleep(2)
    await human_scroll(page)
    
    # Check for blocking
    title = await page.title()
    if "Access Denied" in title or "Robot" in title:
        print(f"BLOCKED on {url}")
        return None, None # Signal block

    # 1. Look for "Shop All" link
    # Sometimes it's a button, sometimes a link.
    shop_all_pl = await page.eval_on_selector_all("a", """
        links => links
            .filter(a => a.innerText.toLowerCase().includes('shop all'))
            .map(a => a.getAttribute('href'))
            .filter(h => h && h.includes('/pl/'))
    """)
    if shop_all_pl:
        target = norm_url(shop_all_pl[0])
        print(f"  Found Shop All: {target}")
        return [target], [] # Found leaf, no more /c/ recursion needed for this branch

    # 2. Click "Show More" if present to reveal more sections
    try:
        show_more = page.locator("button:has-text('Show More'), .show-more-button").first
        if await show_more.is_visible():
            print("  Clicking 'Show More'...")
            await show_more.click()
            await asyncio.sleep(1)
    except:
        pass

    # 3. Look for "Shop by" sections
    # We want ONE partition (Type, Style, etc.)
    # We avoid Brand, Size, Color as they are redundant.
    
    partitions = await page.evaluate("""
        () => {
            const headings = Array.from(document.querySelectorAll('h1, h2, h3, h4, p'))
                .filter(el => el.innerText.toLowerCase().includes('shop by'));
            
            return headings.map(h => {
                const headingText = h.innerText.trim();
                // Find nearest container with links
                let container = h.parentElement;
                let links = [];
                for (let i = 0; i < 3; i++) {
                    if (!container) break;
                    links = Array.from(container.querySelectorAll('a[href]'))
                        .map(a => ({ href: a.getAttribute('href'), text: a.innerText.trim() }));
                    if (links.length > 2) break;
                    container = container.parentElement;
                }
                return { heading: headingText, links };
            });
        }
    """)
    
    preferred_keywords = ['type', 'style', 'category', 'item']
    redundant_keywords = ['brand', 'size', 'width', 'color', 'rating', 'price']
    
    chosen_pl = []
    chosen_c = []
    
    # Try to find the best partition
    best_partition = None
    for p in partitions:
        heading = p['heading'].lower()
        if any(k in heading for k in preferred_keywords):
            best_partition = p
            break
            
    if not best_partition and partitions:
        # If no "preferred", check if it's "redundant". If not, take the first one.
        for p in partitions:
            heading = p['heading'].lower()
            if not any(k in heading for k in redundant_keywords):
                best_partition = p
                break
    
    if best_partition:
        print(f"  Selected partition: {best_partition['heading']}")
        for link in best_partition['links']:
            u = norm_url(link['href'])
            if is_pl(u):
                if u not in chosen_pl: chosen_pl.append(u)
            elif is_c(u):
                if u not in chosen_c: chosen_c.append(u)
        return chosen_pl, chosen_c

    # 4. If no partition found, look for ANY relevant links in the main content
    print("  No 'Shop All' or 'Shop by' partition found. Falling back to all /c/ or /pl/ links in page.")
    # This might be redundant, but we need to cover the ground.
    all_page_links = await page.eval_on_selector_all("main a[href]", """
        links => links.map(a => a.getAttribute('href'))
    """)
    for href in all_page_links:
        u = norm_url(href)
        if "/pl/" in u and u not in chosen_pl: chosen_pl.append(u)
        elif "/c/" in u and u not in chosen_c: chosen_c.append(u)
        
    return chosen_pl, chosen_c

# ============================================================================
# MAIN ORCHESTRATOR
# ============================================================================

async def run_discovery():
    async with async_playwright() as p:
        # Browser setup
        profile_dir = Path(".playwright-profiles/discovery-minimal")
        profile_dir.mkdir(parents=True, exist_ok=True)
        
        launch_kwargs = {
            "headless": False,
            "channel": "chrome",
            "viewport": {"width": 1440, "height": 900},
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-infobars",
            ]
        }
        
        context = await p.chromium.launch_persistent_context(str(profile_dir), **launch_kwargs)
        page = context.pages[0] if context.pages else await context.new_page()
        
        try:
            await warmup_session(page)
            
            # State
            pending_c = deque()
            visited_c = set()
            found_pl = set()
            
            # Load checkpoint if exists
            if Path(CHECKPOINT_FILE).exists():
                with open(CHECKPOINT_FILE, 'r') as f:
                    data = json.load(f)
                    pending_c = deque(data.get('pending_c', []))
                    visited_c = set(data.get('visited_c', []))
                    found_pl = set(data.get('found_pl', []))
                print(f"Resumed from checkpoint: {len(pending_c)} pending, {len(visited_c)} visited, {len(found_pl)} PLs")
            else:
                # 1. Start at Departments
                await page.goto(START_URL, wait_until='domcontentloaded')
                await asyncio.sleep(2)
                sublinks = await get_departments_sublinks(page)
                for item in sublinks:
                    url = item['url']
                    if is_c(url): pending_c.append(url)
                    elif is_pl(url): found_pl.add(url)
            
            # 2. Process Queue
            count = 0
            while pending_c:
                url = pending_c.popleft()
                if url in visited_c: continue
                visited_c.add(url)
                
                pls, cs = await handle_c_hub(page, url)
                
                if pls is None: # Blocked
                    print("Anti-bot triggered. Waiting 30s...")
                    await asyncio.sleep(30)
                    await warmup_session(page)
                    pending_c.appendleft(url) # Retry
                    visited_c.remove(url)
                    continue
                
                for u in pls: found_pl.add(u)
                for u in cs:
                    if u not in visited_c:
                        pending_c.append(u)
                
                count += 1
                if count % 10 == 0:
                    # Save checkpoint
                    checkpoint = {
                        "pending_c": list(pending_c),
                        "visited_c": list(visited_c),
                        "found_pl": list(found_pl),
                        "timestamp": datetime.now().isoformat()
                    }
                    with open(CHECKPOINT_FILE, 'w') as f:
                        json.dump(checkpoint, f, indent=2)
                    
                    # Also save current results to OUTPUT_FILE as plain text for easy viewing
                    with open(OUTPUT_FILE, 'w') as f:
                        f.write(f"# Discovered Minimal PL Links - {datetime.now().isoformat()}\n")
                        for u in sorted(list(found_pl)):
                            f.write(u + "\n")
                    
                    print(f"--- Checkpoint: {len(visited_c)} visited, {len(found_pl)} PLs found ---")

                # Human-like delay between hubs
                await asyncio.sleep(random.uniform(1.5, 3.0))

            print("Discovery complete!")
            print(f"Total PL links found: {len(found_pl)}")

        finally:
            await context.close()

if __name__ == "__main__":
    asyncio.run(run_discovery())
