# Lowe's Actor Local Test Results
## Test Run: 2025-12-25 16:44:00

### Summary
- **Total Tests**: 5
- **Passed**: 3
- **Failed**: 2
- **Success Rate**: 60.0%
- **Duration**: 18.9s

### Key Metrics
- **Products Found**: 0
- **Categories Tested**: 0
- **Akamai Blocks**: 2
- **Pickup Filter Successes**: 0
- **Pickup Filter Failures**: 2

### Test Results

#### ✅ Browser Launch
- **Status**: PASS
- **Message**: Browser launched successfully with anti-fingerprinting measures
- **Details**:
```json
{
  "headless": false,
  "channel": "chrome",
  "fingerprinting": true
}
```

#### ✅ Akamai Block Test
- **Status**: PASS
- **Message**: Homepage loaded successfully without blocks
- **Details**:
```json
{
  "url": "https://www.lowes.com/",
  "title": "Lowe\u2019s Home Improvement"
}
```

#### ✅ Fingerprint Uniqueness
- **Status**: PASS
- **Message**: Fingerprint generated successfully: 585c9069780f1b97...
- **Details**:
```json
{
  "fingerprint_hash": "585c9069780f1b97a3bc5a9a5b4f5adb60b8b7bde2facadbea919b4e6cd298d3",
  "screen": {
    "width": 1958,
    "height": 1154
  },
  "navigator": {
    "platform": "Win32",
    "language": "en-US",
    "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
  }
}
```

#### ❌ Pickup Filter - Clearance
- **Status**: FAIL
- **Message**: Akamai blocked category page
- **Details**:
```json
{
  "url": "https://www.lowes.com/pl/The-back-aisle/2021454685607",
  "screenshot": "C:\\Users\\User\\Documents\\GitHub\\Telomere\\Gloorbot\\lowes-apify-actor\\screenshot_blocked_Clearance.png"
}
```

#### ❌ Pickup Filter - Power Tools
- **Status**: FAIL
- **Message**: Akamai blocked category page
- **Details**:
```json
{
  "url": "https://www.lowes.com/pl/Power-tools-Tools/4294612503",
  "screenshot": "C:\\Users\\User\\Documents\\GitHub\\Telomere\\Gloorbot\\lowes-apify-actor\\screenshot_blocked_Power_Tools.png"
}
```

