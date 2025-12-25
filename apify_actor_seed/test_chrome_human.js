/**
 * Test Chrome with fingerprint-injector AND human behavior
 * Run with: node test_chrome_human.js
 */

const { chromium } = require('playwright');
const { newInjectedContext } = require('fingerprint-injector');

// Use a real category URL from LowesMap.txt
const TEST_URL = 'https://www.lowes.com/pl/Bathroom-vanities-Bathroom-storage/4294612479';

// Human-like mouse movement with bezier curves
async function humanMouseMove(page) {
  const viewport = page.viewportSize();
  const width = viewport?.width || 1440;
  const height = viewport?.height || 900;

  // Random start and end points
  const startX = Math.random() * width * 0.3;
  const startY = Math.random() * height * 0.3;
  const endX = width * 0.4 + Math.random() * width * 0.4;
  const endY = height * 0.4 + Math.random() * height * 0.4;

  const steps = 15 + Math.floor(Math.random() * 15);

  for (let i = 0; i <= steps; i++) {
    const progress = i / steps;
    // Ease in-out curve
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
  const scrollAmount = 150 + Math.floor(Math.random() * 250);
  const steps = 4 + Math.floor(Math.random() * 4);
  const stepAmount = scrollAmount / steps;

  for (let i = 0; i < steps; i++) {
    await page.mouse.wheel(0, stepAmount);
    await page.waitForTimeout(40 + Math.random() * 80);
  }
}

// Simulate human reading time
async function humanWait(min = 1000, max = 3000) {
  const wait = min + Math.random() * (max - min);
  return new Promise(resolve => setTimeout(resolve, wait));
}

// Click with human-like behavior
async function humanClick(page, element) {
  try {
    const box = await element.boundingBox();
    if (!box) return false;

    // Move to element first
    const targetX = box.x + box.width * (0.3 + Math.random() * 0.4);
    const targetY = box.y + box.height * (0.3 + Math.random() * 0.4);

    await page.mouse.move(targetX, targetY, { steps: 10 });
    await page.waitForTimeout(100 + Math.random() * 200);
    await page.mouse.click(targetX, targetY);
    return true;
  } catch {
    return false;
  }
}

async function test() {
  console.log('=' .repeat(60));
  console.log('CHROME + FINGERPRINT-INJECTOR + HUMAN BEHAVIOR TEST');
  console.log('=' .repeat(60));

  console.log('\nLaunching Chrome with fingerprint-injector...');

  const browser = await chromium.launch({
    headless: false,
    channel: 'chrome', // CRITICAL: Real Chrome, not Chromium
    args: [
      '--disable-blink-features=AutomationControlled',
      '--disable-dev-shm-usage',
      '--disable-infobars',
      '--lang=en-US',
      '--window-size=1440,900',
    ],
  });

  console.log('Creating injected context with realistic fingerprint...');

  // Use fingerprint-injector for browser fingerprint masking
  const context = await newInjectedContext(browser, {
    fingerprintOptions: {
      devices: ['desktop'],
      operatingSystems: ['windows'],
      browsers: [{ name: 'chrome', minVersion: 120 }],
    },
  });

  const page = await context.newPage();

  try {
    // STEP 1: Start with homepage
    console.log('\n1. Loading homepage first (like real user)...');
    await page.goto('https://www.lowes.com', {
      waitUntil: 'domcontentloaded',
      timeout: 60000,
    });

    await page.waitForLoadState('networkidle').catch(() => {});

    const homeTitle = await page.title();
    console.log(`   Homepage title: "${homeTitle}"`);

    // Check if blocked on homepage
    let content = await page.content();
    if (content.includes('Access Denied')) {
      console.log('   BLOCKED on homepage!');
      await browser.close();
      return;
    }

    // STEP 2: Human behavior on homepage
    console.log('\n2. Simulating human behavior on homepage...');

    console.log('   - Mouse movement...');
    await humanMouseMove(page);
    await humanWait(800, 1500);

    console.log('   - Scrolling...');
    await humanScroll(page);
    await humanWait(1500, 2500);

    console.log('   - More mouse movement...');
    await humanMouseMove(page);
    await humanWait(500, 1000);

    // Try clicking something on the homepage
    console.log('   - Looking for something to click...');
    const clickable = page.locator('a[href*="/c/"], a[href*="/pl/"]').first();
    if (await clickable.isVisible().catch(() => false)) {
      console.log('   - Clicking a category link...');
      await humanClick(page, clickable);
      await humanWait(2000, 3000);

      // Check where we landed
      await page.waitForLoadState('networkidle').catch(() => {});
      const midTitle = await page.title();
      console.log(`   - Landed on: "${midTitle}"`);

      // More human behavior
      await humanMouseMove(page);
      await humanScroll(page);
      await humanWait(1000, 2000);
    }

    // STEP 3: Navigate to target product listing
    console.log('\n3. Navigating to product listing page...');
    await page.goto(TEST_URL, {
      waitUntil: 'domcontentloaded',
      timeout: 60000,
    });

    // Human behavior during page load
    await page.waitForTimeout(1000);
    await humanMouseMove(page);

    await page.waitForLoadState('networkidle').catch(() => {});
    await humanWait(2000, 3000);

    // Continue human behavior
    console.log('   - Behaving like human on product page...');
    await humanMouseMove(page);
    await humanScroll(page);
    await humanWait(1000, 2000);

    const plTitle = await page.title();
    console.log(`\n   Page title: "${plTitle}"`);

    // Check for blocks
    content = await page.content();
    const blocked = content.includes('Access Denied') || plTitle.includes('Access Denied');

    if (blocked) {
      console.log('\n   RESULT: BLOCKED BY AKAMAI');

      // Take screenshot of block page
      await page.screenshot({ path: 'chrome_blocked.png' });
      console.log('   Screenshot saved to chrome_blocked.png');
    } else if (plTitle.includes('404')) {
      console.log('\n   RESULT: 404 - URL may have changed');
    } else {
      console.log('\n   RESULT: SUCCESS - PAGE LOADED!');

      // Check for products
      const productCount = await page.locator('[data-test="product-pod"], [data-itemid], article:has(a[href*="/pd/"])').count();
      console.log(`   Products found: ${productCount}`);

      // Page preview
      const bodyText = await page.evaluate(() => document.body.innerText.substring(0, 400));
      console.log('\n   Page preview:');
      console.log('   ' + bodyText.split('\n').slice(0, 6).join('\n   '));

      // Screenshot
      await page.screenshot({ path: 'chrome_success.png' });
      console.log('\n   Screenshot saved to chrome_success.png');
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
