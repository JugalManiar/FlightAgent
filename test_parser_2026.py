#!/usr/bin/env python3
"""
Test the system with correct 2026 dates
"""
import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_date_parser():
    """Test that dates are parsed correctly for 2026"""
    from tools.llm_parser import parse_query_with_llama
    
    print("=" * 80)
    print("TESTING DATE PARSER - 2026")
    print("=" * 80)
    
    test_queries = [
        "Flight from Delhi to Bangalore on 12 Feb",
        "Flight from Mumbai to Goa on 15 March",
        "I want to fly from Delhi to Mumbai on 5 Feb 2026",
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        result = parse_query_with_llama(query)
        if result:
            print(f"  ✓ Parsed successfully")
            print(f"    From: {result.from_city}")
            print(f"    To: {result.to_city}")
            print(f"    Date: {result.departure_date}")
            print(f"    Year: {result.departure_date.year}")
        else:
            print(f"  ✗ Failed to parse")


if __name__ == "__main__":
    test_date_parser()