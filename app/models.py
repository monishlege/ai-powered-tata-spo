from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
from datetime import datetime

class TruckStatus(str, Enum):
    MOVING = "MOVING"
    STOPPED = "STOPPED"
    IDLE = "IDLE"

class GeoPoint(BaseModel):
    latitude: float
    longitude: float

class Telemetry(BaseModel):
    truck_id: str
    timestamp: datetime
    location: GeoPoint
    weight_kg: float
    speed_kmh: float
    ignition_on: bool
    
    # Optional: We can infer status, or receive it
    status: Optional[TruckStatus] = None

class AuthorizedStop(BaseModel):
    location: GeoPoint
    radius_meters: float = 100.0
    max_duration_minutes: int
    name: str

class TripConfig(BaseModel):
    trip_id: str
    truck_id: str
    start_location: GeoPoint
    destination_location: GeoPoint
    authorized_stops: List[AuthorizedStop] = []
    total_expected_weight_kg: float
    weight_tolerance_kg: float = 10.0 # Allowed variance

class AlertType(str, Enum):
    WEIGHT_MISMATCH = "WEIGHT_MISMATCH"
    SUSPICIOUS_STOP = "SUSPICIOUS_STOP"
    ROUTE_DEVIATION = "ROUTE_DEVIATION"

class Alert(BaseModel):
    alert_id: str
    trip_id: str
    truck_id: str
    timestamp: datetime
    type: AlertType
    severity: str # HIGH, MEDIUM, LOW
    description: str
    location: GeoPoint
    
    # AI & SOP Insights
    agent_name: str  # e.g., "Weight Guard", "Stop Analyzer"
    why_flagged: str # e.g., "Stop > 15 min at non-whitelisted location"
    sop_rule: Optional[str] = None # e.g., "Unauthorized Stop Protocol"
    action_taken: Optional[str] = None # e.g., "Alert sent to Control Tower"
    status: str = "OPEN" # OPEN, RESOLVED
