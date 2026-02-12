"""
Simple test to verify Playwright and web scraping basics work
"""
import asyncio
from playwright.async_api import async_playwright


async def test_basic_scraping():
    """Test basic web scraping capability"""
    print("Testing Playwright setup...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        # Test with a simple, scraper-friendly site
        print("\n1. Testing with example.com...")
        await page.goto('https://example.com')
        title = await page.title()
        print(f"   ✅ Page title: {title}")
        
        # Test with Google Flights (more realistic)
        print("\n2. Testing with Google Flights...")
        url = "https://www.google.com/travel/flights/search?tfs=CBwQAhooEgoyMDI1LTAyLTEycgwIAxIIL20vMDlmNjFqDAj__xISCC9tLzA5ZjY3QAFIAXABggELCP___________wGYAQI"
        await page.goto(url, wait_until='domcontentloaded', timeout=60000)
        await asyncio.sleep(5)
        
        # Try to find any flight-related elements
        selectors = [
            '[class*="flight"]',
            '[class*="Flight"]', 
            '[class*="result"]',
            'li',
            'div[role="listitem"]'
        ]
        
        found_any = False
        for selector in selectors:
            elements = await page.query_selector_all(selector)
            if len(elements) > 0:
                print(f"   ✅ Found {len(elements)} elements with: {selector}")
                found_any = True
                break
        
        if not found_any:
            print("   ⚠️  No flight elements found")
        
        await page.screenshot(path='test_screenshot.png')
        print("\n3. Screenshot saved to: test_screenshot.png")
        
        print("\nBrowser will close in 10 seconds...")
        await asyncio.sleep(10)
        
        await browser.close()
        print("✅ Test complete!")


if __name__ == "__main__":
    asyncio.run(test_basic_scraping())