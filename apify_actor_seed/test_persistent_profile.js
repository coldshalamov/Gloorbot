/**
 * Test with PERSISTENT browser profile
 * Akamai may trust browsers with history over fresh profiles
 * Run with: node test_persistent_profile.js
 */

const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

// Try a different category from LowesMap.txt
const TEST_URL = 'https://www.lowes.com/pl/Paint-cleaners-chemicals-additives-Paint/2521972965619';

// Use a persistent profile directory
const PROFILE_DIR = path.join(__dirname, '.playwright-profiles', 'lowes-scraper');

async function test() {
  console.log('=' .repeat(60));
  console.log('PERSISTENT PROFILE TEST');
  console.log('=' .repeat(60));
  console.log(`\nProfile directory: ${PROFILE_DIR}`);

  // Ensure profile directory exists
  if (!fs.existsSync(PROFILE_DIR)) {
    fs.mkdirSync(PROFILE_DIR, { recursive: true });
    console.log('Created new profile directory');
  } else {
    console.log('Using existing profile (may have cached trust)');
  }

  // Launch with persistent context (like a real browser)
  console.log('\nLaunching Chrome with persistent profile...');

  const context = await chromium.launchPersistentContext(PROFILE_DIR, {
    headless: false,
    channel: 'chrome',
    viewport: { width: 1440, height: 900 },
    locale: 'en-US',
    timezoneId: 'America/Los_Angeles',
    args: [
      '--disable-blink-features=AutomationControlled',
      '--disable-dev-shm-usage',
      '--disable-infobars',
      '--lang=en-US',
    ],
  });

  const page = context.pages()[0] || await context.newPage();

  try {
    // STEP 1: Load homepage
    console.log('\n1. Loading homepage...');
    await page.goto('https://www.lowes.com', {
      waitUntil: 'domcontentloaded',
      timeout: 60000,
    });
    await page.waitForTimeout(5000);

    const homeTitle = await page.title();
    console.log(`   Homepage title: "${homeTitle}"`);

    // Check cookies
    const cookies = await context.cookies();
    const akamaiCookies = cookies.filter(c => c.name.includes('_abck') || c.name.includes('bm_'));
    console.log(`   Akamai cookies: ${akamaiCookies.length}`);

    // Human-like behavior
    console.log('\n2. Simulating human browsing...');

    // Scroll around
    for (let i = 0; i < 3; i++) {
      await page.mouse.wheel(0, 200 + Math.random() * 200);
      await page.waitForTimeout(500 + Math.random() * 500);
    }

    // Move mouse
    for (let i = 0; i < 5; i++) {
      const x = 100 + Math.random() * 1200;
      const y = 100 + Math.random() * 700;
      await page.mouse.move(x, y);
      await page.waitForTimeout(100 + Math.random() * 200);
    }

    await page.waitForTimeout(2000);

    // STEP 2: Navigate to product page
    console.log('\n3. Navigating to product listing...');
    await page.goto(TEST_URL, {
      waitUntil: 'domcontentloaded',
      timeout: 60000,
    });

    // Human behavior during load
    await page.waitForTimeout(1000);
    await page.mouse.move(500, 400);
    await page.waitForTimeout(2000);

    // More scrolling
    for (let i = 0; i < 2; i++) {
      await page.mouse.wheel(0, 150 + Math.random() * 150);
      await page.waitForTimeout(300 + Math.random() * 300);
    }

    await page.waitForTimeout(5000);

    const title = await page.title();
    const currentUrl = page.url();
    console.log(`   Page title: "${title}"`);
    console.log(`   Current URL: ${currentUrl}`);
    console.log(`   Expected URL: ${TEST_URL}`);

    const content = await page.content();
    const blocked = content.includes('Access Denied') || title.includes('Access Denied');

    if (blocked) {
      console.log('\n   RESULT: BLOCKED');

      // Check _abck cookie
      const finalCookies = await context.cookies();
      const abck = finalCookies.find(c => c.name === '_abck');
      if (abck) {
        const passed = abck.value.includes('~0~');
        console.log(`   _abck status: ${passed ? 'PASSED' : 'FAILED'}`);
      }
    } else if (title.includes('404')) {
      console.log('\n   RESULT: 404');
    } else {
      console.log('\n   RESULT: SUCCESS!');

      // Try multiple selectors
      const selectors = [
        '[data-test="product-pod"]',
        '[data-itemid]',
        'article',
        '[data-sku]',
        '[class*="ProductCard"]',
        '[class*="product-card"]',
        'div[class*="sc-product"]',
        'li:has(a[href*="/pd/"])',
      ];

      console.log('\n   Checking product selectors:');
      for (const sel of selectors) {
        const count = await page.locator(sel).count();
        if (count > 0) {
          console.log(`   - ${sel}: ${count} elements`);
        }
      }

      // Get page text sample
      const bodyText = await page.evaluate(() => document.body.innerText.substring(0, 500));
      console.log('\n   Page text sample:');
      console.log('   ' + bodyText.split('\n').slice(0, 8).join('\n   '));
    }

    // Take screenshot
    await page.screenshot({ path: 'persistent_profile.png' });
    console.log('\n   Screenshot saved');

    console.log('\n\nBrowser stays open for 30 seconds...');
    await page.waitForTimeout(30000);

  } catch (err) {
    console.error(`\nError: ${err.message}`);
  } finally {
    await context.close();
  }
}

test().catch(console.error);
