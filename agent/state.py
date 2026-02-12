from typing import List, Optional, TypedDict
from models.schema import FlightQuery, Flight, ScraperResult, ComparisonResult


class AgentState(TypedDict):
    """
    State object that flows through LangGraph nodes
    
    This is the "memory" of the agent as it processes the request
    """
    # Input
    user_query: str
    
    # Parsed query
    parsed_query: Optional[FlightQuery]
    
    # Scraping results
    mmt_result: Optional[ScraperResult]
    cleartrip_result: Optional[ScraperResult]
    emt_result: Optional[ScraperResult]
    
    # Aggregated flights
    all_flights: List[Flight]
    
    # Final result
    comparison_result: Optional[ComparisonResult]
    
    # Error tracking
    errors: List[str]