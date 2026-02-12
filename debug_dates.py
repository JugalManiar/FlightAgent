#!/usr/bin/env python3
"""
Debug script to see exactly what's happening with dates
"""
import sys
import os
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.llm_parser import parse_query_with_llama
from models.schema import FlightQuery

# Test 1: Check parser output
print("=" * 80)
print("TEST 1: Parser Output")
print("=" * 80)

query_text = "Flight from Delhi to Bangalore on 12 Feb"
print(f"\nInput: {query_text}")

parsed = parse_query_with_llama(query_text)
if parsed:
    print(f"\nParsed Query:")
    print(f"  From: {parsed.from_city}")
    print(f"  To: {parsed.to_city}")
    print(f"  Date: {parsed.departure_date}")
    print(f"  Year: {parsed.departure_date.year}")
    print(f"  Month: {parsed.departure_date.month}")
    print(f"  Day: {parsed.departure_date.day}")
else:
    print("❌ Failed to parse")
    sys.exit(1)

# Test 2: Check URL generation
print("\n" + "=" * 80)
print("TEST 2: URL Generation")
print("=" * 80)

from_code = "DEL"
to_code = "BLR"

# Test different date formats
print(f"\nDate object: {parsed.departure_date}")
print(f"\nDifferent format options:")
print(f"  strftime('%d/%m/%Y'): {parsed.departure_date.strftime('%d/%m/%Y')}")
print(f"  strftime('%Y-%m-%d'): {parsed.departure_date.strftime('%Y-%m-%d')}")
print(f"  strftime('%m/%d/%Y'): {parsed.departure_date.strftime('%m/%d/%Y')}")

date_str = parsed.departure_date.strftime("%d/%m/%Y")
url = f"https://www.cleartrip.com/flights/results?adults=1&childs=0&infants=0&class=Economy&from={from_code}&to={to_code}&depart_date={date_str}&intl=n"

print(f"\nGenerated URL:")
print(f"  {url}")

# Test 3: Verify it's actually 2026
print("\n" + "=" * 80)
print("TEST 3: Year Verification")
print("=" * 80)

if parsed.departure_date.year == 2026:
    print("✅ Year is correctly set to 2026")
elif parsed.departure_date.year == 2025:
    print("❌ ERROR: Year is still 2025!")
    print("   The parser needs to be fixed")
else:
    print(f"⚠️  Unexpected year: {parsed.departure_date.year}")

# Test 4: Check if date is in the future
print("\n" + "=" * 80)
print("TEST 4: Future Date Check")
print("=" * 80)

from datetime import date as date_class
today = date_class.today()
print(f"Today's date: {today}")
print(f"Query date: {parsed.departure_date}")

if parsed.departure_date > today:
    days_diff = (parsed.departure_date - today).days
    print(f"✅ Date is {days_diff} days in the future")
else:
    days_diff = (today - parsed.departure_date).days
    print(f"❌ Date is {days_diff} days in the PAST!")
    print("   This is why Cleartrip shows the error")