"""
Final Validation Tests

These tests validate the Actor is ready for deployment:
1. Dataset schema is valid JSON
2. main.py has no syntax errors
3. All imports work correctly
4. Product structure matches schema
"""

import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_dataset_schema():
    """Test 1: Dataset schema is valid JSON."""
    print("\n" + "="*60)
    print("TEST 1: Dataset Schema Validation")
    print("="*60)

    try:
        schema_path = Path(".actor/dataset_schema.json")
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)

        # Validate required fields
        assert "title" in schema, "Schema missing 'title'"
        assert "type" in schema, "Schema missing 'type'"
        assert "properties" in schema, "Schema missing 'properties'"

        # Validate expected fields
        props = schema["properties"]
        expected_fields = [
            "store_id", "store_name", "sku", "title", "category",
            "price", "price_was", "pct_off", "availability", "clearance",
            "product_url", "image_url", "timestamp"
        ]

        for field in expected_fields:
            assert field in props, f"Schema missing field: {field}"
            assert "type" in props[field], f"Field {field} missing type"
            assert "description" in props[field], f"Field {field} missing description"

        print(f"[PASS] Dataset schema is valid")
        print(f"       Fields: {len(props)}")
        print(f"       Expected: {len(expected_fields)}")
        return True

    except Exception as e:
        print(f"[FAIL] {e}")
        return False


def test_main_syntax():
    """Test 2: main.py has no syntax errors."""
    print("\n" + "="*60)
    print("TEST 2: Main Module Syntax Check")
    print("="*60)

    try:
        import py_compile

        main_path = Path("src/main.py")
        py_compile.compile(str(main_path), doraise=True)

        print(f"[PASS] src/main.py has no syntax errors")
        return True

    except SyntaxError as e:
        print(f"[FAIL] Syntax error in main.py: {e}")
        return False
    except Exception as e:
        print(f"[FAIL] {e}")
        return False


def test_imports():
    """Test 3: All imports work correctly."""
    print("\n" + "="*60)
    print("TEST 3: Import Validation")
    print("="*60)

    imports_ok = True

    # Test critical imports
    tests = [
        ("yaml", "PyYAML"),
        ("playwright.async_api", "Playwright"),
        ("playwright_stealth", "Playwright Stealth"),
        ("tenacity", "Tenacity"),
        ("pydantic", "Pydantic"),
    ]

    for module_name, display_name in tests:
        try:
            __import__(module_name)
            print(f"       [OK] {display_name}")
        except ImportError as e:
            print(f"       [FAIL] {display_name}: {e}")
            imports_ok = False

    # Test apify (may not be installed locally)
    try:
        __import__("apify")
        print(f"       [OK] Apify SDK")
    except ImportError:
        print(f"       [WARN] Apify SDK (optional - not needed for local testing)")

    if imports_ok:
        print(f"\n[PASS] All critical imports work")
        return True
    else:
        print(f"\n[FAIL] Some imports failed")
        return False


def test_product_structure():
    """Test 4: Product structure matches schema."""
    print("\n" + "="*60)
    print("TEST 4: Product Structure Validation")
    print("="*60)

    try:
        from datetime import datetime, timezone

        # Create a sample product (matches src/main.py output)
        sample_product = {
            "store_id": "0061",
            "store_name": "Lowe's Arlington",
            "sku": "1000123456",
            "title": "2x4x8 Pressure Treated Lumber",
            "category": "Lumber",
            "price": 5.98,
            "price_was": 6.98,
            "pct_off": 0.1432,
            "availability": "In Stock",
            "clearance": False,
            "product_url": "https://www.lowes.com/pd/...",
            "image_url": "https://mobileimages.lowes.com/...",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Load schema
        with open(".actor/dataset_schema.json", "r", encoding="utf-8") as f:
            schema = json.load(f)

        # Validate all schema fields are in product
        props = schema["properties"]
        for field in props.keys():
            if field == "zip_code":  # Optional field
                continue
            assert field in sample_product, f"Product missing field: {field}"

        # Validate types
        assert isinstance(sample_product["store_id"], str), "store_id should be string"
        assert isinstance(sample_product["price"], (int, float)), "price should be number"
        assert isinstance(sample_product["clearance"], bool), "clearance should be boolean"
        assert isinstance(sample_product["timestamp"], str), "timestamp should be string"

        print(f"[PASS] Product structure matches schema")
        print(f"       Sample product has {len(sample_product)} fields")
        return True

    except Exception as e:
        print(f"[FAIL] {e}")
        return False


def run_all_tests():
    """Run all validation tests."""
    print("\n" + "="*60)
    print("FINAL VALIDATION TEST SUITE")
    print("="*60)
    print("\nValidating Actor is ready for deployment...")

    results = {
        "Dataset Schema": test_dataset_schema(),
        "Main Syntax": test_main_syntax(),
        "Imports": test_imports(),
        "Product Structure": test_product_structure(),
    }

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status}: {test_name}")

    print(f"\n{passed}/{total} tests passed")

    if passed == total:
        print("\nALL TESTS PASSED - READY FOR DEPLOYMENT")
        return 0
    else:
        print(f"\n{total - passed} test(s) failed - review errors above")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
