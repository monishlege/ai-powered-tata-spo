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
import uuid
import hmac
import hashlib
import base64
import json
import time

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

# In-memory users
USERS = {}
JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret")
JWT_EXP_SECONDS = 3600

# Utilities
def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")

def _jwt(payload: dict) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    h = _b64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    p = _b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{h}.{p}".encode("utf-8")
    sig = hmac.new(JWT_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
    s = _b64url(sig)
    return f"{h}.{p}.{s}"

def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()

def _issue_token(email: str) -> str:
    now = int(time.time())
    payload = {"sub": email, "iat": now, "exp": now + JWT_EXP_SECONDS}
    return _jwt(payload)

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
    return engine.get_alerts(truck_id)

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
class CustodyEvent(BaseModel):
    truck_id: str
    stop_name: str
    photo_base64: str | None = None
    signature: str | None = None
    notes: str | None = None
class LoginRequest(BaseModel):
    email: str
    password: str
class RegisterRequest(BaseModel):
    email: str
    password: str

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

# Predictive Pilferage Risk (simple heuristic)
@app.get("/api/v1/risk/{truck_id}", tags=["AI Innovation"])
def predict_risk(truck_id: str):
    return engine.predict_risk(truck_id)

# Edge computing mode toggle
@app.post("/api/v1/edge/{truck_id}/mode", tags=["Edge"])
def set_edge_mode(truck_id: str, offline: bool = True):
    return engine.set_edge_mode(truck_id, offline)

# Edge buffer sync when signal returns
@app.post("/api/v1/edge/{truck_id}/sync", tags=["Edge"])
def sync_edge(truck_id: str):
    return engine.sync_edge_buffer(truck_id)

# Digital Chain of Custody upload
@app.post("/api/v1/custody", tags=["CCTV/Chain of Custody"])
def upload_custody(event: CustodyEvent):
    return engine.add_custody_event(event.truck_id, event.stop_name, event.photo_base64, event.signature, event.notes)

@app.post("/api/v1/auth/register", tags=["Auth"])
def register(req: RegisterRequest):
    if ("@" not in req.email) or (len(req.password) < 4):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    email = req.email.lower().strip()
    if email in USERS:
        raise HTTPException(status_code=409, detail="User already exists")
    salt = uuid.uuid4().hex
    pwd = _hash_password(req.password, salt)
    USERS[email] = {"salt": salt, "password": pwd}
    token = _issue_token(email)
    return {"token": token, "user": {"email": email}}

@app.post("/api/v1/auth/login", tags=["Auth"])
def login(req: LoginRequest):
    email = req.email.lower().strip()
    user = USERS.get(email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    hashed = _hash_password(req.password, user["salt"])
    if hashed != user["password"]:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = _issue_token(email)
    return {"token": token, "user": {"email": email}}
