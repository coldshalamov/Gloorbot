/**
 * Test Firefox with Lowe's homepage first, then navigate
 * Run with: node test_firefox_homepage.js
 */

const { firefox } = require('playwright');

async function test() {
  console.log('=' .repeat(60));
  console.log('FIREFOX HOMEPAGE TEST');
  console.log('=' .repeat(60));

  const browser = await firefox.launch({
    headless: false,
    firefoxUserPrefs: {
      'dom.webdriver.enabled': false,
    },
  });

  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    locale: 'en-US',
    timezoneId: 'America/Los_Angeles',
  });

  const page = await context.newPage();

  try {
    // Start with homepage
    console.log('\nNavigating to Lowe\'s homepage...');
    await page.goto('https://www.lowes.com', {
      waitUntil: 'domcontentloaded',
      timeout: 60000,
    });
    await page.waitForTimeout(3000);

    const homeTitle = await page.title();
    console.log(`Homepage title: "${homeTitle}"`);

    // Check if we're blocked
    const homeContent = await page.content();
    if (homeContent.includes('Access Denied')) {
      console.log('\nBLOCKED BY AKAMAI on homepage!');
      await browser.close();
      return;
    }

    console.log('Homepage loaded successfully!\n');

    // Now try to navigate to a category page - paint
    console.log('Navigating to Paint category...');

    // Try different URL patterns
    const urlsToTry = [
      'https://www.lowes.com/c/Paint-supplies',
      'https://www.lowes.com/c/Paint',
      'https://www.lowes.com/search?searchTerm=paint',
      'https://www.lowes.com/pl/Paint/4294644082',
    ];

    for (const url of urlsToTry) {
      console.log(`\nTrying: ${url}`);
      try {
        await page.goto(url, {
          waitUntil: 'domcontentloaded',
          timeout: 30000,
        });
        await page.waitForTimeout(5000);

        const title = await page.title();
        console.log(`  Title: "${title}"`);

        if (title.includes('404') || title.toLowerCase().includes('not found')) {
          console.log('  -> 404 error, trying next...');
          continue;
        }

        const content = await page.content();
        if (content.includes('Access Denied')) {
          console.log('  -> BLOCKED');
          continue;
        }

        // Try to find products
        const productSelectors = [
          '[data-test="product-pod"]',
          '[data-itemid]',
          'article',
          '[class*="ProductCard"]',
          '[class*="product"]',
        ];

        for (const sel of productSelectors) {
          const count = await page.locator(sel).count();
          if (count > 5) {
            console.log(`  -> Found ${count} elements with selector: ${sel}`);
          }
        }

        // If we get here, the URL works!
        if (!title.includes('404')) {
          console.log('\n  SUCCESS! This URL structure works.');

          // Screenshot
          await page.screenshot({ path: 'firefox_working.png' });
          console.log('  Screenshot saved to firefox_working.png');

          // Show some page text
          const bodyText = await page.evaluate(() => document.body.innerText.substring(0, 300));
          console.log('\n  Page preview:');
          console.log('  ' + bodyText.split('\n').slice(0, 5).join('\n  '));

          break;
        }
      } catch (e) {
        console.log(`  Error: ${e.message.substring(0, 50)}`);
      }
    }

    console.log('\n\nBrowser stays open for 30 seconds...');
    await page.waitForTimeout(30000);

  } catch (err) {
    console.error(`\nError: ${err.message}`);
  } finally {
    await browser.close();
  }
}

test().catch(console.error);
