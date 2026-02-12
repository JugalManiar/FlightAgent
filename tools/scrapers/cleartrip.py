"""
Cleartrip Scraper - COMPLETE VERSION
- Extracts flight code (QP-1375)
- Saves to JSON file: cleartrip_flight_details.json
- Includes platform name: "Clear Trip"
"""
import asyncio
import os
import re
import json
from datetime import datetime
from playwright.async_api import async_playwright
from models.schema import FlightQuery, Flight, ScraperResult

CITY_TO_CODE = {
    'mumbai': 'BOM', 'bangalore': 'BLR', 'bengaluru': 'BLR',
    'delhi': 'DEL', 'new delhi': 'DEL',
    'hyderabad': 'HYD', 'chennai': 'MAA', 'kolkata': 'CCU',
    'pune': 'PNQ', 'ahmedabad': 'AMD', 'goa': 'GOI',
    'jaipur': 'JAI', 'lucknow': 'LKO', 'chandigarh': 'IXC',
    'kochi': 'COK', 'cochin': 'COK'
}

async def scrape_cleartrip(query: FlightQuery) -> ScraperResult:
    # Prepare URL
    from_code = CITY_TO_CODE.get(query.from_city.lower(), query.from_city[:3].upper())
    to_code = CITY_TO_CODE.get(query.to_city.lower(), query.to_city[:3].upper())
    
    date_str = query.departure_date.strftime("%d/%m/%Y")
    
    url = f"https://www.cleartrip.com/flights/results?adults=1&childs=0&infants=0&class=Economy&from={from_code}&to={to_code}&depart_date={date_str}&intl=n&sd=1"
    print(f"[Cleartrip] 🔍 Navigating: {url}")

    async with async_playwright() as p:
        browser = None
        context = None
        try:
            # Stealth mode
            browser = await p.chromium.launch(
                headless=False, 
                args=["--disable-blink-features=AutomationControlled", "--start-maximized"]
            )
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            
            await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            page = await context.new_page()
            
            await page.goto(url, timeout=60000)
            print("[Cleartrip] ⏳ Page loaded, waiting for results...")
            
            # Wait for prices to appear
            try:
                await page.wait_for_selector('text=₹', timeout=15000)
                print("[Cleartrip] ✓ Prices loaded")
                await asyncio.sleep(3)  # Additional wait for full render
            except:
                print("[Cleartrip] ❌ Timeout waiting for prices")
                return ScraperResult(success=False, source="cleartrip", error="Timeout waiting for prices", flights=[])
            
            # Take screenshot
            await page.screenshot(path="cleartrip_loaded.png", full_page=False)
            
            # ============= EXTRACT WITH FLIGHT CODE =============
            print("[Cleartrip] 📊 Extracting flights with flight codes...")
            
            flights_data = await page.evaluate('''() => {
                const results = [];
                const seenFlights = new Set(); // Track unique flights
                
                // Based on screenshot: Look for the parent div that contains:
                // - div.sc-aXZVg.bCDQyH.pt-1.flex.flex-between.pl-6 (this seems to be the flight card container)
                // The class pattern shows: sc-aXZVg followed by another class, with pt-1, flex, flex-between, pl-6
                
                // Strategy 1: Look for divs with the specific class pattern from screenshot
                let flightCards = document.querySelectorAll('div.sc-aXZVg.bCDQyH.pt-1.flex.flex-between.pl-6');
                
                console.log('Strategy 1 found:', flightCards.length, 'cards');
                
                // Strategy 2: If not found, look for parent containers with class starting with "sc-aXZVg" that contain flight codes
                if (flightCards.length === 0) {
                    const allDivs = document.querySelectorAll('div[class*="sc-aXZVg"]');
                    const candidates = [];
                    
                    for (const div of allDivs) {
                        const text = div.textContent || '';
                        const classes = div.className || '';
                        
                        // Must contain: flight code pattern, time pattern, price, and have flex/between classes
                        if (classes.includes('flex') && 
                            classes.includes('between') && 
                            /[A-Z0-9]{2}-\\d{3,4}/.test(text) &&
                            /\\d{2}:\\d{2}/.test(text) &&
                            text.includes('₹')) {
                            candidates.push(div);
                        }
                    }
                    
                    // Find only top-level cards (not nested)
                    const topLevel = [];
                    for (const card of candidates) {
                        let isNested = false;
                        for (const other of candidates) {
                            if (other !== card && other.contains(card)) {
                                isNested = true;
                                break;
                            }
                        }
                        if (!isNested) {
                            topLevel.push(card);
                        }
                    }
                    
                    flightCards = topLevel;
                    console.log('Strategy 2 found:', flightCards.length, 'cards');
                }
                
                // Strategy 3: Look for containers with "Flight Details" text nearby
                if (flightCards.length === 0) {
                    const flightDetailsElements = document.querySelectorAll('*');
                    const candidates = [];
                    
                    for (const el of flightDetailsElements) {
                        if (el.textContent && el.textContent.includes('Flight Details')) {
                            // Get the parent container that has the full flight info
                            let parent = el.parentElement;
                            let depth = 0;
                            while (parent && depth < 5) {
                                const text = parent.textContent || '';
                                if (/[A-Z0-9]{2}-\\d{3,4}/.test(text) && 
                                    /\\d{2}:\\d{2}/.test(text) && 
                                    text.includes('₹')) {
                                    candidates.push(parent);
                                    break;
                                }
                                parent = parent.parentElement;
                                depth++;
                            }
                        }
                    }
                    
                    // Deduplicate
                    const uniqueCandidates = [];
                    for (const card of candidates) {
                        let isDuplicate = false;
                        for (const existing of uniqueCandidates) {
                            if (existing.contains(card) || card.contains(existing)) {
                                isDuplicate = true;
                                break;
                            }
                        }
                        if (!isDuplicate) {
                            uniqueCandidates.push(card);
                        }
                    }
                    
                    flightCards = uniqueCandidates;
                    console.log('Strategy 3 found:', flightCards.length, 'cards');
                }
                
                console.log('Processing', Math.min(10, flightCards.length), 'flight cards');
                
                for (let i = 0; i < Math.min(10, flightCards.length); i++) {
                    try {
                        const card = flightCards[i];
                        const cardText = card.textContent || '';
                        
                        // ========= EXTRACT FLIGHT CODE =========
                        let flightCode = 'N/A';
                        
                        // Look for flight code in various elements
                        const codeElements = card.querySelectorAll('p, span, div');
                        for (const el of codeElements) {
                            const text = el.textContent.trim();
                            // Match pattern like "6E-6283", "QP-1375", etc.
                            if (/^[A-Z0-9]{2}-\\d{3,4}$/.test(text)) {
                                flightCode = text;
                                console.log(`Flight ${i} code:`, flightCode);
                                break;
                            }
                        }
                        
                        // Fallback: Search in card text
                        if (flightCode === 'N/A') {
                            const match = cardText.match(/\\b([A-Z0-9]{2})-?(\\d{3,4})\\b/);
                            if (match) {
                                flightCode = `${match[1]}-${match[2]}`;
                            }
                        }
                        
                        // ========= EXTRACT AIRLINE =========
                        let airline = 'Unknown';
                        const airlineNames = ['IndiGo', 'Air India Express', 'Air India', 'Vistara', 'Akasa Air', 'SpiceJet', 'Go First', 'Alliance Air'];
                        
                        for (const name of airlineNames) {
                            if (cardText.includes(name)) {
                                airline = name;
                                break;
                            }
                        }
                        
                        // ========= EXTRACT TIMES =========
                        // Look for HH:MM format
                        const timeMatches = cardText.match(/\\b\\d{2}:\\d{2}\\b/g) || [];
                        // Remove duplicates and take first two
                        const uniqueTimes = [...new Set(timeMatches)];
                        const departureTime = uniqueTimes.length > 0 ? uniqueTimes[0] : 'N/A';
                        const arrivalTime = uniqueTimes.length > 1 ? uniqueTimes[1] : 'N/A';
                        
                        // ========= EXTRACT DURATION =========
                        let duration = 'N/A';
                        const durationMatch = cardText.match(/(\\d{1,2})h\\s*(\\d{2})m/i);
                        if (durationMatch) {
                            duration = `${durationMatch[1]}h ${durationMatch[2]}m`;
                        }
                        
                        // ========= EXTRACT STOPS =========
                        let stops = 0;
                        const stopsLower = cardText.toLowerCase();
                        if (stopsLower.includes('non-stop') || stopsLower.includes('nonstop')) {
                            stops = 0;
                        } else if (stopsLower.includes('1 stop')) {
                            stops = 1;
                        } else if (stopsLower.includes('2 stop')) {
                            stops = 2;
                        }
                        
                        // ========= EXTRACT PRICE =========
                        let price = 0;
                        const priceMatches = cardText.match(/₹\\s*([\\d,]+)/g);
                        if (priceMatches) {
                            for (const match of priceMatches) {
                                const numMatch = match.match(/₹\\s*([\\d,]+)/);
                                if (numMatch) {
                                    const p = parseInt(numMatch[1].replace(/,/g, ''));
                                    // Filter: must be reasonable flight price
                                    if (p >= 1000 && p <= 150000) {
                                        price = p;
                                        break;
                                    }
                                }
                            }
                        }
                        
                        // ========= EXTRACT CITIES =========
                        let departureCity = 'N/A';
                        let arrivalCity = 'N/A';
                        
                        const cityPatterns = [
                            'Delhi', 'Mumbai', 'Bangalore', 'Chennai', 'Kolkata', 'Hyderabad',
                            'Pune', 'Ahmedabad', 'Goa', 'Jaipur', 'Lucknow', 'Kochi'
                        ];
                        
                        const foundCities = [];
                        for (const city of cityPatterns) {
                            if (cardText.includes(city)) {
                                foundCities.push(city);
                            }
                        }
                        
                        if (foundCities.length >= 2) {
                            departureCity = foundCities[0];
                            arrivalCity = foundCities[1];
                        }
                        
                        // Create unique identifier
                        const flightId = `${flightCode}-${price}-${departureTime}`;
                        
                        // Skip duplicates
                        if (seenFlights.has(flightId)) {
                            console.log(`Skipping duplicate: ${flightId}`);
                            continue;
                        }
                        
                        console.log(`Flight ${i}: ${airline} ${flightCode}, ${departureTime}->${arrivalTime}, ₹${price}`);
                        
                        if (price > 0 && departureTime !== 'N/A') {
                            seenFlights.add(flightId);
                            results.push({
                                index: i,
                                airline: airline,
                                flightCode: flightCode,
                                departureTime: departureTime,
                                arrivalTime: arrivalTime,
                                departureCity: departureCity,
                                arrivalCity: arrivalCity,
                                duration: duration,
                                stops: stops,
                                price: price
                            });
                        }
                        
                    } catch (err) {
                        console.error(`Error extracting flight ${i}:`, err);
                    }
                }
                
                return results;
            }''')
            
            if not flights_data or len(flights_data) == 0:
                print("[Cleartrip] ❌ Could not extract any flights")
                
                # Save HTML for debugging
                html_content = await page.content()
                with open("cleartrip_debug.html", "w", encoding="utf-8") as f:
                    f.write(html_content)
                print("[Cleartrip] 💾 Saved HTML to cleartrip_debug.html for debugging")
                
                return ScraperResult(
                    success=False,
                    source="cleartrip",
                    error="Could not extract flights",
                    flights=[]
                )
            
            # ============= CREATE JSON OUTPUT =============
            json_data = {
                "platform": "Clear Trip",
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
            print(f"\n[Cleartrip] {'='*60}")
            print(f"[Cleartrip] ✅ EXTRACTED {len(flights_data)} UNIQUE FLIGHTS:")
            print(f"[Cleartrip] {'='*60}")
            
            for idx, data in enumerate(flights_data, 1):
                print(f"\n[Cleartrip] Flight #{idx}:")
                print(f"[Cleartrip]   Airline: {data['airline']} ({data['flightCode']})")
                print(f"[Cleartrip]   Price: ₹{data['price']:,}")
                print(f"[Cleartrip]   Route: {data['departureCity']} → {data['arrivalCity']}")
                print(f"[Cleartrip]   Times: {data['departureTime']} → {data['arrivalTime']}")
                print(f"[Cleartrip]   Duration: {data['duration']}")
                print(f"[Cleartrip]   Stops: {data['stops']}")
                
                flight = Flight(
                    airline=data['airline'],
                    price=float(data['price']),
                    departure_time=data['departureTime'],
                    arrival_time=data['arrivalTime'],
                    duration=data['duration'],
                    stops=data['stops'],
                    source="cleartrip",
                    booking_url=url
                )
                flights.append(flight)
                
                # Add to JSON
                json_data["flights"].append({
                    "flight_number": idx,
                    "platform": "Clear Trip",
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
            json_filename = "cleartrip_flight_details.json"
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            
            print(f"\n[Cleartrip] {'='*60}")
            print(f"[Cleartrip] 💾 Saved flight details to: {json_filename}")
            print(f"[Cleartrip] {'='*60}\n")
            
            await page.screenshot(path="cleartrip_success.png", full_page=True)
            
            return ScraperResult(
                success=True,
                source="cleartrip",
                flights=flights
            )

        except Exception as e:
            print(f"[Cleartrip] ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            try:
                await page.screenshot(path="cleartrip_error.png", full_page=True)
                html_content = await page.content()
                with open("cleartrip_debug.html", "w", encoding="utf-8") as f:
                    f.write(html_content)
                print("[Cleartrip] 💾 Saved debugging files")
            except:
                pass
            return ScraperResult(success=False, source="cleartrip", error=str(e), flights=[])
        
        finally:
            # Close browser properly with timeout
            if context:
                try:
                    print("[Cleartrip] 🔒 Closing browser context...")
                    await asyncio.wait_for(context.close(), timeout=5.0)
                    print("[Cleartrip] ✓ Context closed")
                except asyncio.TimeoutError:
                    print("[Cleartrip] ⚠️ Context close timed out")
                except Exception as e:
                    print(f"[Cleartrip] ⚠️ Error closing context: {e}")
            
            if browser:
                try:
                    await asyncio.wait_for(browser.close(), timeout=5.0)
                    print("[Cleartrip] ✓ Browser closed")
                except asyncio.TimeoutError:
                    print("[Cleartrip] ⚠️ Browser close timed out")
                except Exception as e:
                    print(f"[Cleartrip] ⚠️ Error closing browser: {e}")