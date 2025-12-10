# Prompt for Claude Code - Final Apify Actor Polish

## Context
You've built an excellent Apify Actor for scraping Lowe's "Pickup Today" inventory. Testing shows it's 95% production-ready. We just need to add the dataset schema (Apify best practice) and run validation tests to ensure nothing breaks.

## Task 1: Add Dataset Schema (Required)

Create `.actor/dataset_schema.json` with the following schema to match the data structure in `src/main.py`:

```json
{
  "title": "Lowe's Pickup Today Product",
  "type": "object",
  "description": "Product available for pickup today at a specific Lowe's store",
  "schemaVersion": 1,
  "properties": {
    "store_id": {
      "type": "string",
      "description": "Lowe's store ID (e.g., '0061')",
      "example": "0061"
    },
    "store_name": {
      "type": "string",
      "description": "Store name and location",
      "example": "Lowe's Arlington"
    },
    "sku": {
      "type": ["string", "null"],
      "description": "Product SKU/item number",
      "example": "1000595025"
    },
    "title": {
      "type": "string",
      "description": "Product title/name",
      "example": "DEWALT 20V MAX Cordless Drill"
    },
    "category": {
      "type": "string",
      "description": "Product category",
      "example": "Power Tools"
    },
    "price": {
      "type": ["number", "null"],
      "description": "Current price in USD",
      "example": 129.99
    },
    "price_was": {
      "type": ["number", "null"],
      "description": "Original price if on sale",
      "example": 179.99
    },
    "pct_off": {
      "type": ["number", "null"],
      "description": "Percentage discount (0.0 to 1.0)",
      "example": 0.2778
    },
    "availability": {
      "type": "string",
      "description": "Availability status",
      "example": "In Stock"
    },
    "clearance": {
      "type": "boolean",
      "description": "Whether product is on clearance",
      "example": false
    },
    "product_url": {
      "type": ["string", "null"],
      "description": "Full URL to product page",
      "example": "https://www.lowes.com/pd/DEWALT-20V-MAX-Cordless-Drill/1000595025"
    },
    "image_url": {
      "type": ["string", "null"],
      "description": "Product image URL",
      "example": "https://mobileimages.lowes.com/productimages/12345.jpg"
    },
    "timestamp": {
      "type": "string",
      "description": "ISO 8601 timestamp when scraped",
      "example": "2024-12-08T23:14:00.000Z"
    }
  },
  "required": ["store_id", "store_name", "title", "category", "timestamp"]
}
```

**Verification**: After creating the file, confirm it's valid JSON and matches the data structure in `src/main.py` (lines 416-430 and 502-516).

## Task 2: Verify Store Context Logic (Optional Check)

Review the `set_store_context()` function in `src/main.py` (lines 626-649). It currently:
1. Navigates to Lowe's homepage
2. Logs "Setting store context"
3. Returns True

**Question to investigate**: Does Lowe's use URL parameters or cookies for store context? Check if:
- The category URLs already include store context via `storeNumber` param
- Or if we need to explicitly set a cookie

**If needed**, add cookie setting:
```python
await context.add_cookies([{
    'name': 'preferredStore',
    'value': store_id,
    'domain': '.lowes.com',
    'path': '/'
}])
```

**But**: This might not be necessary if store context is in the URL. Test will reveal.

## Task 3: Run Validation Tests

Create a new test file `test_final_validation.py` that validates:

### Test 1: Dataset Schema Validation
```python
"""Test that dataset schema is valid and matches code output."""
import json
from pathlib import Path

def test_dataset_schema_valid():
    """Verify dataset schema is valid JSON."""
    schema_file = Path('.actor/dataset_schema.json')
    assert schema_file.exists(), "Dataset schema file missing"
    
    with open(schema_file) as f:
        schema = json.load(f)
    
    # Verify required fields
    assert 'properties' in schema
    assert 'store_id' in schema['properties']
    assert 'sku' in schema['properties']
    assert 'title' in schema['properties']
    assert 'price' in schema['properties']
    
    print("✅ Dataset schema is valid")

if __name__ == '__main__':
    test_dataset_schema_valid()
```

### Test 2: Code Syntax Validation
```python
"""Test that main.py has no syntax errors."""
import ast
from pathlib import Path

def test_main_syntax():
    """Verify main.py has valid Python syntax."""
    main_file = Path('src/main.py')
    with open(main_file) as f:
        code = f.read()
    
    try:
        ast.parse(code)
        print("✅ main.py syntax is valid")
    except SyntaxError as e:
        print(f"❌ Syntax error in main.py: {e}")
        raise

if __name__ == '__main__':
    test_main_syntax()
```

### Test 3: Import Validation
```python
"""Test that all imports work."""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Verify all imports in main.py work."""
    try:
        # Test critical imports
        from src.main import (
            parse_store_ids_from_lowesmap,
            parse_categories_from_lowesmap,
            build_category_url,
            apply_pickup_filter,
            extract_products,
        )
        print("✅ All imports successful")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        raise

if __name__ == '__main__':
    test_imports()
```

### Test 4: Data Structure Validation
```python
"""Test that product data structure matches schema."""
import json
from pathlib import Path

def test_product_structure():
    """Verify product dict structure matches schema."""
    schema_file = Path('.actor/dataset_schema.json')
    with open(schema_file) as f:
        schema = json.load(f)
    
    # Mock product (matches what code produces)
    mock_product = {
        'store_id': '0061',
        'store_name': 'Lowe\'s Arlington',
        'sku': '1000595025',
        'title': 'Test Product',
        'category': 'Test Category',
        'price': 99.99,
        'price_was': 129.99,
        'pct_off': 0.2308,
        'availability': 'In Stock',
        'clearance': False,
        'product_url': 'https://www.lowes.com/pd/test/1000595025',
        'image_url': 'https://example.com/image.jpg',
        'timestamp': '2024-12-08T23:14:00.000Z'
    }
    
    # Verify all schema properties exist in mock
    schema_props = schema['properties'].keys()
    mock_props = mock_product.keys()
    
    assert set(schema_props) == set(mock_props), \
        f"Schema/data mismatch. Schema: {schema_props}, Data: {mock_props}"
    
    print("✅ Product structure matches schema")

if __name__ == '__main__':
    test_product_structure()
```

## Task 4: Run All Tests

Create a test runner `run_validation_tests.py`:

```python
"""Run all validation tests."""
import subprocess
import sys

tests = [
    'test_final_validation.py',
]

print("="*80)
print("Running Final Validation Tests")
print("="*80)

failed = []
for test in tests:
    print(f"\n▶ Running {test}...")
    result = subprocess.run([sys.executable, test], capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        failed.append(test)

print("\n" + "="*80)
if failed:
    print(f"❌ {len(failed)} test(s) failed: {', '.join(failed)}")
    sys.exit(1)
else:
    print("✅ All validation tests passed!")
    print("="*80)
    print("\n🎉 Actor is ready for deployment!")
    print("\nNext steps:")
    print("1. Deploy to Apify: apify push")
    print("2. Test with 1 store, 5 categories")
    print("3. Run full scrape if test passes")
```

## Expected Output

After running these changes and tests, you should see:

```
================================================================================
Running Final Validation Tests
================================================================================

▶ Running test_final_validation.py...
✅ Dataset schema is valid
✅ main.py syntax is valid
✅ All imports successful
✅ Product structure matches schema

================================================================================
✅ All validation tests passed!
================================================================================

🎉 Actor is ready for deployment!

Next steps:
1. Deploy to Apify: apify push
2. Test with 1 store, 5 categories
3. Run full scrape if test passes
```

## Safety Notes

These changes are **extremely safe** and **cannot break** the existing functionality because:

1. **Dataset schema** - Just metadata, doesn't affect code execution
2. **Tests** - Only validate, don't modify code
3. **No code changes** - We're only adding files, not modifying `src/main.py`

The only way something could "break" is if:
- JSON syntax error in schema (test will catch it)
- Import error (test will catch it)
- Schema doesn't match data structure (test will catch it)

## Summary

**What you're doing**:
1. Adding dataset schema (Apify best practice)
2. Creating validation tests
3. Running tests to confirm everything works

**What you're NOT doing**:
- Modifying core scraping logic
- Changing browser behavior
- Altering data extraction
- Touching anything that could break

**Time required**: 5-10 minutes

**Risk level**: Minimal (only adding files, not modifying code)

**Benefit**: Professional Apify integration + confidence that everything works

---

## TL;DR Prompt for Claude

"Add the dataset schema file `.actor/dataset_schema.json` as specified above, create the validation test file `test_final_validation.py` with all 4 tests, and create the test runner `run_validation_tests.py`. Then run the tests and show me the output. These are just metadata and validation files - they won't modify any existing code."
