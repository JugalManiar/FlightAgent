import asyncio
import sys
from agent.graph import run_flight_search
from models.schema import ComparisonResult
import json

async def main():
    """
    Main entry point for flight search agent
    """
    print("DEBUG: main() function started")
    
    # Get query from command line or use default
    if len(sys.argv) > 1:
        user_query = " ".join(sys.argv[1:])
    else:
        user_query = "Flight from delhi to chennai on 12 March"
    
    print("=" * 80)
    print("FLIGHT PRICE COMPARISON AGENT")
    print("=" * 80)
    print(f"Query: {user_query}\n")
    
    try:
        print("DEBUG: About to call run_flight_search()")
        # Run the agent
        result: ComparisonResult = await run_flight_search(user_query)
        print("DEBUG: run_flight_search() completed")
        
        # Display results
        print("\n" + "=" * 80)
        print("RESULTS")
        print("=" * 80)
        print(f"\nQuery Details:")
        print(f"  From: {result.query.from_city}")
        print(f"  To: {result.query.to_city}")
        print(f"  Date: {result.query.departure_date}")
        print(f"  Year: {result.query.departure_date.year}")  # Show year explicitly
        
        print(f"\nSources Checked: {', '.join(result.sources_checked)}")
        print(f"Total Flights Found: {result.total_results}")
        
        if result.cheapest_flight:
            print("\n" + "🏆 CHEAPEST FLIGHT 🏆".center(80))
            print("-" * 80)
            cf = result.cheapest_flight
            print(f"Airline:       {cf.airline}")
            print(f"Price:         ₹{cf.price:,.2f}")
            print(f"Departure:     {cf.departure_time or 'N/A'}")
            print(f"Arrival:       {cf.arrival_time or 'N/A'}")
            print(f"Duration:      {cf.duration or 'N/A'}")
            print(f"Stops:         {cf.stops}")
            print(f"Source:        {cf.source}")
            print(f"Booking URL:   {cf.booking_url}")
            print("-" * 80)
        else:
            print("\n❌ No flights found")
            print("\nPossible reasons:")
            print("  - Websites are blocking automated browsers")
            print("  - CSS selectors need updating")
            print("  - No flights available for this route/date")
            print("  - Try running: python test_cleartrip_direct.py")
        
        # Show all flights if multiple found
        if len(result.all_flights) > 1:
            print(f"\n📋 All {len(result.all_flights)} Flights (sorted by price):")
            print("-" * 80)
            sorted_flights = sorted(result.all_flights, key=lambda f: f.price)
            for i, flight in enumerate(sorted_flights[:10], 1):  # Show top 10
                print(f"{i}. {flight.airline:20} ₹{flight.price:8,.2f} ({flight.source})")
        
        # Export to JSON
        output_file = "flight_results.json"
        with open(output_file, 'w') as f:
            json.dump(result.model_dump(), f, indent=2, default=str)
        print(f"\n💾 Full results saved to: {output_file}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    print("DEBUG: Script started, about to run asyncio.run(main())")
    try:
        asyncio.run(main())
        print("DEBUG: asyncio.run(main()) completed successfully")
    except Exception as e:
        print(f"DEBUG: Exception in asyncio.run(): {e}")
        import traceback
        traceback.print_exc()