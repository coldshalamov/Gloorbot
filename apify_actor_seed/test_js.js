/**
 * Simple test to verify Akamai bypass works with fingerprint-injector
 * Run with: node test_js.js
 */

const { chromium } = require('playwright');
const { newInjectedContext } = require('fingerprint-injector');

const TEST_URL = 'https://www.lowes.com/pl/Paint/4294644082';

async function test() {
  console.log('=' .repeat(60));
  console.log('AKAMAI BYPASS TEST (JavaScript + fingerprint-injector)');
  console.log('=' .repeat(60));
  console.log(`\nTarget URL: ${TEST_URL}`);
  console.log('Browser: Chrome (not Chromium)');
  console.log('\nLaunching browser...');

  const browser = await chromium.launch({
    headless: false,
    channel: 'chrome', // CRITICAL: Use real Chrome
    args: [
      '--disable-blink-features=AutomationControlled',
      '--disable-dev-shm-usage',
      '--no-sandbox',
      '--window-size=1440,900',
    ],
  });

  console.log('Creating injected context with fingerprint-injector...');

  // This is the magic - fingerprint-injector generates realistic fingerprints
  const context = await newInjectedContext(browser, {
    fingerprintOptions: {
      devices: ['desktop'],
      operatingSystems: ['windows', 'macos'],
    },
  });

  const page = await context.newPage();

  console.log(`\nNavigating to ${TEST_URL}...`);

  try {
    const response = await page.goto(TEST_URL, {
      waitUntil: 'domcontentloaded',
      timeout: 60000,
    });

    // Wait for content
    await page.waitForTimeout(3000);

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
      await page.waitForSelector('[data-test="product-pod"], [data-itemid]', { timeout: 10000 });
      productCount = await page.locator('[data-test="product-pod"], [data-itemid]').count();
    } catch {
      productCount = 0;
    }

    console.log(`Products found: ${productCount}`);

    console.log('\n' + '=' .repeat(60));
    if (blocked) {
      console.log('RESULT: BLOCKED BY AKAMAI');
      console.log(`Reasons: ${blockReasons.join(', ')}`);
      console.log('\nThe fingerprint-injector is working but your IP may be flagged.');
      console.log('Try: mobile hotspot, different network, or wait 24h.');
    } else if (productCount > 0) {
      console.log('RESULT: SUCCESS! Page loaded with products.');
      console.log(`Found ${productCount} product cards.`);
      console.log('\nThe Akamai bypass is WORKING!');
    } else {
      console.log('RESULT: PARTIAL SUCCESS');
      console.log('Page loaded but no products found.');
      console.log('Check if the category URL is valid.');
    }
    console.log('=' .repeat(60));

    // Keep browser open for inspection
    console.log('\nBrowser stays open for 30 seconds for inspection...');
    console.log('Press Ctrl+C to close early.');
    await page.waitForTimeout(30000);

  } catch (err) {
    console.error(`\nError: ${err.message}`);
    console.log('\nThis might indicate:');
    console.log('1. Chrome not installed (install Google Chrome)');
    console.log('2. Network issues');
    console.log('3. fingerprint-injector not installed (run: npm install)');
  } finally {
    await browser.close();
  }
}

test().catch(console.error);
