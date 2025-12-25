/**
 * Test Firefox navigating to product listing pages
 * Run with: node test_firefox_products.js
 */

const { firefox } = require('playwright');

async function test() {
  console.log('=' .repeat(60));
  console.log('FIREFOX PRODUCT LISTING TEST');
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
    // Go to paint category
    console.log('\nNavigating to Paint category...');
    await page.goto('https://www.lowes.com/c/Paint', {
      waitUntil: 'domcontentloaded',
      timeout: 60000,
    });
    await page.waitForTimeout(5000);

    const title = await page.title();
    console.log(`Page title: "${title}"`);

    // Check if blocked
    const content = await page.content();
    if (content.includes('Access Denied')) {
      console.log('\nBLOCKED BY AKAMAI!');
      await browser.close();
      return;
    }

    console.log('\nLooking for links to product listings...');

    // Find all links on the page
    const links = await page.evaluate(() => {
      const allLinks = Array.from(document.querySelectorAll('a'));
      return allLinks
        .map(a => ({ href: a.href, text: a.innerText.trim().substring(0, 50) }))
        .filter(l => l.href.includes('lowes.com/pl/') || l.href.includes('lowes.com/search'))
        .slice(0, 20);
    });

    if (links.length > 0) {
      console.log('\nFound product listing links:');
      links.slice(0, 10).forEach(l => {
        console.log(`  ${l.text || '(no text)'}: ${l.href}`);
      });

      // Try to navigate to first product listing
      const plLink = links.find(l => l.href.includes('/pl/'));
      if (plLink) {
        console.log(`\nNavigating to: ${plLink.href}`);
        await page.goto(plLink.href, {
          waitUntil: 'networkidle',
          timeout: 60000,
        });
        await page.waitForTimeout(5000);

        const plTitle = await page.title();
        console.log(`Product list page title: "${plTitle}"`);

        if (plTitle.includes('404')) {
          console.log('Got 404 on product list page');
        } else {
          // Look for products
          console.log('\nSearching for product elements...');

          const selectors = [
            'article',
            '[role="listitem"]',
            '[class*="product"]',
            '[class*="card"]',
            '[data-testid]',
            'div[class*="ProductCard"]',
            'div[class*="sc-"]',
          ];

          for (const sel of selectors) {
            const count = await page.locator(sel).count();
            if (count > 0) {
              console.log(`  ${sel}: ${count} elements`);
            }
          }

          // Get actual structure
          const structure = await page.evaluate(() => {
            // Find main content area
            const main = document.querySelector('main') || document.body;
            const elements = main.querySelectorAll('*');
            const classes = new Set();
            elements.forEach(el => {
              if (el.className && typeof el.className === 'string') {
                el.className.split(' ').forEach(c => {
                  if (c.toLowerCase().includes('product') ||
                      c.toLowerCase().includes('card') ||
                      c.toLowerCase().includes('item') ||
                      c.toLowerCase().includes('grid') ||
                      c.toLowerCase().includes('list')) {
                    classes.add(c);
                  }
                });
              }
            });
            return Array.from(classes).slice(0, 30);
          });

          if (structure.length > 0) {
            console.log('\nRelevant CSS classes found:');
            structure.forEach(c => console.log(`  .${c}`));
          }

          // Take screenshot
          await page.screenshot({ path: 'firefox_products.png' });
          console.log('\nScreenshot saved to firefox_products.png');
        }
      }
    } else {
      console.log('No product listing links found on category page');
    }

    // Also try search
    console.log('\n\nTrying search instead...');
    await page.goto('https://www.lowes.com/search?searchTerm=interior+paint', {
      waitUntil: 'networkidle',
      timeout: 60000,
    });
    await page.waitForTimeout(5000);

    const searchTitle = await page.title();
    console.log(`Search page title: "${searchTitle}"`);

    if (!searchTitle.includes('404') && !searchTitle.includes('Access Denied')) {
      // Find product count
      const productInfo = await page.evaluate(() => {
        const text = document.body.innerText;
        const match = text.match(/(\d+)\s*(?:results?|products?|items?)/i);
        return match ? match[0] : 'No count found';
      });
      console.log(`Product info: ${productInfo}`);

      // Screenshot
      await page.screenshot({ path: 'firefox_search.png' });
      console.log('Screenshot saved to firefox_search.png');
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
