"""
MakeMyTrip Scraper - COMPLETE VERSION
- Extracts flight code (IX 1463)
- Saves to JSON file: mmt_flight_details.json
- Includes platform name: "Make My Trip"
"""
import asyncio
import os
import re
import json
from datetime import datetime
from playwright.async_api import async_playwright
from models.schema import FlightQuery, Flight, ScraperResult


async def scrape_makemytrip(query: FlightQuery) -> ScraperResult:
    # URL Construction
    d = query.departure_date
    date_str = f"{d.day:02d}/{d.month:02d}/{d.year}"
    url = f"https://www.makemytrip.com/flight/search?itinerary={query.from_city}-{query.to_city}-{date_str}&tripType=O&paxType=A-1_C-0_I-0&intl=false&cabinClass=E"
    
    print(f"[MMT] 🔍 Navigating to: {url}")
    
    user_data_dir = os.path.abspath("./mmt_session")
    
    async with async_playwright() as p:
        context = None
        try:
            try:
                context = await p.chromium.launch_persistent_context(
                    user_data_dir,
                    headless=False,
                    channel="chrome",
                    args=["--start-maximized","--disable-http2", "--disable-blink-features=AutomationControlled"],
                    viewport=None
                )
            except Exception:
                context = await p.chromium.launch_persistent_context(
                    user_data_dir,
                    headless=False,
                    args=["--start-maximized", "--disable-blink-features=AutomationControlled"],
                    viewport=None
                )
            
            page = context.pages[0]
            
            await page.goto(url, timeout=100000)
            print("[MMT] ⏳ Page loaded, waiting for flight results...")
            
            # Anti-Bot Check
            content = await page.content()
            if "200-OK" in content and len(content) < 200:
                print("❌ [MMT] Bot Trap Detected (200-OK).")
                return ScraperResult(success=False, source="makemytrip", error="Bot Trap 200-OK", flights=[])

            # Wait for flight listings
            try:
                await page.wait_for_selector('.listingCard', timeout=45000)
                print("[MMT] ✓ Flight listings loaded")
                await asyncio.sleep(3)
            except:
                print("[MMT] ❌ Timeout waiting for flight listings")
                return ScraperResult(success=False, source="makemytrip", error="Timeout", flights=[])

            # Take screenshot
            await page.screenshot(path="mmt_loaded.png", full_page=False)

            # ============= EXTRACT WITH FLIGHT CODE =============
            print("[MMT] 📊 Extracting flights with flight codes...")
            
            flights_data = await page.evaluate('''() => {
                const results = [];
                
                let flightCards = document.querySelectorAll('.listingCard');
                console.log('Found', flightCards.length, 'flight cards');
                
                for (let i = 0; i < Math.min(5, flightCards.length); i++) {
                    try {
                        const card = flightCards[i];
                        const cardText = card.textContent || '';
                        
                        // Extract airline
                        let airline = 'Unknown';
                        let airlineEl = card.querySelector('p.boldFont.blackText.airlineName');
                        if (!airlineEl) {
                            airlineEl = card.querySelector('[data-test*="airline"]');
                        }
                        if (airlineEl) {
                            airline = airlineEl.textContent.trim();
                        } else {
                            if (cardText.includes('IndiGo')) airline = 'IndiGo';
                            else if (cardText.includes('Air India Express')) airline = 'Air India Express';
                            else if (cardText.includes('Air India')) airline = 'Air India';
                            else if (cardText.includes('Vistara')) airline = 'Vistara';
                            else if (cardText.includes('SpiceJet')) airline = 'SpiceJet';
                            else if (cardText.includes('Akasa')) airline = 'Akasa Air';
                        }
                        
                        // ========= EXTRACT FLIGHT CODE =========
                        // From screenshot: <p class="fliCode">IX 1463</p>
                        let flightCode = 'N/A';
                        const flightCodeEl = card.querySelector('p.fliCode');
                        if (flightCodeEl) {
                            flightCode = flightCodeEl.textContent.trim();
                            console.log(`Flight ${i} code:`, flightCode);
                        }
                        
                        // ========= EXTRACT TIMES =========
                        let departureTime = 'N/A';
                        let arrivalTime = 'N/A';
                        
                        // Look for time elements
                        const timeElements = card.querySelectorAll(
                            'p.blackText, p.latoBlack, span.blackText, div.blackText, ' +
                            'p.fontSize14, p.fontSize16, p.fontSize18, ' +
                            '[class*="time"], [class*="Time"]'
                        );
                        
                        const timeValues = [];
                        timeElements.forEach(el => {
                            const text = el.textContent.trim();
                            if (/^\\d{2}:\\d{2}$/.test(text)) {
                                timeValues.push(text);
                            }
                        });
                        
                        // Fallback: extract from text
                        if (timeValues.length < 2) {
                            const lines = cardText.split('\\n').map(l => l.trim());
                            for (const line of lines) {
                                const matches = line.match(/\\b\\d{2}:\\d{2}\\b/g);
                                if (matches) {
                                    timeValues.push(...matches);
                                }
                            }
                        }
                        
                        // TreeWalker for deep search
                        if (timeValues.length < 2) {
                            const walker = document.createTreeWalker(
                                card,
                                NodeFilter.SHOW_TEXT,
                                null
                            );
                            
                            let node;
                            while (node = walker.nextNode()) {
                                const text = node.textContent.trim();
                                const match = text.match(/^\\d{2}:\\d{2}$/);
                                if (match && !timeValues.includes(match[0])) {
                                    timeValues.push(match[0]);
                                }
                            }
                        }
                        
                        const uniqueTimes = [...new Set(timeValues)];
                        if (uniqueTimes.length >= 2) {
                            departureTime = uniqueTimes[0];
                            arrivalTime = uniqueTimes[1];
                        } else if (uniqueTimes.length === 1) {
                            departureTime = uniqueTimes[0];
                        }
                        
                        // Extract duration
                        let duration = 'N/A';
                        let durationMatch = cardText.match(/(\\d{1,2})\\s*h\\s*(\\d{2})\\s*m/i);
                        if (durationMatch) {
                            duration = `${durationMatch[1]}h ${durationMatch[2]}m`;
                        }
                        
                        // Extract stops
                        let stops = 0;
                        const stopsLower = cardText.toLowerCase();
                        if (stopsLower.includes('non stop') || stopsLower.includes('nonstop')) {
                            stops = 0;
                        } else if (stopsLower.includes('1 stop')) {
                            stops = 1;
                        } else if (stopsLower.includes('2 stop')) {
                            stops = 2;
                        }
                        
                        // Extract price
                        let price = 0;
                        let priceEl = card.querySelector('span.fontSize18.blackFont');
                        if (!priceEl) {
                            const priceElements = card.querySelectorAll('span, div, p');
                            for (const el of priceElements) {
                                const text = el.textContent;
                                if (text.includes('₹')) {
                                    const match = text.match(/₹\\s*([\\d,]+)/);
                                    if (match) {
                                        const p = parseInt(match[1].replace(/,/g, ''));
                                        if (p >= 1000 && p <= 150000) {
                                            price = p;
                                            break;
                                        }
                                    }
                                }
                            }
                        } else {
                            const priceText = priceEl.textContent;
                            const priceMatch = priceText.match(/₹\\s*([\\d,]+)/);
                            if (priceMatch) {
                                price = parseInt(priceMatch[1].replace(/,/g, ''));
                            }
                        }
                        
                        // Extract cities
                        let departureCity = 'N/A';
                        let arrivalCity = 'N/A';
                        
                        // Look for city names - they often appear near times
                        const cityElements = card.querySelectorAll('.darkText, .appendBottom3');
                        if (cityElements.length >= 2) {
                            const cities = [];
                            cityElements.forEach(el => {
                                const text = el.textContent.trim();
                                // City names are usually capitalized and not time format
                                if (text && text.length > 2 && !/\\d{2}:\\d{2}/.test(text)) {
                                    cities.push(text);
                                }
                            });
                            if (cities.length >= 2) {
                                departureCity = cities[0];
                                arrivalCity = cities[1];
                            }
                        }
                        
                        console.log(`Flight ${i}: ${airline} ${flightCode}, ${departureTime}->${arrivalTime}, ₹${price}`);
                        
                        if (price > 0) {
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
                        console.error(`Error extracting card ${i}:`, err);
                    }
                }
                
                return results;
            }''')
            
            # Fallback: Use Playwright for missing times
            if flights_data:
                missing_times = sum(1 for f in flights_data if f['departureTime'] == 'N/A' or f['arrivalTime'] == 'N/A')
                if missing_times > 0:
                    print(f"[MMT] 🔄 {missing_times} flights missing times, trying Playwright...")
                    
                    cards = page.locator(".listingCard")
                    count = await cards.count()
                    
                    for i in range(min(len(flights_data), count)):
                        if flights_data[i]['departureTime'] == 'N/A' or flights_data[i]['arrivalTime'] == 'N/A':
                            try:
                                card = cards.nth(i)
                                time_elements = await card.locator('p.blackText, p.latoBlack, span.blackText').all()
                                
                                times = []
                                for el in time_elements:
                                    text = await el.inner_text()
                                    text = text.strip()
                                    if re.match(r'^\d{2}:\d{2}$', text):
                                        times.append(text)
                                
                                if len(times) >= 2:
                                    flights_data[i]['departureTime'] = times[0]
                                    flights_data[i]['arrivalTime'] = times[1]
                                    print(f"[MMT] ✓ Found times for flight {i}: {times[0]} → {times[1]}")
                                    
                            except Exception as e:
                                print(f"[MMT] ⚠ Could not extract times for flight {i}: {e}")
            
            if not flights_data or len(flights_data) == 0:
                print("[MMT] ❌ Could not extract any flights")
                return ScraperResult(success=False, source="makemytrip", error="Could not extract flights", flights=[])
            
            # ============= CREATE JSON OUTPUT =============
            json_data = {
                "platform": "Make My Trip",
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
            print(f"\n[MMT] {'='*60}")
            print(f"[MMT] ✅ EXTRACTED {len(flights_data)} FLIGHTS:")
            print(f"[MMT] {'='*60}")
            
            for idx, data in enumerate(flights_data, 1):
                print(f"\n[MMT] Flight #{idx}:")
                print(f"[MMT]   Airline: {data['airline']} ({data['flightCode']})")
                print(f"[MMT]   Price: ₹{data['price']:,}")
                print(f"[MMT]   Route: {data['departureCity']} → {data['arrivalCity']}")
                print(f"[MMT]   Times: {data['departureTime']} → {data['arrivalTime']}")
                print(f"[MMT]   Duration: {data['duration']}")
                print(f"[MMT]   Stops: {data['stops']}")
                
                flight = Flight(
                    airline=data['airline'],
                    price=float(data['price']),
                    departure_time=data['departureTime'],
                    arrival_time=data['arrivalTime'],
                    duration=data['duration'],
                    stops=data['stops'],
                    source="makemytrip",
                    booking_url=url
                )
                flights.append(flight)
                
                # Add to JSON
                json_data["flights"].append({
                    "flight_number": idx,
                    "platform": "Make My Trip",
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
            json_filename = "mmt_flight_details.json"
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            
            print(f"\n[MMT] {'='*60}")
            print(f"[MMT] 💾 Saved flight details to: {json_filename}")
            print(f"[MMT] {'='*60}\n")
            
            await page.screenshot(path="mmt_success.png", full_page=True)
            
            return ScraperResult(
                success=True,
                source="makemytrip",
                flights=flights
            )

        except Exception as e:
            print(f"[MMT] ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            try:
                await page.screenshot(path="mmt_error.png", full_page=True)
            except:
                pass
            return ScraperResult(success=False, source="makemytrip", error=str(e), flights=[])
        
        finally:
            # Close context properly
            if context:
                try:
                    print("[MMT] 🔒 Closing browser context...")
                    await asyncio.wait_for(context.close(), timeout=5.0)
                    print("[MMT] ✓ Browser context closed")
                except asyncio.TimeoutError:
                    print("[MMT] ⚠️ Browser close timed out, continuing anyway")
                except Exception as e:
                    print(f"[MMT] ⚠️ Error closing context: {e}")