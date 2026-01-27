import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto("https://www.lowes.com/store/FL-Lake-Park/1720", wait_until="domcontentloaded")
        await asyncio.sleep(3)
        
        print("Looking for buttons...")
        
        # Check "My Store"
        try:
            my_store = page.locator("button:has-text('My Store')")
            count = await my_store.count()
            visible = await my_store.first.is_visible() if count > 0 else False
            print(f"'My Store' button: count={count}, visible={visible}")
        except Exception as e:
            print(f"'My Store' button error: {e}")
        
        # Check "Set Store"
        try:
            set_store = page.locator("button:has-text('Set Store')")
            count = await set_store.count()
            visible = await set_store.first.is_visible() if count > 0 else False
            print(f"'Set Store' button: count={count}, visible={visible}")
        except Exception as e:
            print(f"'Set Store' button error: {e}")
        
        # Check "Set as My Store"
        try:
            set_as = page.locator("button:has-text('Set as My Store')")
            count = await set_as.count()
            visible = await set_as.first.is_visible() if count > 0 else False
            print(f"'Set as My Store' button: count={count}, visible={visible}")
        except Exception as e:
            print(f"'Set as My Store' button error: {e}")
        
        # Get all button text
        all_buttons = await page.locator("button").all()
        print(f"\nAll buttons on page ({len(all_buttons)} total):")
        for btn in all_buttons[:20]:  # First 20
            try:
                text = await btn.inner_text()
                if "store" in text.lower() or "my" in text.lower():
                    print(f"  - {text[:50]}")
            except:
                pass
        
        input("Press Enter to close...")
        await browser.close()

asyncio.run(test())
