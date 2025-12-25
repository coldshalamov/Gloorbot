/**
 * Debug network requests to understand Akamai blocking pattern
 * Run with: node test_network_debug.js
 */

const { chromium } = require('playwright');
const { newInjectedContext } = require('fingerprint-injector');

const TEST_URL = 'https://www.lowes.com/pl/Bathroom-vanities-Bathroom-storage/4294612479';

async function test() {
  console.log('=' .repeat(60));
  console.log('NETWORK DEBUG TEST');
  console.log('=' .repeat(60));

  const browser = await chromium.launch({
    headless: false,
    channel: 'chrome',
    args: ['--disable-blink-features=AutomationControlled'],
  });

  const context = await newInjectedContext(browser, {
    fingerprintOptions: {
      devices: ['desktop'],
      operatingSystems: ['windows'],
    },
  });

  const page = await context.newPage();

  // Track all requests and responses
  const requests = [];
  const responses = [];

  page.on('request', (req) => {
    const url = req.url();
    if (url.includes('lowes.com') || url.includes('akamai') || url.includes('akam')) {
      requests.push({
        url: url.substring(0, 100),
        method: req.method(),
        headers: req.headers(),
      });
    }
  });

  page.on('response', (res) => {
    const url = res.url();
    if (url.includes('lowes.com') || url.includes('akamai') || url.includes('akam')) {
      responses.push({
        url: url.substring(0, 100),
        status: res.status(),
        headers: res.headers(),
      });
    }
  });

  try {
    console.log('\n1. Loading homepage...');
    await page.goto('https://www.lowes.com', {
      waitUntil: 'domcontentloaded',
      timeout: 60000,
    });
    // Wait for page to load but don't wait for networkidle
    await page.waitForTimeout(5000);

    console.log(`   Requests: ${requests.length}, Responses: ${responses.length}`);
    console.log(`   Homepage title: "${await page.title()}"`);

    // Check for Akamai cookies
    const cookies = await context.cookies();
    const akamaiCookies = cookies.filter(c =>
      c.name.includes('_abck') ||
      c.name.includes('bm_') ||
      c.name.includes('ak_') ||
      c.name.includes('akamai')
    );
    console.log('\n   Akamai-related cookies:');
    akamaiCookies.forEach(c => {
      console.log(`   - ${c.name}: ${c.value.substring(0, 30)}...`);
    });

    // Wait to let Akamai scripts run
    console.log('\n2. Waiting 5 seconds for Akamai scripts to execute...');
    await page.waitForTimeout(5000);

    // Check cookies again
    const cookies2 = await context.cookies();
    const akamaiCookies2 = cookies2.filter(c =>
      c.name.includes('_abck') ||
      c.name.includes('bm_') ||
      c.name.includes('ak_') ||
      c.name.includes('akamai')
    );
    console.log('\n   Akamai cookies after waiting:');
    akamaiCookies2.forEach(c => {
      console.log(`   - ${c.name}: ${c.value.substring(0, 50)}...`);
    });

    // Now try the product page
    console.log('\n3. Navigating to product listing...');
    const startReqs = requests.length;
    const response = await page.goto(TEST_URL, {
      waitUntil: 'domcontentloaded',
      timeout: 60000,
    });

    console.log(`   Response status: ${response.status()}`);
    console.log(`   New requests made: ${requests.length - startReqs}`);

    await page.waitForLoadState('networkidle').catch(() => {});

    const title = await page.title();
    console.log(`   Page title: "${title}"`);

    // Check for block
    if (title.includes('Access Denied')) {
      console.log('\n   BLOCKED!');

      // Show response headers
      const mainResponse = responses.find(r => r.url.includes(TEST_URL.substring(0, 50)));
      if (mainResponse) {
        console.log('\n   Response headers:');
        Object.entries(mainResponse.headers).forEach(([k, v]) => {
          if (k.includes('akamai') || k.includes('server') || k.includes('x-')) {
            console.log(`   - ${k}: ${v}`);
          }
        });
      }

      // Check final cookies
      const finalCookies = await context.cookies();
      const finalAkamai = finalCookies.filter(c =>
        c.name.includes('_abck') ||
        c.name.includes('bm_')
      );
      console.log('\n   Final Akamai cookies:');
      finalAkamai.forEach(c => {
        // _abck cookie value pattern indicates pass/fail
        if (c.name === '_abck') {
          const passed = c.value.includes('~0~');
          console.log(`   - ${c.name}: ${passed ? 'CHALLENGE PASSED' : 'CHALLENGE FAILED'}`);
        } else {
          console.log(`   - ${c.name}: ${c.value.substring(0, 40)}...`);
        }
      });
    } else {
      console.log('\n   Page loaded (checking content)...');

      // Wait more for content
      await page.waitForTimeout(5000);
      const finalTitle = await page.title();
      console.log(`   Final title: "${finalTitle}"`);

      const content = await page.content();
      if (content.includes('Access Denied')) {
        console.log('   ACTUALLY BLOCKED (Access Denied in content)');
      } else {
        console.log('   Checking for products...');
        const productCount = await page.locator('[data-test="product-pod"], [data-itemid]').count();
        console.log(`   Products found: ${productCount}`);

        // Get page text sample
        const bodyText = await page.evaluate(() => document.body.innerText.substring(0, 300));
        console.log('\n   Page text sample:');
        console.log('   ' + bodyText.split('\n').slice(0, 5).join('\n   '));
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
