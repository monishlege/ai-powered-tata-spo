from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import List
from pydantic import BaseModel
from datetime import datetime, timedelta
from app.models import TripConfig, Telemetry, Alert, GeoPoint
from app.core.engine import IntelligenceEngine
import os

app = FastAPI(
    title="Tata Steel Rebar Anti-Pilferage AI System",
    description="AI-Led Prevention of Pilferage in Rebar Transportation. Features: Anomaly Detection Agent, SOP Enforcement Agent.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Intelligence Engine
engine = IntelligenceEngine()

# Mount Static Files
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def read_root():
    return FileResponse(os.path.join(static_dir, "index.html"))

@app.post("/api/v1/trips", response_model=TripConfig, tags=["Trip Management"])
def register_trip(trip: TripConfig):
    engine.register_trip(trip)
    return trip

@app.post("/api/v1/telemetry", response_model=List[Alert], tags=["Telemetry Ingestion"])
def receive_telemetry(data: Telemetry):
    alerts = engine.process_telemetry(data)
    return alerts

@app.get("/api/v1/alerts", response_model=List[Alert], tags=["Monitoring"])
def get_alerts(truck_id: str = None):
    if truck_id:
        return [a for a in engine.alerts if a.truck_id == truck_id]
    return engine.alerts

@app.get("/api/v1/trucks", tags=["Monitoring"])
def get_active_trucks():
    return list(engine.active_trips.keys())

@app.get("/api/v1/fleet/summary", tags=["Monitoring"])
def get_fleet_summary():
    active_trucks = list(engine.active_trips.keys())
    total_active = len(active_trucks)
    
    # Simple logic: if a truck has alerts in the last 15 mins, it's "Under Alert"
    under_alert = 0
    # In a real app, we'd check alert timestamps. For PoC, check if alerts list is non-empty.
    for truck_id in active_trucks:
        if engine.get_alerts(truck_id):
            under_alert += 1
            
    return {
        "active_vehicles": total_active,
        "under_alert": under_alert,
        "offline": 0, # Mocked
        "data_sources": {
            "gps": "ONLINE",
            "load_cells": "ONLINE",
            "camera_feeds": "STANDBY"
        }
    }


@app.get("/api/v1/status/{truck_id}", tags=["Monitoring"])
def get_status(truck_id: str):
    if truck_id in engine.truck_states:
        return engine.truck_states[truck_id]
    raise HTTPException(status_code=404, detail="Truck not found")

class ResolveRequest(BaseModel):
    alert_id: str
class DriverInfo(BaseModel):
    truck_id: str
    driver_name: str
    phone: str
    company: str

@app.post("/api/v1/alerts/resolve", tags=["Monitoring"])
def resolve_alert(req: ResolveRequest):
    a = engine.resolve_alert(req.alert_id)
    if not a:
        raise HTTPException(status_code=404, detail="Alert not found")
    return a

@app.post("/api/v1/alerts/unresolve", tags=["Monitoring"])
def unresolve_alert(req: ResolveRequest):
    a = engine.unresolve_alert(req.alert_id)
    if not a:
        raise HTTPException(status_code=404, detail="Alert not found")
    return a

@app.get("/api/v1/driver/{truck_id}", tags=["Monitoring"])
def get_driver(truck_id: str):
    return engine.get_driver_info(truck_id)

@app.post("/api/v1/driver", tags=["Monitoring"])
def set_driver(info: DriverInfo):
    engine.set_driver_info(info.truck_id, info.driver_name, info.phone, info.company)
    return {"status": "ok"}
