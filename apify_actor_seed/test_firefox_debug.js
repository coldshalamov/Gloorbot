/**
 * Test Firefox with better debugging to find product selectors
 * Run with: node test_firefox_debug.js
 */

const { firefox } = require('playwright');

const TEST_URL = 'https://www.lowes.com/pl/Paint/4294644082';

async function test() {
  console.log('=' .repeat(60));
  console.log('FIREFOX DEBUG TEST');
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

  console.log(`\nNavigating to ${TEST_URL}...`);

  try {
    const response = await page.goto(TEST_URL, {
      waitUntil: 'networkidle',  // Wait for network to be idle
      timeout: 90000,
    });

    console.log(`Response status: ${response.status()}`);

    // Wait extra time for JS to render
    console.log('Waiting 10 seconds for JS rendering...');
    await page.waitForTimeout(10000);

    const title = await page.title();
    console.log(`Page title: "${title}"`);

    // Check for Akamai block
    const content = await page.content();
    if (content.includes('Access Denied')) {
      console.log('\nBLOCKED BY AKAMAI!');
      await browser.close();
      return;
    }

    console.log('\nSearching for products with various selectors...\n');

    // Try various product selectors
    const selectors = [
      '[data-test="product-pod"]',
      '[data-itemid]',
      '.product-card',
      '.plp-card',
      '[class*="ProductCard"]',
      '[class*="product-card"]',
      '[class*="product"]',
      'article',
      '[data-productid]',
      'div[data-sku]',
      '.sc-product-card',
      '[data-testid*="product"]',
    ];

    for (const selector of selectors) {
      try {
        const count = await page.locator(selector).count();
        if (count > 0) {
          console.log(`  ${selector}: ${count} elements`);
        }
      } catch (e) {
        // ignore
      }
    }

    // Check what's actually on the page
    console.log('\n\nLooking at page structure...');

    // Get all article/div elements with data attributes
    const elements = await page.evaluate(() => {
      const items = [];
      // Look for anything that looks like a product container
      document.querySelectorAll('div, article, li').forEach(el => {
        const attrs = el.getAttributeNames().filter(a =>
          a.includes('data-') || a.includes('product') || a.includes('item')
        );
        if (attrs.length > 0) {
          const classes = el.className ? el.className.split(' ').slice(0, 3).join(' ') : '';
          if (classes.toLowerCase().includes('product') ||
              classes.toLowerCase().includes('card') ||
              classes.toLowerCase().includes('item') ||
              attrs.some(a => a.includes('product') || a.includes('item'))) {
            items.push({
              tag: el.tagName.toLowerCase(),
              classes: classes.substring(0, 50),
              attrs: attrs.join(', ').substring(0, 50),
            });
          }
        }
      });
      return items.slice(0, 20); // First 20
    });

    if (elements.length > 0) {
      console.log('\nFound elements that might be products:');
      elements.forEach(el => {
        console.log(`  <${el.tag}> classes="${el.classes}" attrs="${el.attrs}"`);
      });
    } else {
      console.log('No product-like elements found!');
    }

    // Check if page shows any visible text about products
    const bodyText = await page.evaluate(() => document.body.innerText.substring(0, 500));
    console.log('\n\nFirst 500 chars of page text:');
    console.log(bodyText);

    // Take a screenshot
    await page.screenshot({ path: 'firefox_debug.png', fullPage: false });
    console.log('\n\nScreenshot saved to firefox_debug.png');

    console.log('\nBrowser stays open for 60 seconds for inspection...');
    await page.waitForTimeout(60000);

  } catch (err) {
    console.error(`\nError: ${err.message}`);
  } finally {
    await browser.close();
  }
}

test().catch(console.error);
