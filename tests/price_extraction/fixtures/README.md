# Price Extraction Test Fixtures

This directory contains HTML fixtures for testing price extraction failure modes in the Gloorbot scraper.

## Fixture Files

Each fixture file represents a known failure scenario with realistic Lowe's product card HTML structure.

| Fixture File | Purpose | Failure Mode Tested |
|------------|----------------|------------------|
| `financing_noise.html` | Financing noise being misread as product price | DOM Extraction Failures |
| `savings_percentage.html` | Savings percentage being misread as dollar amount | DOM Extraction Failures |
| `mixed_tile_group.html` | Wrong price from mixed tile_group rows | DOM Extraction Failures |
| `price_below_dollar.html` | Price below $1 being filtered out | Price Parsing Failures |
| `absurd_price_ceiling.html` | Absurd price ceiling violation | Worker/Coordinator Validation Failures |
| `missing_image.html` | Missing image URL | Data Transformation Failures |
| `empty_title.html` | Empty or missing title | Data Transformation Failures |
| `invalid_product_url.html` | Invalid product URL | Data Transformation Failures |

## Usage

These fixtures are used in unit and integration tests to verify that price extraction logic correctly handles each failure mode.

## How to Use Fixtures

1. **Load fixture in test**: Read the HTML file content
2. **Extract expected data**: Parse the HTML to extract prices, titles, URLs, etc.
3. **Compare with actual**: Compare extracted data with expected values
4. **Verify fix**: Ensure the fix prevents the failure mode

## Example

```python
from pathlib import Path
from bs4 import BeautifulSoup

# Load fixture
fixture_path = Path(__file__).parent / "tests/price_extraction/fixtures" / "financing_noise.html"
with open(fixture_path, 'r', encoding='utf-8') as f:
    html = f.read()
    soup = BeautifulSoup(html, 'html.parser')

# Extract prices
price_elements = soup.select('[data-selector*="splp-prd-act-$"]')
print(f"Found {len(price_elements)} price elements")
```

## Notes

- Fixtures use realistic Lowe's DOM structure
- Each fixture tests a specific failure mode
- Fixtures can be extended to cover additional scenarios
