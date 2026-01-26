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
        
        # 1. Anomaly Detection Agent
        raw_alerts = self.anomaly_agent.analyze(trip, data, state)
        
        # 2. SOP Enforcement Agent
        sop_actions = self.sop_agent.evaluate(trip, data, raw_alerts)
        
        # Combine all alerts
        all_alerts = raw_alerts + sop_actions
        
        self.alerts.extend(all_alerts)
        state["last_telemetry"] = data
        
        return all_alerts
