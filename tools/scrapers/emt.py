"""
EaseMyTrip Scraper - COMPLETE VERSION
- Extracts flight code (IX-1463) from span.txt-r5
- Saves to JSON file: emt_flight_details.json
- Includes platform name: "Ease My Trip"
"""
import asyncio
import os
import re
import json
from datetime import datetime
from playwright.async_api import async_playwright
from models.schema import FlightQuery, Flight, ScraperResult


CITY_TO_CODE = {
    'delhi': 'DEL', 'new delhi': 'DEL', 'mumbai': 'BOM',
    'bangalore': 'BLR', 'bengaluru': 'BLR', 'chennai': 'MAA',
    'kolkata': 'CCU', 'hyderabad': 'HYD', 'pune': 'PNQ',
    'ahmedabad': 'AMD', 'goa': 'GOI', 'jaipur': 'JAI',
    'lucknow': 'LKO', 'chandigarh': 'IXC', 'kochi': 'COK',
    'cochin': 'COK', 'guwahati': 'GAU', 'srinagar': 'SXR',
    'varanasi': 'VNS', 'bhubaneswar': 'BBI', 'indore': 'IDR',
    'patna': 'PAT', 'nagpur': 'NAG', 'trivandrum': 'TRV',
}

CODE_TO_FULL_NAME = {
    'DEL': 'Delhi', 'BOM': 'Mumbai', 'BLR': 'Bangalore', 'MAA': 'Chennai',
    'CCU': 'Kolkata', 'HYD': 'Hyderabad', 'PNQ': 'Pune', 'AMD': 'Ahmedabad',
    'GOI': 'Goa', 'JAI': 'Jaipur', 'LKO': 'Lucknow', 'IXC': 'Chandigarh',
    'COK': 'Kochi', 'GAU': 'Guwahati', 'SXR': 'Srinagar', 'VNS': 'Varanasi',
    'BBI': 'Bhubaneswar', 'IDR': 'Indore', 'PAT': 'Patna', 'NAG': 'Nagpur',
    'TRV': 'Trivandrum',
}


async def scrape_easemytrip(query: FlightQuery) -> ScraperResult:
    from_city_lower = query.from_city.lower()
    to_city_lower = query.to_city.lower()
    
    from_code = CITY_TO_CODE.get(from_city_lower, query.from_city.upper()[:3])
    to_code = CITY_TO_CODE.get(to_city_lower, query.to_city.upper()[:3])
    from_city_full = CODE_TO_FULL_NAME.get(from_code, query.from_city.capitalize())
    to_city_full = CODE_TO_FULL_NAME.get(to_code, query.to_city.capitalize())
    
    date_str = query.departure_date.strftime("%d/%m/%Y")
    search_param = f"{from_code}-{from_city_full}-India|{to_code}-{to_city_full}-India|{date_str}"
    url = f"https://flight.easemytrip.com/FlightList/Index?srch={search_param}&px=1-0-0&cbn=0&ar=undefined&isow=true&isdm=true&lang="
    
    print(f"[EMT] 🔍 {from_code} → {to_code} | {date_str}")
    
    user_data_dir = os.path.abspath("./emt_session")

    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch_persistent_context(
                user_data_dir, headless=False, channel="chrome", 
                args=["--start-maximized", "--disable-blink-features=AutomationControlled"],
                viewport=None
            )
        except:
            browser = await p.chromium.launch_persistent_context(
                user_data_dir, headless=False,
                args=["--start-maximized", "--disable-blink-features=AutomationControlled"],
                viewport=None
            )
            
        page = browser.pages[0]
        
        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=60000)
            print("[EMT] ⏳ Page loaded, waiting for results...")
            
            # Wait for flights to load
            await asyncio.sleep(5)
            
            # Take screenshot
            await page.screenshot(path="emt_loaded.png", full_page=False)
            
            # ============= EXTRACTION WITH FLIGHT CODE =============
            print("[EMT] 📊 Extracting flights with flight codes...")
            
            flights_data = await page.evaluate('''() => {
                const results = [];
                
                // Find first 5 price elements
                for (let i = 0; i < 5; i++) {
                    try {
                        const priceSpan = document.querySelector(`span[id="spnPrice${i}"][price]`);
                        
                        if (!priceSpan) {
                            console.log(`spnPrice${i} not found`);
                            continue;
                        }
                        
                        // Get price
                        const priceAttr = priceSpan.getAttribute('price');
                        const price = priceAttr ? parseInt(priceAttr) : null;
                        
                        if (!price || price < 1000 || price > 150000) {
                            console.log(`Invalid price for flight ${i}:`, price);
                            continue;
                        }
                        
                        // Find the parent flight row
                        let flightRow = priceSpan;
                        for (let j = 0; j < 15; j++) {
                            flightRow = flightRow.parentElement;
                            if (!flightRow) break;
                            
                            const rowText = flightRow.textContent || '';
                            
                            // Check if this is a complete flight row
                            const hasAirline = flightRow.querySelector('span.txt-r4.ng-binding');
                            const times = rowText.match(/\\d{2}:\\d{2}/g);
                            
                            if (hasAirline && times && times.length >= 2) {
                                // Extract airline
                                const airlineSpan = flightRow.querySelector('span.txt-r4.ng-binding');
                                let airline = airlineSpan ? airlineSpan.textContent.trim() : 'Unknown';
                                airline = airline.replace(/\\n/g, ' ').replace(/\\s+/g, ' ').trim();
                                
                                // ========= EXTRACT FLIGHT CODE =========
                                // From screenshot: <span class="txt-r5">IX-1463</span>
                                let flightCode = 'N/A';
                                const flightCodeSpan = flightRow.querySelector('span.txt-r5');
                                if (flightCodeSpan) {
                                    flightCode = flightCodeSpan.textContent.trim();
                                    console.log(`Flight ${i} code:`, flightCode);
                                }
                                
                                // If flight code not found in txt-r5, try to extract from text
                                if (flightCode === 'N/A') {
                                    // Look for pattern like "6E-", "IX-", "AI-", etc.
                                    const codeMatch = rowText.match(/\\b([A-Z0-9]{2})-?\\s*\\d{3,4}\\b/);
                                    if (codeMatch) {
                                        flightCode = codeMatch[0];
                                    }
                                }
                                
                                // Extract times
                                const departureTime = times[0] || 'N/A';
                                const arrivalTime = times[1] || 'N/A';
                                
                                // Extract duration
                                const durationMatch = rowText.match(/(\\d{2}h\\s*\\d{2}m)/);
                                const duration = durationMatch ? durationMatch[1] : 'N/A';
                                
                                // Extract stops
                                let stops = 0;
                                if (rowText.includes('Non-stop') || rowText.includes('Nonstop')) {
                                    stops = 0;
                                } else if (rowText.includes('1 Stop') || rowText.includes('1-Stop')) {
                                    stops = 1;
                                } else if (rowText.includes('2 Stop') || rowText.includes('2-Stop')) {
                                    stops = 2;
                                }
                                
                                // Extract cities
                                const cityElements = flightRow.querySelectorAll('.txt-r3-n.ng-binding');
                                const departureCity = cityElements[0] ? cityElements[0].textContent.trim() : 'N/A';
                                const arrivalCity = cityElements[1] ? cityElements[1].textContent.trim() : 'N/A';
                                
                                results.push({
                                    index: i,
                                    airline,
                                    flightCode,
                                    price,
                                    departureTime,
                                    arrivalTime,
                                    duration,
                                    stops,
                                    departureCity,
                                    arrivalCity
                                });
                                
                                console.log(`Flight ${i}: ${airline} ${flightCode}, ${departureTime}->${arrivalTime}, ₹${price}`);
                                break;
                            }
                        }
                    } catch (err) {
                        console.error(`Error extracting flight ${i}:`, err);
                    }
                }
                
                return results;
            }''')
            
            if not flights_data or len(flights_data) == 0:
                print("[EMT] ❌ Could not extract any flights")
                await browser.close()
                return ScraperResult(
                    success=False, 
                    source="easemytrip", 
                    error="Could not extract flights",
                    flights=[]
                )
            
            # ============= CREATE JSON OUTPUT =============
            json_data = {
                "platform": "Ease My Trip",
                "search_query": {
                    "from": query.from_city,
                    "to": query.to_city,
                    "date": query.departure_date.strftime("%Y-%m-%d"),
                    "search_url": url
                },
                "scraped_at": datetime.now().isoformat(),
                "total_flights": len(flights_data),
                "flights": []
            }
            
            # Create flight objects and JSON entries
            flights = []
            print(f"\n[EMT] {'='*60}")
            print(f"[EMT] ✅ EXTRACTED {len(flights_data)} FLIGHTS:")
            print(f"[EMT] {'='*60}")
            
            for idx, data in enumerate(flights_data, 1):
                print(f"\n[EMT] Flight #{idx}:")
                print(f"[EMT]   Airline: {data['airline']} ({data['flightCode']})")
                print(f"[EMT]   Price: ₹{data['price']:,}")
                print(f"[EMT]   Route: {data['departureCity']} → {data['arrivalCity']}")
                print(f"[EMT]   Times: {data['departureTime']} → {data['arrivalTime']}")
                print(f"[EMT]   Duration: {data['duration']}")
                print(f"[EMT]   Stops: {data['stops']}")
                
                flight = Flight(
                    airline=data['airline'],
                    price=float(data['price']),
                    departure_time=data['departureTime'],
                    arrival_time=data['arrivalTime'],
                    duration=data['duration'],
                    stops=data['stops'],
                    source="easemytrip",
                    booking_url=url
                )
                flights.append(flight)
                
                # Add to JSON
                json_data["flights"].append({
                    "flight_number": idx,
                    "platform": "Ease My Trip",
                    "airline": data['airline'],
                    "flight_code": data['flightCode'],
                    "departure": {
                        "time": data['departureTime'],
                        "city": data['departureCity']
                    },
                    "arrival": {
                        "time": data['arrivalTime'],
                        "city": data['arrivalCity']
                    },
                    "duration": data['duration'],
                    "stops": data['stops'],
                    "price": {
                        "amount": data['price'],
                        "currency": "INR",
                        "formatted": f"₹{data['price']:,}"
                    },
                    "booking_url": url
                })
            
            # Save JSON file
            json_filename = "emt_flight_details.json"
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            
            print(f"\n[EMT] {'='*60}")
            print(f"[EMT] 💾 Saved flight details to: {json_filename}")
            print(f"[EMT] {'='*60}\n")
            
            await page.screenshot(path="emt_success.png", full_page=True)
            await browser.close()
            
            return ScraperResult(
                success=True,
                source="easemytrip",
                flights=flights,
                error=None
            )

        except Exception as e:
            print(f"[EMT] ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            try:
                await page.screenshot(path="emt_error.png", full_page=True)
            except:
                pass
            await browser.close()
            return ScraperResult(success=False, source="easemytrip", error=str(e), flights=[])