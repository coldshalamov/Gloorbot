"""
Test the parse_price function fix with real-world examples
"""
import re
from typing import Optional

def parse_price(text: Optional[str]) -> Optional[float]:
    if not text:
        return None
    
    # Find ALL numeric values in the text
    matches = re.findall(r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', str(text))
    if not matches:
        return None
    
    # Convert all matches to floats
    prices = []
    for match in matches:
        try:
            price = float(match.replace(",", ""))
            # Only consider reasonable prices (>= $1.00)
            # This filters out cents-only prices, ratings, and small metadata numbers
            if price >= 1.0:
                prices.append(price)
        except (ValueError, TypeError):
            continue
    
    # Return the largest price found (actual product price is usually the largest number)
    return max(prices) if prices else None


# Test cases based on the issue
test_cases = [
    # Case 1: The problematic case - price with "Was" price
    {
        "input": "998.00",
        "expected": 998.00,
        "description": "Simple current price"
    },
    {
        "input": "$998.00 was $1,048.00 Save 4%",
        "expected": 1048.00,  # Should get the largest price
        "description": "Price with 'was' price and percentage"
    },
    {
        "input": "4.00",
        "expected": 4.00,
        "description": "Small valid price"
    },
    {
        "input": "0.99",
        "expected": None,  # Less than $1, should be filtered
        "description": "Cents-only price (filtered)"
    },
    {
        "input": "$50.00 was $799.99 Save $749.99",
        "expected": 799.99,
        "description": "Large discount scenario"
    },
    {
        "input": "Rating: 4.1 stars, Price: $998.00",
        "expected": 998.00,
        "description": "Price with rating number"
    },
    {
        "input": "$1,234.56",
        "expected": 1234.56,
        "description": "Price with comma separator"
    },
]

print("="*70)
print("PRICE PARSING TEST SUITE")
print("="*70)
print()

passed = 0
failed = 0

for i, test in enumerate(test_cases, 1):
    result = parse_price(test["input"])
    expected = test["expected"]
    status = "✅ PASS" if result == expected else "❌ FAIL"
    
    if result == expected:
        passed += 1
    else:
        failed += 1
    
    print(f"Test {i}: {test['description']}")
    print(f"  Input:    '{test['input']}'")
    print(f"  Expected: {expected}")
    print(f"  Got:      {result}")
    print(f"  {status}")
    print()

print("="*70)
print(f"RESULTS: {passed} passed, {failed} failed out of {len(test_cases)} tests")
print("="*70)

# Test the specific issue: JSON-LD offers object
print("\n" + "="*70)
print("SIMULATING JSON-LD OFFERS OBJECT")
print("="*70)

# Simulating what might come from Lowe's JSON-LD
offers_example = {
    "price": "998.00",
    "priceWas": "1048.00"
}

current_price = parse_price(str(offers_example.get("price", "")))
was_price = parse_price(str(offers_example.get("priceWas", "")))

print(f"\nJSON-LD offers.price: '{offers_example['price']}' → ${current_price:.2f}")
print(f"JSON-LD offers.priceWas: '{offers_example['priceWas']}' → ${was_price:.2f}")

if current_price == 998.00 and was_price == 1048.00:
    print("\n✅ JSON-LD parsing works correctly!")
    print(f"   Current price: ${current_price:.2f}")
    print(f"   Was price: ${was_price:.2f}")
else:
    print(f"\n❌ JSON-LD parsing failed!")
    print(f"   Expected: price=$998.00, priceWas=$1048.00")
    print(f"   Got: price=${current_price:.2f}, priceWas=${was_price:.2f}")
