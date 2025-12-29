import re

def test():
    money_re = re.compile(r"\$([0-9]{1,5})(?:\.\s*([0-9]{2}))?")
    text = "Northlight13-ft 13-in (non powered) Artificial wreath $ 35.21 $44.01 Save 20%"
    print(f"Original Text: {text}")
    print(f"Regex Matches: {money_re.findall(text)}")
    
    # Simulate the logic in scraper.py
    def money_values(text: str) -> list[float]:
        if not text:
            return []
        compact = re.sub(r"\s+", "", text)
        print(f"Compact Text: {compact}")
        vals: list[float] = []
        for m in money_re.finditer(compact):
            whole = m.group(1)
            cents = m.group(2) or "00"
            print(f"Match: {m.group(0)} -> {whole}.{cents}")
            try:
                vals.append(float(f"{whole}.{cents}"))
            except Exception:
                continue
        return vals

    vals = money_values(text)
    print(f"Values: {vals}")
    if vals:
        print(f"Min (Price): {min(vals)}")
        print(f"Max (Was): {max(vals)}")

if __name__ == "__main__":
    test()
