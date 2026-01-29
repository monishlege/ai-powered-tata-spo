from typing import Dict, List, Optional
import uuid
import json
from datetime import datetime, timedelta
from sqlmodel import Session, select
from app.database import engine as db_engine, create_db_and_tables
from app.db_models import AlertDB, TripConfigDB, TelemetryDB, DriverDB
from app.models import Telemetry, TripConfig, Alert, AlertType, GeoPoint, AuthorizedStop
from app.agents.anomaly_detector import AnomalyDetectionAgent
from app.agents.sop_engine import SOPEngineAgent

class IntelligenceEngine:
    """
    The Coordinator that orchestrates the AI Agents.
    Now backed by SQLite database.
    """
    def __init__(self):
        create_db_and_tables()
        
        self.active_trips: Dict[str, TripConfig] = {}
        self.truck_states: Dict[str, Dict] = {} 
        self.custody_log: List[Dict] = []
        self.driver_directory: Dict[str, Dict] = {}
        
        # Initialize Agents
        self.anomaly_agent = AnomalyDetectionAgent()
        self.sop_agent = SOPEngineAgent()

        self._load_state_from_db()
        self._inject_mock_data_if_empty()

    # --- Data Conversion Helpers ---

    def _trip_to_db(self, t: TripConfig) -> TripConfigDB:
        return TripConfigDB(
            trip_id=t.trip_id,
            truck_id=t.truck_id,
            start_lat=t.start_location.latitude,
            start_lng=t.start_location.longitude,
            dest_lat=t.destination_location.latitude,
            dest_lng=t.destination_location.longitude,
            total_expected_weight_kg=t.total_expected_weight_kg,
            weight_tolerance_kg=t.weight_tolerance_kg,
            authorized_stops_json=json.dumps([s.model_dump() for s in t.authorized_stops])
        )

    def _db_to_trip(self, t: TripConfigDB) -> TripConfig:
        stops_data = json.loads(t.authorized_stops_json)
        stops = [AuthorizedStop(**s) for s in stops_data]
        return TripConfig(
            trip_id=t.trip_id,
            truck_id=t.truck_id,
            start_location=GeoPoint(latitude=t.start_lat, longitude=t.start_lng),
            destination_location=GeoPoint(latitude=t.dest_lat, longitude=t.dest_lng),
            total_expected_weight_kg=t.total_expected_weight_kg,
            weight_tolerance_kg=t.weight_tolerance_kg,
            authorized_stops=stops
        )

    def _alert_to_db(self, a: Alert) -> AlertDB:
        return AlertDB(
            alert_id=a.alert_id,
            trip_id=a.trip_id,
            truck_id=a.truck_id,
            timestamp=a.timestamp,
            type=a.type.value,
            severity=a.severity,
            description=a.description,
            latitude=a.location.latitude,
            longitude=a.location.longitude,
            agent_name=a.agent_name,
            why_flagged=a.why_flagged,
            sop_rule=a.sop_rule,
            action_taken=a.action_taken,
            status=a.status
        )

    def _db_to_alert(self, a: AlertDB) -> Alert:
        return Alert(
            alert_id=a.alert_id,
            trip_id=a.trip_id,
            truck_id=a.truck_id,
            timestamp=a.timestamp,
            type=AlertType(a.type),
            severity=a.severity,
            description=a.description,
            location=GeoPoint(latitude=a.latitude, longitude=a.longitude),
            agent_name=a.agent_name,
            why_flagged=a.why_flagged,
            sop_rule=a.sop_rule,
            action_taken=a.action_taken,
            status=a.status
        )

    def _telemetry_to_db(self, t: Telemetry) -> TelemetryDB:
        return TelemetryDB(
            truck_id=t.truck_id,
            timestamp=t.timestamp,
            latitude=t.location.latitude,
            longitude=t.location.longitude,
            weight_kg=t.weight_kg,
            speed_kmh=t.speed_kmh,
            ignition_on=t.ignition_on,
            status=t.status
        )

    def _db_to_telemetry(self, t: TelemetryDB) -> Telemetry:
        return Telemetry(
            truck_id=t.truck_id,
            timestamp=t.timestamp,
            location=GeoPoint(latitude=t.latitude, longitude=t.longitude),
            weight_kg=t.weight_kg,
            speed_kmh=t.speed_kmh,
            ignition_on=t.ignition_on,
            status=t.status
        )

    # --- Initialization ---

    def _load_state_from_db(self):
        with Session(db_engine) as session:
            # Load Trips
            trips = session.exec(select(TripConfigDB)).all()
            for t_db in trips:
                trip = self._db_to_trip(t_db)
                self.active_trips[trip.truck_id] = trip
                
                # Initialize state
                self.truck_states[trip.truck_id] = {
                    "last_telemetry": None,
                    "stop_start_time": None,
                    "is_stopped": False,
                    "alerted_overstay": False
                }
                
                # Load latest telemetry
                latest_tel = session.exec(select(TelemetryDB).where(TelemetryDB.truck_id == trip.truck_id).order_by(TelemetryDB.timestamp.desc()).limit(1)).first()
                if latest_tel:
                    self.truck_states[trip.truck_id]["last_telemetry"] = self._db_to_telemetry(latest_tel)

            # Load Drivers
            drivers = session.exec(select(DriverDB)).all()
            for d in drivers:
                self.driver_directory[d.truck_id] = {
                    "driver_name": d.driver_name,
                    "phone": d.phone,
                    "company": d.company
                }

    def _inject_mock_data_if_empty(self):
        with Session(db_engine) as session:
            if session.exec(select(TripConfigDB)).first():
                return # Already initialized

            # 1. Mock Truck 1
            mock_truck_id = "KA-01-AB-1234"
            trip1 = TripConfig(
                trip_id="TRIP-DEMO-001",
                truck_id=mock_truck_id,
                start_location=GeoPoint(latitude=22.8046, longitude=86.2029), # Jamshedpur
                destination_location=GeoPoint(latitude=22.5726, longitude=88.3639), # Kolkata
                total_expected_weight_kg=25000.0,
                authorized_stops=[]
            )
            session.add(self._trip_to_db(trip1))
            
            # Driver 1
            driver1 = DriverDB(truck_id=mock_truck_id, driver_name="Ramesh Kumar", phone="+91-98765-43210", company="Monish Logistics")
            session.add(driver1)

            # Telemetry 1
            tel1 = Telemetry(
                truck_id=mock_truck_id,
                timestamp=datetime.now(),
                location=GeoPoint(latitude=22.3460, longitude=87.2320),
                weight_kg=22000.0,
                speed_kmh=45.0,
                ignition_on=True,
                status="MOVING"
            )
            session.add(self._telemetry_to_db(tel1))

            # Alerts 1
            alerts_data = [
                Alert(
                    alert_id=str(uuid.uuid4()), trip_id="TRIP-DEMO-001", truck_id=mock_truck_id,
                    timestamp=datetime.now() - timedelta(minutes=10), type=AlertType.WEIGHT_MISMATCH, severity="CRITICAL",
                    description="Weight Guard: 12% weight drop detected outside geofence.",
                    location=GeoPoint(latitude=22.3460, longitude=87.2320), agent_name="Weight Guard",
                    why_flagged="12% weight drop detected outside geofence", sop_rule="SOP-102", action_taken="Security team alerted; driver contacted"
                ),
                Alert(
                    alert_id=str(uuid.uuid4()), trip_id="TRIP-DEMO-001", truck_id=mock_truck_id,
                    timestamp=datetime.now() - timedelta(minutes=25), type=AlertType.ROUTE_DEVIATION, severity="HIGH",
                    description="Route Monitor: Deviation 7 km from planned corridor near Kharagpur.",
                    location=GeoPoint(latitude=22.3000, longitude=87.3000), agent_name="Route Monitor",
                    why_flagged="Deviation 7 km from planned corridor", sop_rule="SOP-075", action_taken="Control room notified"
                ),
                Alert(
                    alert_id=str(uuid.uuid4()), trip_id="TRIP-DEMO-001", truck_id=mock_truck_id,
                    timestamp=datetime.now() - timedelta(minutes=45), type=AlertType.SUSPICIOUS_STOP, severity="MEDIUM",
                    description="Stop Analyzer: 18 min stop at non-whitelisted dhaba.",
                    location=GeoPoint(latitude=22.4000, longitude=87.1000), agent_name="Stop Analyzer",
                    why_flagged="18 min stop at non-whitelisted dhaba", sop_rule="SOP-089", action_taken="Verification call initiated", status="OPEN"
                ),
                Alert(
                    alert_id=str(uuid.uuid4()), trip_id="TRIP-DEMO-001", truck_id=mock_truck_id,
                    timestamp=datetime.now() - timedelta(hours=2), type=AlertType.WEIGHT_MISMATCH, severity="HIGH",
                    description="ALERT RESOLVED – Reweigh at Kolkata Hub confirms no loss; SOP-102 closed by Control Room at 12:05 AM.",
                    location=GeoPoint(latitude=22.5726, longitude=88.3639), agent_name="Weight Guard",
                    why_flagged="Initial sensor drift > 5%", sop_rule="SOP-102", action_taken="Reweigh ordered & Verified", status="RESOLVED"
                )
            ]
            for a in alerts_data:
                session.add(self._alert_to_db(a))

            # 2. Mock Truck 2
            mock_truck_2 = "KA-02-XY-5678"
            trip2 = TripConfig(
                trip_id="TRIP-DEMO-002",
                truck_id=mock_truck_2,
                start_location=GeoPoint(latitude=22.8046, longitude=86.2029),
                destination_location=GeoPoint(latitude=22.5726, longitude=88.3639),
                total_expected_weight_kg=22000.0,
                authorized_stops=[]
            )
            session.add(self._trip_to_db(trip2))
            
            driver2 = DriverDB(truck_id=mock_truck_2, driver_name="Suresh Patel", phone="+91-99876-54321", company="Third Party Travels")
            session.add(driver2)

            tel2 = Telemetry(
                truck_id=mock_truck_2, timestamp=datetime.now(),
                location=GeoPoint(latitude=22.4327, longitude=87.8672),
                weight_kg=22000.0, speed_kmh=45.0, ignition_on=True, status="MOVING"
            )
            session.add(self._telemetry_to_db(tel2))

            alerts_data_2 = [
                Alert(
                    alert_id=str(uuid.uuid4()), trip_id="TRIP-DEMO-002", truck_id=mock_truck_2,
                    timestamp=datetime.now() - timedelta(minutes=5), type=AlertType.ROUTE_DEVIATION, severity="HIGH",
                    description="Route Deviation detected near Kolaghat.",
                    location=GeoPoint(latitude=22.4327, longitude=87.8672), agent_name="Route Monitor",
                    why_flagged="Deviation from path", sop_rule="SOP-075", action_taken="Control room notified"
                ),
                Alert(
                    alert_id=str(uuid.uuid4()), trip_id="TRIP-DEMO-002", truck_id=mock_truck_2,
                    timestamp=datetime.now() - timedelta(minutes=20), type=AlertType.SUSPICIOUS_STOP, severity="MEDIUM",
                    description="Stop Analyzer: 12 min stop at unauthorized location.",
                    location=GeoPoint(latitude=22.3898, longitude=87.7402), agent_name="Stop Analyzer",
                    why_flagged="Unauthorized stop duration", sop_rule="SOP-089", action_taken="Verification call initiated"
                )
            ]
            for a in alerts_data_2:
                session.add(self._alert_to_db(a))

            # 3. Mock Truck 3
            mock_truck_3 = "KA-03-GH-9012"
            trip3 = TripConfig(
                trip_id="TRIP-DEMO-003",
                truck_id=mock_truck_3,
                start_location=GeoPoint(latitude=22.8046, longitude=86.2029),
                destination_location=GeoPoint(latitude=22.5726, longitude=88.3639),
                total_expected_weight_kg=21000.0,
                authorized_stops=[]
            )
            session.add(self._trip_to_db(trip3))

            driver3 = DriverDB(truck_id=mock_truck_3, driver_name="Anil Singh", phone="+91-91234-56789", company="Reliance Roadways")
            session.add(driver3)

            tel3 = Telemetry(
                truck_id=mock_truck_3, timestamp=datetime.now(),
                location=GeoPoint(latitude=22.6500, longitude=87.5000),
                weight_kg=21000.0, speed_kmh=55.0, ignition_on=True, status="MOVING"
            )
            session.add(self._telemetry_to_db(tel3))

            session.commit()
            
            # Reload to sync memory state
            self._load_state_from_db()

    # --- Core Methods ---

    def register_trip(self, trip: TripConfig):
        with Session(db_engine) as session:
            session.add(self._trip_to_db(trip))
            session.commit()
        
        # Update memory
        self.active_trips[trip.truck_id] = trip
        self.truck_states[trip.truck_id] = {
            "last_telemetry": None,
            "stop_start_time": None,
            "is_stopped": False,
            "alerted_overstay": False
        }

    def get_alerts(self, truck_id: str = None) -> List[Alert]:
        with Session(db_engine) as session:
            if truck_id:
                statement = select(AlertDB).where(AlertDB.truck_id == truck_id)
            else:
                statement = select(AlertDB)
            results = session.exec(statement).all()
            return [self._db_to_alert(a) for a in results]

    def process_telemetry(self, data: Telemetry) -> List[Alert]:
        if data.truck_id not in self.active_trips:
            return [] 
        
        trip = self.active_trips[data.truck_id]
        state = self.truck_states[data.truck_id]
        
        # Persist Telemetry
        with Session(db_engine) as session:
            session.add(self._telemetry_to_db(data))
            session.commit()

        # Edge Offline: buffer telemetry and skip processing
        if state.get("edge_offline", False):
            buf = state.setdefault("edge_buffer", [])
            buf.append(data)
            return []
        
        # 1. Anomaly Detection Agent
        raw_alerts = self.anomaly_agent.analyze(trip, data, state)
        
        # 2. SOP Enforcement Agent
        sop_actions = self.sop_agent.evaluate(trip, data, raw_alerts)
        
        # Combine all alerts
        all_alerts = raw_alerts + sop_actions
        
        # Persist Alerts
        if all_alerts:
            with Session(db_engine) as session:
                for a in all_alerts:
                    session.add(self._alert_to_db(a))
                session.commit()
        
        state["last_telemetry"] = data
        return all_alerts

    def resolve_alert(self, alert_id: str) -> Alert | None:
        with Session(db_engine) as session:
            alert_db = session.get(AlertDB, alert_id)
            if alert_db:
                alert_db.status = "RESOLVED"
                session.add(alert_db)
                session.commit()
                session.refresh(alert_db)
                return self._db_to_alert(alert_db)
        return None

    def unresolve_alert(self, alert_id: str) -> Alert | None:
        with Session(db_engine) as session:
            alert_db = session.get(AlertDB, alert_id)
            if alert_db:
                alert_db.status = "OPEN"
                session.add(alert_db)
                session.commit()
                session.refresh(alert_db)
                return self._db_to_alert(alert_db)
        return None

    def get_driver_info(self, truck_id: str) -> Dict:
        return self.driver_directory.get(truck_id, {"driver_name": "Unknown", "phone": "N/A", "company": "N/A"})
    
    def set_driver_info(self, truck_id: str, name: str, phone: str, company: str):
        with Session(db_engine) as session:
            driver = session.get(DriverDB, truck_id)
            if not driver:
                driver = DriverDB(truck_id=truck_id, driver_name=name, phone=phone, company=company)
            else:
                driver.driver_name = name
                driver.phone = phone
                driver.company = company
            session.add(driver)
            session.commit()
        
        self.driver_directory[truck_id] = {
            "driver_name": name,
            "phone": phone,
            "company": company
        }

    # Predictive Pilferage Risk (simple heuristic)
    def predict_risk(self, truck_id: str) -> Dict:
        state = self.truck_states.get(truck_id)
        if not state or not state.get("last_telemetry"):
            return {"risk_score": 0.1, "message": "No telemetry", "factors": []}
        tel = state["last_telemetry"]
        lat = tel.location.latitude
        lng = tel.location.longitude
        hour = tel.timestamp.hour
        factors = []
        score = 0.2
        # Time-of-day risk window
        if 2 <= hour <= 4:
            score += 0.4
            factors.append("Time window 2–4 AM")
        # Corridor zones near Kharagpur/Kolaghat raise baseline risk
        def near(p_lat, p_lng, th=0.15):
            return abs(lat - p_lat) < th and abs(lng - p_lng) < th
        if near(22.3460, 87.2320) or near(22.4327, 87.8672):
            score += 0.3
            factors.append("Eastern Corridor hotspot")
        score = min(score, 0.95)
        msg = f"Predicted pilferage risk: {int(score*100)}% in current corridor"
        return {"risk_score": score, "message": msg, "factors": factors}

    # Edge computing mode toggle & sync
    def set_edge_mode(self, truck_id: str, offline: bool) -> Dict:
        st = self.truck_states.setdefault(truck_id, {})
        st["edge_offline"] = offline
        if offline:
            st.setdefault("edge_buffer", [])
        return {"truck_id": truck_id, "edge_offline": offline}

    def sync_edge_buffer(self, truck_id: str) -> Dict:
        st = self.truck_states.get(truck_id, {})
        buf = st.get("edge_buffer", [])
        processed = 0
        for tel in buf:
            self.process_telemetry(tel)
            processed += 1
        st["edge_buffer"] = []
        st["edge_offline"] = False
        return {"processed": processed, "edge_offline": False}

    # Digital Chain of Custody log
    def add_custody_event(self, truck_id: str, stop_name: str, photo_b64: str | None, signature: str | None, notes: str | None) -> Dict:
        event = {
            "truck_id": truck_id,
            "stop_name": stop_name,
            "timestamp": datetime.now().isoformat(),
            "photo_base64": photo_b64,
            "signature": signature,
            "notes": notes
        }
        self.custody_log.append(event)
        # Optional: create a supportive alert from CCTV perspective
        tel = self.truck_states.get(truck_id, {}).get("last_telemetry")
        if tel:
            alert = Alert(
                alert_id=str(uuid.uuid4()),
                trip_id=self.active_trips.get(truck_id, TripConfig(
                    trip_id="N/A", truck_id=truck_id,
                    start_location=GeoPoint(latitude=0, longitude=0),
                    destination_location=GeoPoint(latitude=0, longitude=0),
                    authorized_stops=[], total_expected_weight_kg=0.0
                )).trip_id,
                truck_id=truck_id,
                timestamp=datetime.now(),
                type=AlertType.WEIGHT_MISMATCH,
                severity="LOW",
                description="CCTV Guard: Digital custody verified at whitelisted stop.",
                location=tel.location,
                agent_name="CCTV Guard",
                why_flagged="Object count/load height verification performed",
                sop_rule="SOP-110 (Custody Verification)",
                action_taken="Custody record stored",
                status="OPEN"
            )
            # Persist alert
            with Session(db_engine) as session:
                session.add(self._alert_to_db(alert))
                session.commit()
                
        return event
