# Fingerprint Suite Usage (JS/TS)

Use fingerprint-suite to generate and inject realistic browser fingerprints. This is the preferred approach for Akamai-class defenses.

## Minimal Playwright + fingerprint-injector
```ts
import { chromium } from 'playwright';
import { newInjectedContext } from 'fingerprint-injector';

const browser = await chromium.launch({ headless: false });
const context = await newInjectedContext(browser, {
  fingerprintOptions: {
    devices: ['desktop', 'mobile'],
    operatingSystems: ['windows', 'macos', 'android', 'ios'],
  },
});
const page = await context.newPage();
```

## Crawlee / Apify SDK Integration
- Enable browser fingerprinting via browser pool options.
- Keep proxies and fingerprints aligned per session.

```ts
import { PlaywrightCrawler } from 'crawlee';

const crawler = new PlaywrightCrawler({
  launchContext: { launchOptions: { headless: false } },
  browserPoolOptions: {
    useFingerprints: true,
    fingerprintOptions: {
      devices: ['desktop'],
      operatingSystems: ['windows', 'macos'],
    },
  },
});
```

## Notes
- JS/TS fingerprint-suite covers Canvas, WebGL, Audio, and header alignment.
- Python Playwright cannot use fingerprint-suite; expect lower success.
