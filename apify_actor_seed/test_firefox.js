/**
 * Test Akamai bypass with Firefox - docs recommend Firefox over Chrome!
 * "We recommend Playwright with Firefox because it is not that common for scraping"
 * Run with: node test_firefox.js
 */

const { firefox } = require('playwright');
const { newInjectedContext } = require('fingerprint-injector');

const TEST_URL = 'https://www.lowes.com/pl/Paint/4294644082';

async function test() {
  console.log('=' .repeat(60));
  console.log('AKAMAI BYPASS TEST - FIREFOX');
  console.log('=' .repeat(60));
  console.log('\nWhy Firefox? Apify docs say:');
  console.log('"We recommend Playwright with Firefox because it is not');
  console.log(' that common for scraping"');
  console.log(`\nTarget URL: ${TEST_URL}`);
  console.log('\nLaunching Firefox...');

  const browser = await firefox.launch({
    headless: false, // CRITICAL: Akamai blocks headless
    args: [
      '--width=1440',
      '--height=900',
    ],
  });

  console.log('Creating injected context with fingerprint-injector...');

  // fingerprint-injector works with Firefox too
  const context = await newInjectedContext(browser, {
    fingerprintOptions: {
      devices: ['desktop'],
      operatingSystems: ['windows', 'macos', 'linux'],
      browsers: [{ name: 'firefox', minVersion: 120 }],
    },
  });

  const page = await context.newPage();

  console.log(`\nNavigating to ${TEST_URL}...`);

  try {
    const response = await page.goto(TEST_URL, {
      waitUntil: 'domcontentloaded',
      timeout: 60000,
    });

    // Wait for content to render
    await page.waitForTimeout(5000);

    const title = await page.title();
    const url = page.url();
    const status = response ? response.status() : 'N/A';

    console.log(`\nResponse status: ${status}`);
    console.log(`Page title: ${title}`);
    console.log(`Final URL: ${url}`);

    // Check for blocks
    let blocked = false;
    const blockReasons = [];

    if (status === 403) {
      blocked = true;
      blockReasons.push('HTTP 403 Forbidden');
    }

    if (title.toLowerCase().includes('access denied')) {
      blocked = true;
      blockReasons.push("'Access Denied' in page title");
    }

    const content = await page.content();
    if (content.includes('Access Denied') || content.includes('errors.edgesuite.net')) {
      blocked = true;
      blockReasons.push('Akamai block message in page content');
    }

    // Check for products
    let productCount = 0;
    try {
      await page.waitForSelector('[data-test="product-pod"], [data-itemid], .product-card', { timeout: 15000 });
      productCount = await page.locator('[data-test="product-pod"], [data-itemid], .product-card').count();
    } catch {
      productCount = 0;
    }

    console.log(`Products found: ${productCount}`);

    console.log('\n' + '=' .repeat(60));
    if (blocked) {
      console.log('RESULT: BLOCKED BY AKAMAI');
      console.log(`Reasons: ${blockReasons.join(', ')}`);
    } else if (productCount > 0) {
      console.log('RESULT: SUCCESS! Page loaded with products.');
      console.log(`Found ${productCount} product cards.`);
      console.log('\nFirefox bypass is WORKING!');
    } else {
      console.log('RESULT: PARTIAL SUCCESS');
      console.log('Page loaded but no products found.');
    }
    console.log('=' .repeat(60));

    // Keep browser open for inspection
    console.log('\nBrowser stays open for 30 seconds...');
    await page.waitForTimeout(30000);

  } catch (err) {
    console.error(`\nError: ${err.message}`);
  } finally {
    await browser.close();
  }
}

test().catch(console.error);
