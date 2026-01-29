from typing import Optional
from sqlmodel import Field, SQLModel
from datetime import datetime

class AlertDB(SQLModel, table=True):
    alert_id: str = Field(primary_key=True)
    trip_id: str
    truck_id: str
    timestamp: datetime
    type: str
    severity: str
    description: str
    
    # Flattened GeoPoint
    latitude: float
    longitude: float
    
    agent_name: str
    why_flagged: str
    sop_rule: Optional[str] = None
    action_taken: Optional[str] = None
    status: str = "OPEN"

class TripConfigDB(SQLModel, table=True):
    trip_id: str = Field(primary_key=True)
    truck_id: str
    
    # Start Location
    start_lat: float
    start_lng: float
    
    # Destination Location
    dest_lat: float
    dest_lng: float
    
    total_expected_weight_kg: float
    weight_tolerance_kg: float = 10.0
    
    # We'll store authorized stops as a JSON string for simplicity in SQLite
    # or separate table if strictly normalized. JSON is easier for now.
    authorized_stops_json: str = "[]" 

class TelemetryDB(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    truck_id: str
    timestamp: datetime
    latitude: float
    longitude: float
    weight_kg: float
    speed_kmh: float
    ignition_on: bool
    status: Optional[str] = None

class DriverDB(SQLModel, table=True):
    truck_id: str = Field(primary_key=True)
    driver_name: str
    phone: str
    company: str
