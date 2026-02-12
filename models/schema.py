from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from datetime import datetime, date


class FlightQuery(BaseModel):
    """User's flight search query parsed by LLM"""
    from_city: str = Field(..., description="Departure city")
    to_city: str = Field(..., description="Arrival city")
    departure_date: date = Field(..., description="Date of travel in YYYY-MM-DD format")
    raw_query: str = Field(..., description="Original user query")


class Flight(BaseModel):
    """Normalized flight information from any scraper"""
    airline: str = Field(..., description="Airline name")
    price: float = Field(..., description="Price in INR")
    departure_time: Optional[str] = Field(None, description="Departure time (HH:MM format)")
    arrival_time: Optional[str] = Field(None, description="Arrival time (HH:MM format)")
    duration: Optional[str] = Field(None, description="Flight duration")
    stops: Optional[int] = Field(None, description="Number of stops")
    booking_url: str = Field(..., description="Direct booking URL")
    source: str = Field(..., description="Scraper source (mmt/cleartrip/emt)")
    scraped_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ScraperResult(BaseModel):
    """Result from a single scraper"""
    source: str
    flights: List[Flight]
    success: bool
    error: Optional[str] = None


class ComparisonResult(BaseModel):
    """Final comparison output"""
    query: FlightQuery
    all_flights: List[Flight]
    cheapest_flight: Optional[Flight]
    total_results: int
    sources_checked: List[str]
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }