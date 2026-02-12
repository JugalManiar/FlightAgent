import asyncio
from datetime import date, timedelta
from models.schema import FlightQuery
from tools.scrapers.mmt import scrape_makemytrip
from tools.scrapers.emt import scrape_easemytrip

async def main():
    # Create a dummy query for testing
    # Flight from Delhi (DEL) to Mumbai (BOM) 30 days from now
    travel_date = date.today() + timedelta(days=30)
    query = FlightQuery(
        from_city="IXR",
        to_city="BOM",
        departure_date=travel_date,
        raw_query="Test Query"
    )
    
    print(f"--- TESTING SCRAPERS for {travel_date} ---")
    
    # Test EMT
    print("\n1. Testing EaseMyTrip...")
    emt_res = await scrape_easemytrip(query)
    
    if emt_res.success and len(emt_res.flights) > 0:
        print(f"✅ EMT Success: Found {len(emt_res.flights)} flights")
        print(f"   Sample: {emt_res.flights[0].airline} - ₹{emt_res.flights[0].price}")
    elif emt_res.success and len(emt_res.flights) == 0:
        print(f"⚠️  EMT returned success but found 0 flights")
        print(f"   This means the page loaded but extraction failed")
    else:
        print(f"❌ EMT Failed: {emt_res.error}")
    
    # Test MMT
    print("\n2. Testing MakeMyTrip...")
    mmt_res = await scrape_makemytrip(query)
    
    if mmt_res.success and len(mmt_res.flights) > 0:
        print(f"✅ MMT Success: Found {len(mmt_res.flights)} flights")
        print(f"   Sample: {mmt_res.flights[0].airline} - ₹{mmt_res.flights[0].price}")
    elif mmt_res.success and len(mmt_res.flights) == 0:
        print(f"⚠️  MMT returned success but found 0 flights")
        print(f"   This means the page loaded but extraction failed")
    else:
        print(f"❌ MMT Failed: {mmt_res.error}")

if __name__ == "__main__":
    asyncio.run(main())