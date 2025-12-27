const { Actor, log } = require('apify');
const { chromium } = require('playwright');
const { newInjectedContext } = require('fingerprint-injector');
const yaml = require('js-yaml');
const fs = require('fs');
const path = require('path');
const pLimitImport = require('p-limit');

const BASE_URL = 'https://www.lowes.com';
const PAGE_SIZE = 24;
const MIN_PRODUCTS_TO_CONTINUE = 6;
const MAX_EMPTY_PAGES = 2;

const SELECTORS = {
  CARD: "[data-test='product-pod'], [data-test='productPod'], div[data-itemid], li[data-itemid], [data-itemid], li:has(a[href*='/pd/']), article:has(a[href*='/pd/'])",
  TITLE: ":scope [data-testid='item-description'], :scope a[data-testid='item-description-link'], :scope a[href*='/pd/'], :scope [data-test*='product-title'], :scope h3, :scope h2",
  PRICE: ":scope [data-testid='regular-price'], :scope [data-testid='current-price'], :scope [data-test*='price'], :scope [data-testid*='price'], :scope [aria-label*='$'], :scope [data-test*='current-price']",
  PRICE_ALT: ":scope [data-test*='value'], :scope [data-testid*='value'], :scope [data-test*='sale-price']",
  WAS_PRICE: ":scope [data-testid='was-price'], :scope [data-test*='was'], :scope [data-testid*='was'], :scope [class*='was-price'], :scope [data-test*='savings']",
  AVAIL: ":scope [data-test*='availability'], :scope [data-testid*='availability'], :scope [data-test*='fulfillment'], :scope [data-test*='pickup']",
  LINK: ":scope a[data-testid='item-description-link'], :scope a[href*='/pd/'], :scope a[data-test*='product-link']",
  IMG: ":scope img",
};

const PICKUP_SELECTORS = [
  'label:has-text("Get It Today")',
  'label:has-text("Pickup Today")',
  'label:has-text("Available Today")',
  'label:has-text("Pickup")',
  'div:has-text("Pickup Today")',
  'button:has-text("Pickup")',
  'button:has-text("Pickup Today")',
  'button:has-text("Get It Today")',
  'button:has-text("Get it today")',
  '[data-testid*="pickup"]',
  '[aria-label*="Pickup"]',
  'input[type="checkbox"][id*="pickup"]',
];

const STORE_SELECTORS = {
  BADGE: "header [data-test*='store'], header [aria-label*='store'], [data-test*='store-badge'], a[href*='store-details']",
  STORE_CARD: "[data-store-id], [data-storeid], [data-test*='store-card'], li:has(a[href*='store-details']), a[href*='store-details']",
};

const BLOCKED_RESOURCE_TYPES = new Set(['image', 'media', 'font']);
const BLOCKED_URL_PATTERNS = [
  /google-analytics\.com/i,
  /googletagmanager\.com/i,
  /doubleclick\.net/i,
  /facebook\.net/i,
  /analytics/i,
  /tracking/i,
  /beacon/i,
  /pixel/i,
  /ads\./i,
  /adservice/i,
  /hotjar\.com/i,
  /clarity\.ms/i,
  /newrelic\.com/i,
  /sentry\.io/i,
  /segment\.com/i,
  /optimizely\.com/i,
  /fullstory\.com/i,
  /\.woff2?(\?|$)/i,
  /\.ttf(\?|$)/i,
  /\.eot(\?|$)/i,
];

function readYaml(filePath) {
  if (!fs.existsSync(filePath)) return null;
  const raw = fs.readFileSync(filePath, 'utf8');
  return yaml.load(raw);
}

function buildUrl(base, offset, storeId) {
  const parsed = new URL(base, BASE_URL);
  parsed.searchParams.set('pickupType', 'pickupToday');
  parsed.searchParams.set('availability', 'pickupToday');
  parsed.searchParams.set('inStock', '1');
  parsed.searchParams.set('rollUpVariants', '0');
  if (offset > 0) parsed.searchParams.set('offset', String(offset));
  if (storeId && !parsed.searchParams.get('storeNumber')) {
    parsed.searchParams.set('storeNumber', storeId);
  }
  return parsed.toString();
}

function parsePrice(value) {
  if (!value) return null;
  const cleaned = String(value).replace(/[^0-9.,]/g, '');
  if (!cleaned) return null;
  const numberValue = Number(cleaned.replace(/,/g, ''));
  return Number.isFinite(numberValue) ? numberValue : null;
}

function collectProductDicts(obj, results = []) {
  if (obj && typeof obj === 'object') {
    if (Array.isArray(obj)) {
      obj.forEach((entry) => collectProductDicts(entry, results));
    } else {
      const typeValue = String(obj['@type'] || '').toLowerCase();
      if (typeValue === 'product') {
        results.push(obj);
      } else {
        Object.values(obj).forEach((entry) => collectProductDicts(entry, results));
      }
    }
  }
  return results;
}

function normalizeImageUrl(value) {
  if (Array.isArray(value)) {
    for (const entry of value) {
      const normalized = normalizeImageUrl(entry);
      if (normalized) return normalized;
    }
    return null;
  }
  if (!value || typeof value !== 'string') return null;
  if (value.startsWith('//')) return `https:${value}`;
  if (value.startsWith('/')) return new URL(value, BASE_URL).toString();
  return value;
}

function ensureStoreUrl(url, storeId) {
  if (!url) return null;
  const absolute = new URL(url, BASE_URL);
  if (storeId && !absolute.searchParams.get('storeNumber')) {
    absolute.searchParams.set('storeNumber', storeId);
  }
  return absolute.toString();
}

function skuFromUrl(url) {
  if (!url) return null;
  const match = String(url).match(/\/(?:pd|product)\/[^/\-]*-?(\d{4,})/i);
  return match ? match[1] : null;
}

async function setupRequestBlocking(page) {
  // CRITICAL: Akamai detects aggressive resource blocking as bot behavior
  // Real users load images, fonts, and tracking scripts
  // Only block obvious third-party trackers that won't affect Akamai detection
  await page.route('**/*', async (route) => {
    const url = route.request().url().toLowerCase();

    // NEVER block anything from lowes.com or Akamai
    if (url.includes('lowes.com') || url.includes('akamai') || url.includes('/_sec/')) {
      return route.continue();
    }

    // Only block obvious third-party trackers (NOT images/fonts)
    const blockPatterns = [
      /google-analytics\.com/i,
      /googletagmanager\.com/i,
      /doubleclick\.net/i,
      /facebook\.net/i,
    ];

    for (const pattern of blockPatterns) {
      if (pattern.test(url)) {
        return route.abort();
      }
    }

    // Let everything else through - real users load images and fonts!
    return route.continue();
  });
}

async function isSelected(element) {
  try {
    const attrs = ['aria-checked', 'aria-pressed', 'aria-selected'];
    for (const attr of attrs) {
      const value = await element.getAttribute(attr);
      if (value === 'true') return true;
    }
    if (await element.isChecked()) return true;
  } catch {
    return false;
  }
  return false;
}

async function applyPickupFilter(page) {
  const pickupSelectors = [
    'label:has-text("Get It Today")',
    'label:has-text("Pickup Today")',
    'label:has-text("Available Today")',
    'button:has-text("Pickup")',
    'button:has-text("Pickup Today")',
    'button:has-text("Get It Today")',
    'button:has-text("Get it fast")',
    '[data-testid*="pickup"]',
    '[data-testid*="availability"]',
    '[data-test-id*="pickup"]',
    '[aria-label*="Pickup"]',
    '[aria-label*="Get it today"]',
    '[aria-label*="Available today"]',
    'input[type="checkbox"][id*="pickup"]',
    'input[type="checkbox"][id*="availability"]',
  ];

  const availabilityToggles = [
    'button:has-text("Availability")',
    'button:has-text("Get It Fast")',
    'summary:has-text("Availability")',
    'summary:has-text("Get It Fast")',
  ];

  const filterTriggers = [
    'button:has-text("Filters")',
    'button:has-text("Filter")',
    'button:has-text("Refine")',
    'button:has-text("Availability")',
    'button:has-text("Get It Fast")',
  ];

  async function expandFilters() {
    for (const selector of filterTriggers) {
      const trigger = page.locator(selector).first();
      try {
        if (!(await trigger.isVisible())) continue;
        await trigger.scrollIntoViewIfNeeded().catch(() => {});
        const expanded = await trigger.getAttribute('aria-expanded');
        if (expanded === 'false' || expanded === null) {
          await trigger.click({ timeout: 8000 }).catch(async () => {
            await trigger.click({ timeout: 8000, force: true }).catch(() => {});
          });
          await page.waitForTimeout(700);
        }
        break;
      } catch {
        continue;
      }
    }

    for (const selector of availabilityToggles) {
      const toggle = page.locator(selector).first();
      try {
        if (!(await toggle.isVisible())) continue;
        const expanded = await toggle.getAttribute('aria-expanded');
        if (expanded === 'false') {
          await toggle.click({ timeout: 8000 });
          await page.waitForTimeout(700);
        }
        break;
      } catch {
        continue;
      }
    }
  }

  async function verifyApplied() {
    const url = page.url().toLowerCase();
    if (url.includes('pickup') || url.includes('availability') || url.includes('refinement')) return true;
    const chip = page.locator('text=/Pickup Today/i').first();
    try {
      if (await chip.isVisible()) {
        const pressed = await chip.getAttribute('aria-pressed');
        if (pressed === 'true') return true;
      }
    } catch {
      // ignore
    }
    return false;
  }

  await page.waitForLoadState('domcontentloaded').catch(() => {});
  await page.waitForSelector('text=/Pickup Today/i', { timeout: 8000 }).catch(() => {});
  await expandFilters();

  for (let attempt = 0; attempt < 3; attempt += 1) {
    log.info(`[Pickup] Looking for pickup filter (attempt ${attempt + 1}/3)`);
    for (const selector of pickupSelectors) {
      let handles = [];
      try {
        handles = await page.locator(selector).elementHandles();
      } catch {
        handles = [];
      }
      for (const handle of handles) {
        try {
          const visible = await handle.isVisible().catch(() => false);
          let text = '';
          if (visible) {
            try {
              text = (await handle.innerText()) || '';
            } catch {
              text = '';
            }
          }
          if (!visible && !text) continue;
          if (text.length > 120) continue;

          if (await isSelected(handle)) {
            return true;
          }

          await handle.scrollIntoViewIfNeeded().catch(() => {});
          await handle.click({ timeout: 8000 }).catch(async () => {
            await handle.click({ timeout: 8000, force: true }).catch(() => {});
          });
          await page.waitForLoadState('networkidle', { timeout: 12000 }).catch(() => {});

          if (await isSelected(handle)) return true;
          if (await verifyApplied()) return true;
        } catch {
          continue;
        }
      }
    }

    await page.waitForTimeout(900 + Math.random() * 900);
    await expandFilters();
  }

  return false;
}


async function setStoreContext(page, store) {
  if (store.url) {
    await page.goto(store.url, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForLoadState('networkidle').catch(() => {});
    const storeButtons = [
      "button:has-text('Set Store')",
      "button:has-text('Set as My Store')",
      "button:has-text('Make This My Store')",
    ];
    for (const selector of storeButtons) {
      const btn = page.locator(selector).first();
      try {
        if (await btn.isVisible()) {
          await btn.click({ timeout: 8000 });
          await page.waitForTimeout(1500);
          return true;
        }
      } catch {
        continue;
      }
    }
  }

  await page.goto(BASE_URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForLoadState('networkidle').catch(() => {});

  const triggers = [
    page.locator(STORE_SELECTORS.BADGE).first(),
    page.getByRole('button', { name: /store|my store|change/i }).first(),
    page.getByRole('link', { name: /store|my store|change/i }).first(),
    page.locator('text=/Find a Store/i').first(),
  ];

  for (const trigger of triggers) {
    try {
      if (!(await trigger.isVisible())) continue;
      await trigger.click({ timeout: 5000 });
      break;
    } catch {
      continue;
    }
  }

  const inputs = [
    page.getByRole('textbox', { name: /zip/i }).first(),
    page.getByPlaceholder(/zip|store|city/i).first(),
    page.locator("input[name*='zip']").first(),
    page.locator("input[id*='zip']").first(),
  ];

  let zipInput = null;
  for (const input of inputs) {
    try {
      if (await input.isVisible()) {
        zipInput = input;
        break;
      }
    } catch {
      continue;
    }
  }

  if (!zipInput) return false;

  await zipInput.fill(String(store.zip || ''));
  await zipInput.press('Enter').catch(() => {});
  await page.waitForTimeout(1200);

  const storeId = store.store_id;
  let storeCard = null;
  if (storeId) {
    storeCard = page.locator(`[data-store-id='${storeId}'], [data-storeid='${storeId}']`).first();
  }
  if (!storeCard || !(await storeCard.count())) {
    storeCard = page.locator(STORE_SELECTORS.STORE_CARD).first();
  }

  const buttonSelectors = [
    "button:has-text('Set Store')",
    "button:has-text('Make This My Store')",
    "button:has-text('Select Store')",
  ];

  for (const selector of buttonSelectors) {
    const btn = storeCard.locator(selector).first();
    try {
      if (await btn.isVisible()) {
        await btn.click({ timeout: 8000 });
        await page.waitForTimeout(1500);
        return true;
      }
    } catch {
      continue;
    }
  }

  return false;
}

async function isBlocked(page) {
  try {
    const title = await page.title();
    if (title.includes('Access Denied')) return true;
    const content = await page.content();
    if (content.includes('Access Denied') || content.includes('errors.edgesuite.net')) {
      return true;
    }
  } catch {
    return false;
  }
  return false;
}

async function extractProducts(page, store, categoryName, pickupOnly) {
  const scriptLocator = page.locator("script[type='application/ld+json']");
  const scriptCount = await scriptLocator.count().catch(() => 0);
  if (scriptCount > 0) {
    const rows = [];
    for (let i = 0; i < scriptCount; i += 1) {
      const raw = await scriptLocator.nth(i).innerText().catch(() => null);
      if (!raw) continue;
      let payload = null;
      try {
        payload = JSON.parse(raw);
      } catch {
        continue;
      }
      const products = collectProductDicts(payload);
      for (const product of products) {
        const offersValue = product.offers || {};
        const offers = Array.isArray(offersValue) ? (offersValue[0] || {}) : offersValue;
        const price = parsePrice(offers.price);
        if (price == null) continue;
        const priceWas = parsePrice(offers.priceWas);
        const productUrl = ensureStoreUrl(offers.url || product.url, store.store_id);
        rows.push({
          retailer: 'lowes',
          store_id: store.store_id,
          store_name: store.name || store.store_id,
          zip: store.zip,
          category: categoryName,
          title: (product.name || product.description || "Lowe's item").trim(),
          price,
          price_was: priceWas,
          pct_off: priceWas ? (priceWas - price) / priceWas : null,
          availability: offers.availability || null,
          product_url: productUrl,
          image_url: normalizeImageUrl(product.image),
          sku: product.sku || product.productID || product.itemNumber || skuFromUrl(productUrl),
          timestamp: new Date().toISOString(),
          pickup_filter_applied: !pickupOnly,
        });
      }
    }
    if (rows.length) {
      if (pickupOnly) {
        log.warning(`[Extract] pickup filter missing; JSON-LD used without pickup-only verification`);
      }
      return rows;
    }
  }

  const cards = page.locator(SELECTORS.CARD);
  const total = await cards.count().catch(() => 0);
  if (!total) return [];

  const results = [];
  for (let i = 0; i < total; i += 1) {
    const card = cards.nth(i);
    const title = await card.locator(SELECTORS.TITLE).first().innerText().catch(() => null);
    const priceText = await card.locator(SELECTORS.PRICE).first().innerText().catch(() => null);
    const priceAlt = await card.locator(SELECTORS.PRICE_ALT).first().innerText().catch(() => null);
    const wasText = await card.locator(SELECTORS.WAS_PRICE).first().innerText().catch(() => null);
    const avail = await card.locator(SELECTORS.AVAIL).first().innerText().catch(() => null);
    const link = await card.locator(SELECTORS.LINK).first().getAttribute('href').catch(() => null);
    const img = await card.locator(SELECTORS.IMG).first().getAttribute('src').catch(() => null);

    const price = parsePrice(priceText || priceAlt);
    if (price == null) continue;
    const priceWas = parsePrice(wasText);
    const productUrl = link ? new URL(link, BASE_URL).toString() : null;
    const sku = skuFromUrl(productUrl) || (await card.getAttribute('data-itemid').catch(() => null));
    const pctOff = priceWas ? (priceWas - price) / priceWas : null;
    const availText = avail ? avail.trim() : '';
    if (pickupOnly && !/pickup/i.test(availText)) continue;

    results.push({
      retailer: 'lowes',
      store_id: store.store_id,
      store_name: store.name || store.store_id,
      zip: store.zip,
      category: categoryName,
      title: title ? title.trim() : null,
      price,
      price_was: priceWas,
      pct_off: pctOff,
      availability: availText || null,
      product_url: productUrl,
      image_url: img,
      timestamp: new Date().toISOString(),
    });
  }

  if (!results.length && total) {
    try {
      const preview = await cards.nth(0).innerText();
      log.info(`[Extract] first card preview: ${preview.slice(0, 200)}`);
    } catch {
      // ignore
    }
  }

  return results;
}

async function scrapeCategory(page, store, category, maxPages, requirePickup) {
  const seen = new Set();
  const all = [];
  let emptyStreak = 0;

  for (let pageNum = 0; pageNum < maxPages; pageNum += 1) {
    const offset = pageNum * PAGE_SIZE;
    const target = buildUrl(category.url, offset, store.store_id);
    log.info(`[${store.store_id}] ${category.name} p${pageNum + 1} -> ${target}`);

    let resp = null;
    try {
      resp = await page.goto(target, { waitUntil: 'domcontentloaded', timeout: 60000 });
    } catch (err) {
      log.warning(`[${category.name}] goto failed: ${err.message || err}`);
    }
    if (resp && resp.status() >= 400) {
      log.warning(`[${category.name}] HTTP ${resp.status()}`);
    }

    // Human-like behavior after each page load to avoid detection
    await page.waitForTimeout(1000 + Math.random() * 1000);
    await humanMouseMove(page);
    await page.waitForTimeout(500 + Math.random() * 500);
    await humanScroll(page);

    const currentUrl = page.url();
    if (!currentUrl.includes('/pl/')) {
      log.warning(`[${category.name}] Navigation landed on unexpected URL: ${currentUrl}`);
    }

    await page.waitForSelector(SELECTORS.CARD, { timeout: 15000 }).catch(() => {});

    if (await isBlocked(page)) {
      log.error(`[${category.name}] BLOCKED (Access Denied)`);
      break;
    }

    const filterOk = await applyPickupFilter(page);
    const pickupOnly = !filterOk;
    if (!filterOk) {
      log.warning(`[${category.name}] Pickup filter failed; falling back to per-item pickup filtering`);
    }

    const items = await extractProducts(page, store, category.name, pickupOnly);
    log.info(`[${category.name}] extracted ${items.length} items`);
    let newCount = 0;
    for (const item of items) {
      const key = item.sku || item.product_url;
      if (!key || seen.has(key)) continue;
      seen.add(key);
      all.push(item);
      newCount += 1;
    }

    if (!newCount) {
      emptyStreak += 1;
    } else {
      emptyStreak = 0;
    }

    if (items.length < MIN_PRODUCTS_TO_CONTINUE) break;
    if (emptyStreak >= MAX_EMPTY_PAGES) break;

    await page.waitForTimeout(800 + Math.random() * 700);
  }

  return all;
}

function parseLowesMap(text) {
  const stores = [];
  const categories = [];
  for (const rawLine of text.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith('#')) continue;
    if (!line.startsWith('http')) continue;
    if (line.includes('/store/')) {
      try {
        const url = new URL(line);
        const parts = url.pathname.split('/').filter(Boolean);
        const store_id = parts[parts.length - 1];
        const nameRaw = parts[parts.length - 2] || store_id;
        const name = nameRaw.replace(/-/g, ' ');
        const stateCity = parts[parts.length - 3] || '';
        const [state, city] = stateCity.split('-');
        stores.push({ store_id, name, state, city, url: line });
      } catch {
        continue;
      }
    } else if (line.includes('/pl/')) {
      const url = line;
      if (/the-back-aisle/i.test(url)) continue;
      const slug = url.split('/pl/')[1] || url;
      const name = decodeURIComponent(slug.split('/')[0]).replace(/-/g, ' ');
      categories.push({ name, url });
    }
  }
  return { stores, categories };
}

function loadDefaults() {
  const candidate = [
    path.join(__dirname, '..', 'input', 'LowesMap.txt'),
    path.join(__dirname, '..', 'LowesMap.txt'),
  ];
  for (const filePath of candidate) {
    if (fs.existsSync(filePath)) {
      const raw = fs.readFileSync(filePath, 'utf8');
      const parsed = parseLowesMap(raw);
      if (parsed.stores.length && parsed.categories.length) return parsed;
    }
  }
  return { stores: [], categories: [] };
}

const CHROME_ARGS = [
  '--disable-blink-features=AutomationControlled',
  '--disable-dev-shm-usage',
  '--disable-features=IsolateOrigins,site-per-process',
  '--disable-infobars',
  '--lang=en-US',
  '--no-default-browser-check',
  '--start-maximized',
  '--window-size=1440,960',
];

// CRITICAL: Use real Chrome, not Chromium, to bypass Akamai
// Chromium has detectable TLS/JA3 fingerprints
const DEFAULT_BROWSER_CHANNEL = 'chrome';

// Human-like mouse movement to bypass behavioral detection
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

// Warm up browser session to establish trust with Akamai
async function warmUpSession(page) {
  log.info('Warming up browser session...');

  // Load homepage first
  await page.goto(BASE_URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(3000 + Math.random() * 2000);

  // Simulate human behavior
  await humanMouseMove(page);
  await page.waitForTimeout(1000 + Math.random() * 1000);
  await humanScroll(page);
  await page.waitForTimeout(1500 + Math.random() * 1500);
  await humanMouseMove(page);
  await page.waitForTimeout(500 + Math.random() * 500);

  log.info('Session warm-up complete');
}

async function scrapeStore(store, categories, proxyUrl, maxPages, requirePickup) {
  const cdpUrl = process.env.CHEAPSKATER_CDP_URL;
  // Use Chrome by default, override with CHEAPSKATER_BROWSER_CHANNEL env var
  const channel = process.env.CHEAPSKATER_BROWSER_CHANNEL || DEFAULT_BROWSER_CHANNEL;
  // Use persistent profile by default for better Akamai bypass
  const usePersistentProfile = process.env.CHEAPSKATER_PERSISTENT_PROFILE !== '0';

  let browser = null;
  let context = null;
  let page = null;

  if (cdpUrl) {
    browser = await chromium.connectOverCDP(cdpUrl);
    if (browser.contexts().length) {
      context = browser.contexts()[0];
      page = context.pages()[0] || await context.newPage();
    } else {
      context = await browser.newContext();
      page = await context.newPage();
    }
  } else if (usePersistentProfile) {
    // CRITICAL: Use persistent context to bypass Akamai behavioral detection
    // Akamai trusts browsers with consistent profiles over fresh instances
    const storeId = store.store_id || 'default';
    const profileDir = path.join(process.cwd(), '.playwright-profiles', `store_${storeId}`);

    log.info(`Using persistent profile at: ${profileDir}`);

    context = await chromium.launchPersistentContext(profileDir, {
      headless: false,
      channel: channel,
      viewport: { width: 1440, height: 900 },
      locale: 'en-US',
      timezoneId: 'America/Los_Angeles',
      args: CHROME_ARGS,
      ...(proxyUrl ? { proxy: { server: proxyUrl } } : {}),
    });

    page = context.pages()[0] || await context.newPage();
    browser = null; // Persistent context manages its own browser
  } else {
    const launchOptions = {
      headless: false,
      args: CHROME_ARGS,
      channel: channel, // Always use Chrome channel
    };
    if (proxyUrl) launchOptions.proxy = { server: proxyUrl };

    browser = await chromium.launch(launchOptions);
    context = await newInjectedContext(browser, {
      fingerprintOptions: {
        devices: ['desktop'],
        operatingSystems: ['windows', 'macos'],
      },
    });
    page = await context.newPage();
  }

  await setupRequestBlocking(page);

  // Warm up session with human-like behavior before scraping
  await warmUpSession(page);

  const storeSet = await setStoreContext(page, store);
  if (!storeSet) {
    log.warning(`Store context not set for ${store.store_id || store.name}`);
  }

  const allResults = [];
  for (const category of categories) {
    const items = await scrapeCategory(page, store, category, maxPages, requirePickup);
    if (items.length) {
      await Actor.pushData(items);
      allResults.push(...items);
    }
    await page.waitForTimeout(1200 + Math.random() * 1200);
  }

  await context.close().catch(() => {});
  if (!cdpUrl && browser) {
    await browser.close().catch(() => {});
  }
  return allResults.length;
}

function readLocalInputFallback() {
  const base = process.env.APIFY_LOCAL_STORAGE_DIR || path.join(process.cwd(), 'apify_storage');
  const filePath = path.join(base, 'key_value_stores', 'default', 'INPUT.json');
  if (!fs.existsSync(filePath)) return {};
  try {
    const raw = fs.readFileSync(filePath, 'utf8');
    return JSON.parse(raw);
  } catch {
    return {};
  }
}

Actor.main(async () => {
  let input = (await Actor.getInput()) || {};
  if (!input || Object.keys(input).length === 0) {
    input = readLocalInputFallback();
  }
  const defaults = loadDefaults();

  const defaultStores = defaults.stores;
  const defaultCategories = defaults.categories;

  let stores = defaultStores;
  if (Array.isArray(input.stores) && input.stores.length) {
    stores = input.stores;
  } else if (Array.isArray(input.store_ids) && input.store_ids.length) {
    const desired = new Set(input.store_ids.map((id) => String(id)));
    const matched = defaultStores.filter((store) => desired.has(String(store.store_id)));
    stores = matched.length ? matched : input.store_ids.map((id) => ({ store_id: String(id) }));
  }

  let rawCategories = defaultCategories;
  if (Array.isArray(input.categories) && input.categories.length) {
    rawCategories = input.categories;
  } else if (Array.isArray(input.category_urls) && input.category_urls.length) {
    rawCategories = input.category_urls.map((url) => ({ url }));
  }
  if (rawCategories.length && typeof rawCategories[0] === 'string') {
    rawCategories = rawCategories.map((url) => ({ url }));
  }
  const categories = rawCategories.filter((cat) => !/the-back-aisle/i.test(cat.url || ''));
  if (categories.length !== rawCategories.length) {
    log.warning('Removed Back Aisle categories from input/defaults');
  }
  if (!stores.length || !categories.length) {
    throw new Error('No stores or categories found. Provide input or ensure LowesMap.txt exists.');
  }

  const concurrency = Number.isFinite(input.concurrency) ? input.concurrency : 3;
  const requirePickup = Boolean(input.require_pickup_filter);
  const maxPages = Number.isFinite(input.max_pages_per_category)
    ? input.max_pages_per_category
    : Number.MAX_SAFE_INTEGER;

  const proxyConfiguration = await Actor.createProxyConfiguration({
    groups: ['RESIDENTIAL'],
    countryCode: input.proxy_country_code || 'US',
  }).catch(() => null);

  log.info(`Input keys: ${Object.keys(input).join(', ') || 'none'}`);
  log.info(`Stores: ${stores.length}`);
  log.info(`Categories: ${categories.length}`);
  log.info(`Concurrency: ${concurrency}`);

  const pLimit = pLimitImport.default ? pLimitImport.default : pLimitImport;
  const limit = pLimit(Math.max(1, concurrency));
  const tasks = stores.map((store) => limit(async () => {
    const sessionId = store.store_id ? `lowes_${store.store_id}` : undefined;
    const proxyUrl = proxyConfiguration
      ? await proxyConfiguration.newUrl(sessionId)
      : null;

    log.info(`STORE ${store.store_id || store.name}`);
    const count = await scrapeStore(store, categories, proxyUrl, maxPages, requirePickup);
    log.info(`STORE ${store.store_id || store.name} complete: ${count} items`);
  }));

  await Promise.all(tasks);
  log.info('SCRAPING COMPLETE');
});
