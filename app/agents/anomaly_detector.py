from typing import List, Optional
import uuid
from geopy.distance import geodesic
from app.models import Telemetry, TripConfig, Alert, AlertType, GeoPoint, AuthorizedStop

class AnomalyDetectionAgent:
    """
    Agent responsible for detecting anomalies in telemetry data.
    Focuses on:
    1. Suspicious Stop Durations (vs Authorized Rests)
    2. Weight-to-Location Mismatches
    """
    
    def analyze(self, trip: TripConfig, telemetry: Telemetry, truck_state: dict) -> List[Alert]:
        alerts = []
        
        # 1. Analyze Weight
        weight_alerts = self._analyze_weight(trip, telemetry)
        alerts.extend(weight_alerts)
        
        # 2. Analyze Stop Behavior
        stop_alerts = self._analyze_stops(trip, telemetry, truck_state)
        alerts.extend(stop_alerts)
        
        return alerts

    def _analyze_weight(self, trip: TripConfig, data: Telemetry) -> List[Alert]:
        alerts = []
        # Calculate dynamic threshold based on sensor noise tolerance
        min_allowed_weight = trip.total_expected_weight_kg - trip.weight_tolerance_kg
        
        if data.weight_kg < min_allowed_weight:
            dist_to_dest = self._calculate_distance(data.location, trip.destination_location)
            
            # Innovation: "Safe Zone" logic - if within 500m of destination, weight drop might be authorized offloading
            if dist_to_dest > 500:
                drop_percent = ((trip.total_expected_weight_kg - data.weight_kg) / trip.total_expected_weight_kg) * 100
                alert = Alert(
                    alert_id=str(uuid.uuid4()),
                    trip_id=trip.trip_id,
                    truck_id=data.truck_id,
                    timestamp=data.timestamp,
                    type=AlertType.WEIGHT_MISMATCH,
                    severity="CRITICAL",
                    description=f"CRITICAL – Weight drop {drop_percent:.0f}% outside geofence.",
                    location=data.location,
                    agent_name="Weight Guard",
                    why_flagged=f"Current weight ({data.weight_kg:.0f}kg) dropped significantly below expected ({trip.total_expected_weight_kg}kg).",
                    sop_rule="SOP-102 (Theft Prevention)",
                    action_taken="Security team alerted; driver called"
                )
                alerts.append(alert)
        return alerts

    def _analyze_stops(self, trip: TripConfig, data: Telemetry, state: dict) -> List[Alert]:
        alerts = []
        is_stopped = data.speed_kmh < 5.0

        if is_stopped:
            if not state["is_stopped"]:
                # Transition to Stopped
                state["is_stopped"] = True
                state["stop_start_time"] = data.timestamp
            else:
                # Continuing Stop
                stop_duration = (data.timestamp - state["stop_start_time"]).total_seconds() / 60.0
                
                # Context: Check if authorized
                auth_stop = self._find_authorized_stop(data.location, trip.authorized_stops)
                
                if auth_stop:
                    if stop_duration > auth_stop.max_duration_minutes:
                         # Overstay
                        if not state.get("alerted_overstay", False): # Prevent spam
                            alerts.append(Alert(
                                alert_id=str(uuid.uuid4()),
                                trip_id=trip.trip_id,
                                truck_id=data.truck_id,
                                timestamp=data.timestamp,
                                type=AlertType.SUSPICIOUS_STOP,
                                severity="MEDIUM",
                                description=f"Overstay at authorized stop '{auth_stop.name}'. Duration: {stop_duration:.1f} min",
                                location=data.location,
                                agent_name="Stop Analyzer",
                                why_flagged=f"Stop duration ({stop_duration:.0f}m) > Max authorized ({auth_stop.max_duration_minutes}m)",
                                sop_rule="SOP-005 (Rest Management)",
                                action_taken="Notify Fleet Manager"
                            ))
                            state["alerted_overstay"] = True
                else:
                    # Unauthorized Stop
                    # Heuristic: Allow 5 mins for traffic/signals
                    if stop_duration > 5.0:
                        # Escalation logic could go here (e.g., if duration > 30, severity = CRITICAL)
                        alerts.append(Alert(
                            alert_id=str(uuid.uuid4()),
                            trip_id=trip.trip_id,
                            truck_id=data.truck_id,
                            timestamp=data.timestamp,
                            type=AlertType.SUSPICIOUS_STOP,
                            severity="HIGH",
                            description=f"HIGH – Suspicious stop {stop_duration:.0f} min at non-whitelisted location.",
                            location=data.location,
                            agent_name="Stop Analyzer",
                            why_flagged="Vehicle stopped > 5 mins outside geo-fenced authorized zones.",
                            sop_rule="SOP-089 (Unauthorized Stoppage)",
                            action_taken="Security notified / driver called"
                        ))
        else:
            # Moving
            state["is_stopped"] = False
            state["stop_start_time"] = None
            state["alerted_overstay"] = False
            
        return alerts

    def _calculate_distance(self, p1: GeoPoint, p2: GeoPoint) -> float:
        return geodesic((p1.latitude, p1.longitude), (p2.latitude, p2.longitude)).meters

    def _find_authorized_stop(self, location: GeoPoint, auth_stops: List[AuthorizedStop]) -> Optional[AuthorizedStop]:
        for stop in auth_stops:
            if self._calculate_distance(location, stop.location) <= stop.radius_meters:
                return stop
        return None
