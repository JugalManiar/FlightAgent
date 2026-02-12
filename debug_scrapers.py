"""
Debug script to test scrapers with visible browser and see actual HTML
"""
import asyncio
from playwright.async_api import async_playwright
from models.schema import FlightQuery
from datetime import date


async def debug_makemytrip():
    """Debug MakeMyTrip scraper"""
    print("\n" + "="*80)
    print("DEBUGGING MAKEMYTRIP")
    print("="*80)
    
    query = FlightQuery(
        from_city="Delhi",
        to_city="Bangalore",
        departure_date=date(2025, 2, 12),
        raw_query="test"
    )
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=1000)  # Visible browser
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        page = await context.new_page()
        
        # Build URL
        from_code = "DEL"
        to_code = "BLR"
        date_str = query.departure_date.strftime("%m/%d/%Y")
        
        url = f"https://www.makemytrip.com/flight/search?itinerary={from_code}-{to_code}-{date_str}&tripType=O&paxType=A-1_C-0_I-0&intl=false&cabinClass=E"
        
        print(f"URL: {url}")
        print("Opening browser... (will stay open for 30 seconds)")
        
        await page.goto(url, wait_until='domcontentloaded', timeout=60000)
        
        # Wait and let page load
        await asyncio.sleep(10)
        
        # Try to find any flight-related elements
        print("\nSearching for flight elements...")
        
        selectors_to_try = [
            '.listingCard',
            '.fli-list',
            '[class*="flight"]',
            '[class*="Flight"]',
            '[data-cy*="flight"]',
            '.makeFlex',
            '.commonCard',
        ]
        
        for selector in selectors_to_try:
            elements = await page.query_selector_all(selector)
            if elements:
                print(f"✅ Found {len(elements)} elements with selector: {selector}")
            else:
                print(f"❌ No elements found with selector: {selector}")
        
        # Get page content to analyze
        content = await page.content()
        
        # Save HTML for inspection
        with open('debug_mmt.html', 'w', encoding='utf-8') as f:
            f.write(content)
        print("\n💾 Saved page HTML to: debug_mmt.html")
        
        # Take screenshot
        await page.screenshot(path='debug_mmt.png', full_page=True)
        print("📸 Saved screenshot to: debug_mmt.png")
        
        print("\nWaiting 30 seconds before closing... (check the browser)")
        await asyncio.sleep(30)
        
        await browser.close()


async def debug_cleartrip():
    """Debug Cleartrip scraper"""
    print("\n" + "="*80)
    print("DEBUGGING CLEARTRIP")
    print("="*80)
    
    query = FlightQuery(
        from_city="Delhi",
        to_city="Bangalore",
        departure_date=date(2025, 2, 12),
        raw_query="test"
    )
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=1000)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        page = await context.new_page()
        
        date_str = query.departure_date.strftime("%d/%m/%Y")
        url = f"https://www.cleartrip.com/flights/results?adults=1&childs=0&infants=0&class=Economy&from=DEL&to=BLR&depart_date={date_str}&intl=n"
        
        print(f"URL: {url}")
        print("Opening browser...")
        
        await page.goto(url, wait_until='domcontentloaded', timeout=60000)
        await asyncio.sleep(10)
        
        print("\nSearching for flight elements...")
        
        selectors_to_try = [
            '[data-testid="flight-card"]',
            '.flight-card',
            '[class*="flight"]',
            '[class*="Flight"]',
            '[class*="result"]',
            '.card',
        ]
        
        for selector in selectors_to_try:
            elements = await page.query_selector_all(selector)
            if elements:
                print(f"✅ Found {len(elements)} elements with selector: {selector}")
            else:
                print(f"❌ No elements found with selector: {selector}")
        
        content = await page.content()
        with open('debug_cleartrip.html', 'w', encoding='utf-8') as f:
            f.write(content)
        print("\n💾 Saved page HTML to: debug_cleartrip.html")
        
        await page.screenshot(path='debug_cleartrip.png', full_page=True)
        print("📸 Saved screenshot to: debug_cleartrip.png")
        
        print("\nWaiting 30 seconds before closing...")
        await asyncio.sleep(30)
        
        await browser.close()


async def main():
    """Run all debuggers"""
    choice = input("Which site to debug? (1=MMT, 2=Cleartrip, 3=Both): ")
    
    if choice == "1":
        await debug_makemytrip()
    elif choice == "2":
        await debug_cleartrip()
    else:
        await debug_makemytrip()
        await debug_cleartrip()


if __name__ == "__main__":
    asyncio.run(main())