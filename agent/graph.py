from langgraph.graph import StateGraph, END
from agent.state import AgentState
from models.schema import FlightQuery, Flight, ComparisonResult
from tools.llm_parser import parse_query_with_llama
from tools.scrapers import scrape_makemytrip, scrape_cleartrip, scrape_easemytrip
import asyncio
from typing import Dict, Any
from datetime import datetime


# ============= NODE FUNCTIONS =============

def parse_intent_node(state: AgentState) -> Dict[str, Any]:
    """
    Node 1: Parse user's natural language query using LLaMA
    """
    print(f"\n[PARSE] Processing query: {state['user_query']}")
    
    parsed = parse_query_with_llama(state['user_query'])
    
    if not parsed:
        return {
            "parsed_query": None,
            "errors": state.get("errors", []) + ["Failed to parse query"]
        }
    
    print(f"[PARSE] Extracted: {parsed.from_city} → {parsed.to_city} on {parsed.departure_date}")
    
    return {
        "parsed_query": parsed,
        "errors": state.get("errors", [])
    }


async def scrape_all_node(state: AgentState) -> Dict[str, Any]:
    """
    Node 2: Scrape all three websites SEQUENTIALLY (one after another)
    This is easier on system resources than parallel execution
    """
    parsed_query = state["parsed_query"]
    
    # SAFETY CHECK: If parsing failed, skip scraping
    if not parsed_query:
        return {
            "mmt_result": None,
            "cleartrip_result": None,
            "emt_result": None,
            "errors": state.get("errors", []) + ["Skipping scrape: No parsed query"]
        }
    
    print("\n[SCRAPE] Starting SEQUENTIAL scraping...")
    print("[SCRAPE] This will run one scraper at a time to reduce system load")
    
    errors = state.get("errors", [])
    
    # ============= SCRAPE 1: MakeMyTrip =============
    print("\n[SCRAPE] 1/3 - Starting MakeMyTrip...")
    try:
        mmt_result = await scrape_makemytrip(parsed_query)
        
        if mmt_result and mmt_result.success:
            print(f"[SCRAPE] ✅ MMT: Found {len(mmt_result.flights)} flights")
        elif mmt_result and not mmt_result.success:
            print(f"[SCRAPE] ❌ MMT: {mmt_result.error}")
            errors.append(f"MMT: {mmt_result.error}")
        else:
            print("[SCRAPE] ❌ MMT: No result returned")
            mmt_result = None
            errors.append("MMT: No result returned")
    except Exception as e:
        print(f"[SCRAPE] ❌ MMT Exception: {e}")
        mmt_result = None
        errors.append(f"MMT: {str(e)}")
    
    # ============= SCRAPE 2: Cleartrip =============
    print("\n[SCRAPE] 2/3 - Starting Cleartrip...")
    try:
        cleartrip_result = await scrape_cleartrip(parsed_query)
        
        if cleartrip_result and cleartrip_result.success:
            print(f"[SCRAPE] ✅ Cleartrip: Found {len(cleartrip_result.flights)} flights")
        elif cleartrip_result and not cleartrip_result.success:
            print(f"[SCRAPE] ❌ Cleartrip: {cleartrip_result.error}")
            errors.append(f"Cleartrip: {cleartrip_result.error}")
        else:
            print("[SCRAPE] ❌ Cleartrip: No result returned")
            cleartrip_result = None
            errors.append("Cleartrip: No result returned")
    except Exception as e:
        print(f"[SCRAPE] ❌ Cleartrip Exception: {e}")
        cleartrip_result = None
        errors.append(f"Cleartrip: {str(e)}")
    
    # ============= SCRAPE 3: EaseMyTrip =============
    print("\n[SCRAPE] 3/3 - Starting EaseMyTrip...")
    try:
        emt_result = await scrape_easemytrip(parsed_query)
        
        if emt_result and emt_result.success:
            print(f"[SCRAPE] ✅ EMT: Found {len(emt_result.flights)} flights")
        elif emt_result and not emt_result.success:
            print(f"[SCRAPE] ❌ EMT: {emt_result.error}")
            errors.append(f"EMT: {emt_result.error}")
        else:
            print("[SCRAPE] ❌ EMT: No result returned")
            emt_result = None
            errors.append("EMT: No result returned")
    except Exception as e:
        print(f"[SCRAPE] ❌ EMT Exception: {e}")
        emt_result = None
        errors.append(f"EMT: {str(e)}")
    
    print("\n[SCRAPE] Sequential scraping completed!")
    
    return {
        "mmt_result": mmt_result,
        "cleartrip_result": cleartrip_result,
        "emt_result": emt_result,
        "errors": errors
    }


def compare_flights_node(state: AgentState) -> Dict[str, Any]:
    """
    Node 3: Aggregate and compare all flights
    """
    print("\n[COMPARE] Aggregating results...")

    # SAFETY CHECK: If parsing failed, return error result
    if not state.get("parsed_query"):
        print("❌ Error: Cannot compare flights because query parsing failed.")
        
        # Create a dummy query object to satisfy Pydantic
        dummy_query = FlightQuery(
            from_city="ERROR", 
            to_city="ERROR", 
            departure_date=datetime.now().date(), 
            raw_query=state["user_query"]
        )
        
        error_result = ComparisonResult(
            query=dummy_query,
            all_flights=[],
            cheapest_flight=None,
            total_results=0,
            sources_checked=[],
            error="LLM Parsing Failed"
        )
        return {
            "all_flights": [],
            "comparison_result": error_result
        }
    
    all_flights = []
    sources_checked = []
    
    # Aggregate flights from all sources
    if state.get("mmt_result") and state["mmt_result"].success:
        all_flights.extend(state["mmt_result"].flights)
        sources_checked.append("makemytrip")
    
    if state.get("cleartrip_result") and state["cleartrip_result"].success:
        all_flights.extend(state["cleartrip_result"].flights)
        sources_checked.append("cleartrip")
    
    if state.get("emt_result") and state["emt_result"].success:
        all_flights.extend(state["emt_result"].flights)
        sources_checked.append("easemytrip")
    
    # Find cheapest flight
    cheapest = None
    if all_flights:
        cheapest = min(all_flights, key=lambda f: f.price)
        print(f"[COMPARE] Cheapest: {cheapest.airline} - ₹{cheapest.price} on {cheapest.source}")
    else:
        print("❌ No flights found on any platform.")
    
    # Build comparison result
    comparison = ComparisonResult(
        query=state["parsed_query"],
        all_flights=all_flights,
        cheapest_flight=cheapest,
        total_results=len(all_flights),
        sources_checked=sources_checked
    )
    
    return {
        "all_flights": all_flights,
        "comparison_result": comparison
    }


# ============= GRAPH CONSTRUCTION =============

def create_flight_agent() -> StateGraph:
    """
    Build the LangGraph workflow
    """
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("parse_intent", parse_intent_node)
    workflow.add_node("scrape_all", scrape_all_node)
    workflow.add_node("compare_flights", compare_flights_node)
    
    # Define edges
    workflow.set_entry_point("parse_intent")
    workflow.add_edge("parse_intent", "scrape_all")
    workflow.add_edge("scrape_all", "compare_flights")
    workflow.add_edge("compare_flights", END)
    
    return workflow.compile()


# ============= CONVENIENCE FUNCTION =============

async def run_flight_search(user_query: str) -> ComparisonResult:
    """
    Main entry point for running flight search
    """
    agent = create_flight_agent()
    
    initial_state = {
        "user_query": user_query,
        "parsed_query": None,
        "mmt_result": None,
        "cleartrip_result": None,
        "emt_result": None,
        "all_flights": [],
        "comparison_result": None,
        "errors": []
    }
    
    final_state = await agent.ainvoke(initial_state)
    
    return final_state["comparison_result"]