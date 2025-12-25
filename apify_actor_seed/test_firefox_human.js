/**
 * Test Firefox with HUMAN-LIKE BEHAVIOR
 * Akamai tracks mouse movements, scrolling, and clicks
 * Run with: node test_firefox_human.js
 */

const { firefox } = require('playwright');

// Use a real category URL from LowesMap.txt
const TEST_URL = 'https://www.lowes.com/pl/Bathroom-vanities-Bathroom-storage/4294612479';

// Human-like mouse movement
async function humanMouseMove(page) {
  const viewport = page.viewportSize();
  const width = viewport?.width || 1440;
  const height = viewport?.height || 900;

  // Generate random bezier-curve like path
  const startX = Math.random() * width * 0.2;
  const startY = Math.random() * height * 0.2;
  const endX = width * 0.5 + Math.random() * width * 0.3;
  const endY = height * 0.5 + Math.random() * height * 0.3;

  const steps = 10 + Math.floor(Math.random() * 10);

  for (let i = 0; i <= steps; i++) {
    const progress = i / steps;
    // Ease in-out curve
    const eased = progress < 0.5
      ? 2 * progress * progress
      : 1 - Math.pow(-2 * progress + 2, 2) / 2;

    const x = startX + (endX - startX) * eased + (Math.random() - 0.5) * 5;
    const y = startY + (endY - startY) * eased + (Math.random() - 0.5) * 5;

    await page.mouse.move(x, y);
    await page.waitForTimeout(20 + Math.random() * 30);
  }
}

// Human-like scrolling
async function humanScroll(page) {
  const scrollAmount = 200 + Math.floor(Math.random() * 300);
  const steps = 5 + Math.floor(Math.random() * 5);
  const stepAmount = scrollAmount / steps;

  for (let i = 0; i < steps; i++) {
    await page.mouse.wheel(0, stepAmount);
    await page.waitForTimeout(50 + Math.random() * 100);
  }
}

// Simulate human reading time
async function humanWait(min = 1000, max = 3000) {
  const wait = min + Math.random() * (max - min);
  return new Promise(resolve => setTimeout(resolve, wait));
}

async function test() {
  console.log('=' .repeat(60));
  console.log('FIREFOX HUMAN BEHAVIOR TEST');
  console.log('=' .repeat(60));
  console.log('\nKey insight from Apify docs:');
  console.log('"Anti-scraping uses JavaScript to track mouse movement,');
  console.log(' clicks and key presses to decide if user is bot or human"');

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
    // Add realistic headers
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
  });

  const page = await context.newPage();

  try {
    // STEP 1: Start with homepage (like a real user would)
    console.log('\n1. Starting at homepage (like real user)...');
    await page.goto('https://www.lowes.com', {
      waitUntil: 'domcontentloaded',
      timeout: 60000,
    });

    // Wait for page to fully load
    await page.waitForLoadState('networkidle').catch(() => {});

    const homeTitle = await page.title();
    console.log(`   Homepage title: "${homeTitle}"`);

    // Check if blocked
    if ((await page.content()).includes('Access Denied')) {
      console.log('   BLOCKED on homepage!');
      await browser.close();
      return;
    }

    // STEP 2: Simulate human behavior on homepage
    console.log('\n2. Simulating human behavior on homepage...');

    // Move mouse around
    console.log('   - Moving mouse...');
    await humanMouseMove(page);
    await humanWait(500, 1500);

    // Scroll down a bit
    console.log('   - Scrolling...');
    await humanScroll(page);
    await humanWait(1000, 2000);

    // Move mouse again
    await humanMouseMove(page);
    await humanWait(500, 1000);

    // STEP 3: Now navigate to product listing
    console.log('\n3. Navigating to product listing page...');
    await page.goto(TEST_URL, {
      waitUntil: 'domcontentloaded',
      timeout: 60000,
    });

    // Continue human behavior while page loads
    await page.waitForTimeout(1000);
    await humanMouseMove(page);

    await page.waitForLoadState('networkidle').catch(() => {});
    await humanWait(2000, 4000);

    // More human behavior
    console.log('   - More human behavior on product page...');
    await humanMouseMove(page);
    await humanScroll(page);
    await humanWait(1000, 2000);

    const plTitle = await page.title();
    console.log(`\n   Page title: "${plTitle}"`);

    // Check for blocks
    const content = await page.content();
    const blocked = content.includes('Access Denied') || plTitle.includes('Access Denied');

    if (blocked) {
      console.log('\n   RESULT: BLOCKED BY AKAMAI');
      console.log('   Even with human behavior simulation...');
    } else if (plTitle.includes('404')) {
      console.log('\n   RESULT: 404 - URL may have changed');
    } else {
      console.log('\n   RESULT: PAGE LOADED!');

      // Try to find products
      const bodyText = await page.evaluate(() => document.body.innerText.substring(0, 300));
      console.log('\n   Page preview:');
      console.log('   ' + bodyText.split('\n').slice(0, 5).join('\n   '));

      // Screenshot
      await page.screenshot({ path: 'firefox_human.png' });
      console.log('\n   Screenshot saved to firefox_human.png');
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
