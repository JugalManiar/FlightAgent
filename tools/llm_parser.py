import ollama
import re
import csv
import os
from datetime import datetime
from typing import Optional, Dict
from models.schema import FlightQuery

# --- CSV LOADING LOGIC (FIXED FOR MAC) ---

def load_airport_map(csv_path: str = "airport.csv") -> Dict[str, str]:
    mapping = {}
    
    # Absolute path calculation
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    full_path = os.path.join(base_dir, csv_path)

    print(f"[INIT] Reading database: {full_path}")

    try:
        with open(full_path, mode='r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            
            # Clean headers
            if reader.fieldnames:
                reader.fieldnames = [h.strip().lower() for h in reader.fieldnames]
                print(f"[DEBUG] Found Headers: {reader.fieldnames}")
            else:
                return _get_fallback_data()

            # SMART COLUMN DETECTION
            # Look for 'city', 'location', 'name'
            city_col = next((h for h in reader.fieldnames if h in ['city', 'name', 'location']), None)
            
            # Look for 'code', 'iata', 'iata_code'
            code_col = next((h for h in reader.fieldnames if h in ['code', 'iata', 'iata_code', 'airport_code']), None)

            if not city_col or not code_col:
                print(f"❌ CSV Error: Could not find city/code columns. Found: {reader.fieldnames}")
                print("Tip: Rename columns to 'city' and 'code' or 'iata'")
                return _get_fallback_data()

            for row in reader:
                if row.get(city_col) and row.get(code_col):
                    clean_city = row[city_col].strip().lower()
                    clean_code = row[code_col].strip().upper()
                    mapping[clean_city] = clean_code
                    
        print(f"[INIT] Successfully loaded {len(mapping)} airports.")
        return mapping

    except FileNotFoundError:
        print(f"⚠️ Warning: '{csv_path}' not found. Using fallback.")
        return _get_fallback_data()
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
        return _get_fallback_data()

def _get_fallback_data() -> Dict[str, str]:
    return {
        "delhi": "DEL", "mumbai": "BOM", "bangalore": "BLR", 
        "chennai": "MAA", "ranchi": "IXR", "kolkata": "CCU",
        "hyderabad": "HYD", "pune": "PNQ", "goa": "GOI"
    }

# Load data immediately
AIRPORT_MAP = load_airport_map()


# --- REST OF FILE REMAINS SAME ---
def get_airport_code(city_name: str) -> str:
    clean_name = city_name.lower().strip().replace('"', '').replace("'", "")
    
    if clean_name in AIRPORT_MAP:
        return AIRPORT_MAP[clean_name]
    
    if len(clean_name) == 3:
        return clean_name.upper()
        
    print(f"⚠️ Warning: City '{clean_name}' not found in DB. Guessing code.")
    return clean_name[:3].upper()

def parse_query_with_llama(user_query: str) -> Optional[FlightQuery]:
    try:
        prompt = _build_llama_prompt(user_query)
        response = ollama.chat(model='llama3:8b', messages=[{'role': 'user', 'content': prompt}])
        return _parse_llama_response_robust(response['message']['content'], user_query)
    except Exception as e:
        print(f"\n[LLM Error] {str(e)}")
        return None

def _build_llama_prompt(user_query: str) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    return f"""
    You are a flight data extraction API. Current Date: {today}
    Extract origin_city, destination_city, and date (YYYY-MM-DD).
    User Query: "{user_query}"
    Output Format:
    origin_city: "City Name"
    destination_city: "City Name"
    date: "YYYY-MM-DD"
    """

def _parse_llama_response_robust(text: str, raw_query: str) -> Optional[FlightQuery]:
    try:
        origin_match = re.search(r'origin_city["\s:]+["\']?([a-zA-Z\s]+?)["\']?\s*(?:$|\n|destination)', text, re.IGNORECASE)
        dest_match = re.search(r'destination_city["\s:]+["\']?([a-zA-Z\s]+?)["\']?\s*(?:$|\n|date)', text, re.IGNORECASE)
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', text)

        if not origin_match or not dest_match or not date_match:
            return None

        raw_origin = origin_match.group(1).strip()
        raw_dest = dest_match.group(1).strip()
        
        from_code = get_airport_code(raw_origin)
        to_code = get_airport_code(raw_dest)
        
        print(f"[DEBUG] Mapped '{raw_origin}' -> {from_code}, '{raw_dest}' -> {to_code}")

        return FlightQuery(
            from_city=from_code, 
            to_city=to_code,
            departure_date=datetime.strptime(date_match.group(1), '%Y-%m-%d').date(),
            raw_query=raw_query
        )
    except Exception:
        return None