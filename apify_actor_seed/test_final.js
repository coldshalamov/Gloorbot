/**
 * FINAL WORKING TEST - Lowe's Akamai Bypass
 *
 * Key techniques that work:
 * 1. Persistent browser profile (builds trust over time)
 * 2. Real Chrome browser (not Chromium)
 * 3. Human-like behavior (mouse movements, scrolling)
 * 4. Session warm-up (visit homepage first)
 *
 * Run with: node test_final.js
 */

const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const PROFILE_DIR = path.join(__dirname, '.playwright-profiles', 'test_final');
const TEST_URL = 'https://www.lowes.com/pl/Paint-cleaners-chemicals-additives/2521972965619';

// Human-like mouse movement
async function humanMouseMove(page) {
  const viewport = page.viewportSize();
  const width = viewport?.width || 1440;
  const height = viewport?.height || 900;

  const startX = Math.random() * width * 0.3;
  const startY = Math.random() * height * 0.3;
  const endX = width * 0.4 + Math.random() * width * 0.4;
  const endY = height * 0.4 + Math.random() * height * 0.4;

  const steps = 10 + Math.floor(Math.random() * 10);
  for (let i = 0; i <= steps; i++) {
    const progress = i / steps;
    const eased = progress < 0.5
      ? 2 * progress * progress
      : 1 - Math.pow(-2 * progress + 2, 2) / 2;
    const x = startX + (endX - startX) * eased + (Math.random() - 0.5) * 3;
    const y = startY + (endY - startY) * eased + (Math.random() - 0.5) * 3;
    await page.mouse.move(x, y);
    await page.waitForTimeout(15 + Math.random() * 25);
  }
}

// Human-like scrolling
async function humanScroll(page) {
  const scrollAmount = 150 + Math.floor(Math.random() * 200);
  const steps = 4 + Math.floor(Math.random() * 4);
  const stepAmount = scrollAmount / steps;
  for (let i = 0; i < steps; i++) {
    await page.mouse.wheel(0, stepAmount);
    await page.waitForTimeout(40 + Math.random() * 80);
  }
}

async function test() {
  console.log('=' .repeat(60));
  console.log('AKAMAI BYPASS - FINAL WORKING TEST');
  console.log('=' .repeat(60));

  // Ensure profile directory exists
  if (!fs.existsSync(PROFILE_DIR)) {
    fs.mkdirSync(PROFILE_DIR, { recursive: true });
    console.log('\nCreated new profile directory');
  } else {
    console.log('\nUsing existing profile');
  }

  // Launch with persistent context
  console.log('Launching Chrome with persistent profile...\n');

  const context = await chromium.launchPersistentContext(PROFILE_DIR, {
    headless: false,
    channel: 'chrome', // Real Chrome, not Chromium
    viewport: { width: 1440, height: 900 },
    locale: 'en-US',
    timezoneId: 'America/Los_Angeles',
    args: [
      '--disable-blink-features=AutomationControlled',
      '--disable-dev-shm-usage',
      '--disable-infobars',
    ],
  });

  const page = context.pages()[0] || await context.newPage();

  try {
    // STEP 1: Warm up with homepage
    console.log('1. Loading homepage first (session warm-up)...');
    await page.goto('https://www.lowes.com', {
      waitUntil: 'domcontentloaded',
      timeout: 60000,
    });
    await page.waitForTimeout(3000 + Math.random() * 2000);

    const homeTitle = await page.title();
    console.log(`   Title: "${homeTitle}"`);

    if ((await page.content()).includes('Access Denied')) {
      console.log('   BLOCKED on homepage!');
      await context.close();
      return;
    }

    // STEP 2: Human behavior on homepage
    console.log('\n2. Simulating human behavior...');
    await humanMouseMove(page);
    await page.waitForTimeout(1000 + Math.random() * 1000);
    await humanScroll(page);
    await page.waitForTimeout(1500 + Math.random() * 1500);
    await humanMouseMove(page);
    console.log('   Done.');

    // STEP 3: Navigate to product page
    console.log('\n3. Navigating to product listing...');
    await page.goto(TEST_URL, {
      waitUntil: 'domcontentloaded',
      timeout: 60000,
    });

    await page.waitForTimeout(1000 + Math.random() * 1000);
    await humanMouseMove(page);
    await humanScroll(page);
    await page.waitForTimeout(2000);

    const title = await page.title();
    const url = page.url();

    console.log(`   Title: "${title}"`);
    console.log(`   URL: ${url}`);

    // Check results
    const content = await page.content();
    const blocked = content.includes('Access Denied') || title.includes('Access Denied');

    console.log('\n' + '=' .repeat(60));
    if (blocked) {
      console.log('RESULT: BLOCKED');
    } else if (title.includes('404')) {
      console.log('RESULT: 404 (URL changed)');
    } else {
      console.log('RESULT: SUCCESS!');

      // Count products
      const selectors = ['article', '[class*="ProductCard"]', '[class*="product-card"]'];
      console.log('\nProduct counts:');
      for (const sel of selectors) {
        const count = await page.locator(sel).count();
        if (count > 0) {
          console.log(`  ${sel}: ${count} elements`);
        }
      }

      // Show page text sample
      const bodyText = await page.evaluate(() => document.body.innerText.substring(0, 400));
      console.log('\nPage text preview:');
      console.log(bodyText.split('\n').slice(0, 6).join('\n'));
    }
    console.log('=' .repeat(60));

    console.log('\nBrowser stays open for 15 seconds...');
    await page.waitForTimeout(15000);

  } catch (err) {
    console.error(`\nError: ${err.message}`);
  } finally {
    await context.close();
  }
}

test().catch(console.error);
