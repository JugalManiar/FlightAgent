#!/usr/bin/env python3
"""
Direct test of Cleartrip scraper with correct 2026 date
"""
import asyncio
import sys
import os
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.schema import FlightQuery
from tools.scrapers.cleartrip import scrape_cleartrip

async def test_cleartrip():
    """Test Cleartrip scraper directly"""
    
    print("=" * 80)
    print("DIRECT CLEARTRIP SCRAPER TEST - 2026")
    print("=" * 80)
    
    # Create query with explicit 2026 date
    query = FlightQuery(
        from_city="chennai",
        to_city="delhi",
        departure_date=date(2026, 3, 12),  # Explicitly 2026
        raw_query="Flight from Delhi to Bangalore on 12 Feb"
    )
    
    print(f"\nQuery Details:")
    print(f"  From: {query.from_city}")
    print(f"  To: {query.to_city}")
    print(f"  Date: {query.departure_date}")
    print(f"  Year: {query.departure_date.year}")
    
    # Check date format
    date_str = query.departure_date.strftime("%d/%m/%Y")
    print(f"\nFormatted date: {date_str}")
    
    # Generate URL
    url = f"https://www.cleartrip.com/flights/results?adults=1&childs=0&infants=0&class=Economy&from=DEL&to=BLR&depart_date={date_str}&intl=n"
    print(f"\nURL that will be used:")
    print(f"  {url}")
    
    print("\n" + "=" * 80)
    print("Starting scraper...")
    print("=" * 80)
    
    result = await scrape_cleartrip(query)
    
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    
    print(f"\nSuccess: {result.success}")
    print(f"Source: {result.source}")
    print(f"Flights found: {len(result.flights)}")
    
    if result.error:
        print(f"\n❌ Error: {result.error}")
    
    if result.flights:
        print(f"\n✅ Found {len(result.flights)} flights!")
        print("\nSample flights:")
        for i, flight in enumerate(result.flights[:5], 1):
            print(f"  {i}. {flight.airline}: ₹{flight.price} ({flight.departure_time} → {flight.arrival_time})")
    else:
        print("\n⚠️  No flights returned")
        print("\nPossible reasons:")
        print("  1. Date format issue with Cleartrip")
        print("  2. CSS selectors don't match current page structure")
        print("  3. Bot detection blocking the scraper")
        print("  4. No flights available for this route/date")

if __name__ == "__main__":
    asyncio.run(test_cleartrip())