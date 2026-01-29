from typing import Dict, List
import uuid
from datetime import datetime, timedelta
from app.models import Telemetry, TripConfig, Alert, AlertType, GeoPoint
from app.agents.anomaly_detector import AnomalyDetectionAgent
from app.agents.sop_engine import SOPEngineAgent

class IntelligenceEngine:
    """
    The Coordinator that orchestrates the AI Agents.
    """
    def __init__(self):
        self.active_trips: Dict[str, TripConfig] = {}
        self.truck_states: Dict[str, Dict] = {} 
        self.alerts: List[Alert] = []
        self.custody_log: List[Dict] = []
        self.driver_directory: Dict[str, Dict] = {
            "KA-01-AB-1234": {"driver_name": "Ramesh Kumar", "phone": "+91-98765-43210", "company": "Monish Logistics"},
            "KA-02-XY-5678": {"driver_name": "Suresh Patel", "phone": "+91-99876-54321", "company": "Third Party Travels"},
            "KA-03-GH-9012": {"driver_name": "Anil Singh", "phone": "+91-91234-56789", "company": "Reliance Roadways"}
        }
        
        # Initialize Agents
        self.anomaly_agent = AnomalyDetectionAgent()
        self.sop_agent = SOPEngineAgent()

        # Inject Mock Data for Demo
        self._inject_mock_data()

    def _inject_mock_data(self):
        # 1. Register a Mock Truck so it appears in the list
        mock_truck_id = "KA-01-AB-1234"
        self.active_trips[mock_truck_id] = TripConfig(
            trip_id="TRIP-DEMO-001",
            truck_id=mock_truck_id,
            start_location=GeoPoint(latitude=22.8046, longitude=86.2029), # Jamshedpur
            destination_location=GeoPoint(latitude=22.5726, longitude=88.3639), # Kolkata
            total_expected_weight_kg=25000.0,
            authorized_stops=[]
        )
        self.truck_states[mock_truck_id] = {
            "last_telemetry": Telemetry(
                truck_id=mock_truck_id,
                timestamp=datetime.now(),
                location=GeoPoint(latitude=22.3460, longitude=87.2320), # Kharagpur (En route)
                weight_kg=22000.0, # Light (Pilferage?)
                speed_kmh=45.0,
                ignition_on=True,
                status="MOVING"
            ),
            "stop_start_time": None,
            "is_stopped": False,
            "alerted_overstay": False
        }

        # 2. Inject Mock Alerts
        self.alerts.extend([
            Alert(
                alert_id=str(uuid.uuid4()),
                trip_id="TRIP-DEMO-001",
                truck_id=mock_truck_id,
                timestamp=datetime.now() - timedelta(minutes=10),
                type=AlertType.WEIGHT_MISMATCH,
                severity="CRITICAL",
                description="Weight Guard: 12% weight drop detected outside geofence.",
                location=GeoPoint(latitude=22.3460, longitude=87.2320),
                agent_name="Weight Guard",
                why_flagged="12% weight drop detected outside geofence",
                sop_rule="SOP-102",
                action_taken="Security team alerted; driver contacted"
            ),
            Alert(
                alert_id=str(uuid.uuid4()),
                trip_id="TRIP-DEMO-001",
                truck_id=mock_truck_id,
                timestamp=datetime.now() - timedelta(minutes=25),
                type=AlertType.ROUTE_DEVIATION,
                severity="HIGH",
                description="Route Monitor: Deviation 7 km from planned corridor near Kharagpur.",
                location=GeoPoint(latitude=22.3000, longitude=87.3000),
                agent_name="Route Monitor",
                why_flagged="Deviation 7 km from planned corridor",
                sop_rule="SOP-075",
                action_taken="Control room notified"
            ),
            Alert(
                alert_id=str(uuid.uuid4()),
                trip_id="TRIP-DEMO-001",
                truck_id=mock_truck_id,
                timestamp=datetime.now() - timedelta(minutes=45),
                type=AlertType.SUSPICIOUS_STOP,
                severity="MEDIUM",
                description="Stop Analyzer: 18 min stop at non-whitelisted dhaba.",
                location=GeoPoint(latitude=22.4000, longitude=87.1000),
                agent_name="Stop Analyzer",
                why_flagged="18 min stop at non-whitelisted dhaba",
                sop_rule="SOP-089",
                action_taken="Verification call initiated",
                status="OPEN"
            ),
            Alert(
                alert_id=str(uuid.uuid4()),
                trip_id="TRIP-DEMO-001",
                truck_id=mock_truck_id,
                timestamp=datetime.now() - timedelta(hours=2),
                type=AlertType.WEIGHT_MISMATCH,
                severity="HIGH",
                description="ALERT RESOLVED – Reweigh at Kolkata Hub confirms no loss; SOP-102 closed by Control Room at 12:05 AM.",
                location=GeoPoint(latitude=22.5726, longitude=88.3639), # Kolkata Hub
                agent_name="Weight Guard",
                why_flagged="Initial sensor drift > 5%",
                sop_rule="SOP-102",
                action_taken="Reweigh ordered & Verified",
                status="RESOLVED"
            )
        ])
        
        # 3. Inject Second Mock Truck (Fleet Scale Demo)
        mock_truck_2 = "KA-02-XY-5678"
        self.active_trips[mock_truck_2] = TripConfig(
            trip_id="TRIP-DEMO-002",
            truck_id=mock_truck_2,
            start_location=GeoPoint(latitude=22.8046, longitude=86.2029), # Jamshedpur
            destination_location=GeoPoint(latitude=22.5726, longitude=88.3639), # Kolkata
            total_expected_weight_kg=22000.0,
            authorized_stops=[]
        )
        self.truck_states[mock_truck_2] = {
            "last_telemetry": Telemetry(
                truck_id=mock_truck_2,
                timestamp=datetime.now(),
                location=GeoPoint(latitude=22.4327, longitude=87.8672),
                weight_kg=22000.0,
                speed_kmh=45.0,
                ignition_on=True,
                status="MOVING"
            ),
            "stop_start_time": None,
            "is_stopped": False,
            "alerted_overstay": False
        }
        # Add an alert for the second truck so it shows as "Under Alert"
        self.alerts.extend([
            Alert(
                alert_id=str(uuid.uuid4()),
                trip_id="TRIP-DEMO-002",
                truck_id=mock_truck_2,
                timestamp=datetime.now() - timedelta(minutes=5),
                type=AlertType.ROUTE_DEVIATION,
                severity="HIGH",
                description="Route Deviation detected near Kolaghat.",
                location=GeoPoint(latitude=22.4327, longitude=87.8672),
                agent_name="Route Monitor",
                why_flagged="Deviation from path",
                sop_rule="SOP-075",
                action_taken="Control room notified"
            ),
            Alert(
                alert_id=str(uuid.uuid4()),
                trip_id="TRIP-DEMO-002",
                truck_id=mock_truck_2,
                timestamp=datetime.now() - timedelta(minutes=20),
                type=AlertType.SUSPICIOUS_STOP,
                severity="MEDIUM",
                description="Stop Analyzer: 12 min stop at unauthorized location.",
                location=GeoPoint(latitude=22.3898, longitude=87.7402),
                agent_name="Stop Analyzer",
                why_flagged="Unauthorized stop duration",
                sop_rule="SOP-089",
                action_taken="Verification call initiated"
            )
        ])
        
        # 3. Inject Third Mock Truck (Fleet Scale Demo - Normal)
        mock_truck_3 = "KA-03-GH-9012"
        self.active_trips[mock_truck_3] = TripConfig(
            trip_id="TRIP-DEMO-003",
            truck_id=mock_truck_3,
            start_location=GeoPoint(latitude=22.8046, longitude=86.2029), # Jamshedpur
            destination_location=GeoPoint(latitude=22.5726, longitude=88.3639), # Kolkata
            total_expected_weight_kg=21000.0,
            authorized_stops=[]
        )
        self.truck_states[mock_truck_3] = {
            "last_telemetry": Telemetry(
                truck_id=mock_truck_3,
                timestamp=datetime.now(),
                location=GeoPoint(latitude=22.6500, longitude=87.5000), # Mid-route
                weight_kg=21000.0,
                speed_kmh=55.0,
                ignition_on=True,
                status="MOVING"
            ),
            "stop_start_time": None,
            "is_stopped": False,
            "alerted_overstay": False
        }

    def register_trip(self, trip: TripConfig):
        self.active_trips[trip.truck_id] = trip
        self.truck_states[trip.truck_id] = {
            "last_telemetry": None,
            "stop_start_time": None,
            "is_stopped": False,
            "alerted_overstay": False
        }

    def get_alerts(self, truck_id: str = None) -> List[Alert]:
        if truck_id:
            return [a for a in self.alerts if a.truck_id == truck_id]
        return self.alerts

    def process_telemetry(self, data: Telemetry) -> List[Alert]:
        if data.truck_id not in self.active_trips:
            return [] 
        trip = self.active_trips[data.truck_id]
        state = self.truck_states[data.truck_id]
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
        
        self.alerts.extend(all_alerts)
        state["last_telemetry"] = data
        
        return all_alerts

    def resolve_alert(self, alert_id: str) -> Alert | None:
        for a in self.alerts:
            if a.alert_id == alert_id:
                a.status = "RESOLVED"
                return a
        return None

    def get_driver_info(self, truck_id: str) -> Dict:
        return self.driver_directory.get(truck_id, {"driver_name": "Unknown", "phone": "N/A", "company": "N/A"})
    
    def set_driver_info(self, truck_id: str, name: str, phone: str, company: str):
        self.driver_directory[truck_id] = {
            "driver_name": name,
            "phone": phone,
            "company": company
        }
    
    def unresolve_alert(self, alert_id: str) -> Alert | None:
        for a in self.alerts:
            if a.alert_id == alert_id:
                a.status = "OPEN"
                return a
        return None

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
            self.alerts.append(Alert(
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
            ))
        return event
