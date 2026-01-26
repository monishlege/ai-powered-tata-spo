from typing import List
import uuid
from app.models import Telemetry, TripConfig, Alert, AlertType

class SOPEngineAgent:
    """
    Agent responsible for enforcing Standard Operating Procedures (SOPs).
    It acts as the 'Decision Logic' layer.
    """
    
    def evaluate(self, trip: TripConfig, telemetry: Telemetry, incoming_alerts: List[Alert]) -> List[Alert]:
        """
        Evaluates incoming alerts against SOPs to determine if further escalation or specific actions are needed.
        """
        sop_actions = []
        
        for alert in incoming_alerts:
            if alert.type == AlertType.WEIGHT_MISMATCH:
                # SOP Rule 1: Immediate Security Protocol for Weight Loss outside Safe Zone
                # We can enrich the alert or create a new 'Action' alert
                sop_actions.append(self._trigger_security_protocol(alert))
            
            if alert.type == AlertType.SUSPICIOUS_STOP and alert.severity == "HIGH":
                # SOP Rule 2: High Severity Stops require driver contact
                sop_actions.append(self._trigger_driver_contact(alert))
                
        return sop_actions

    def _trigger_security_protocol(self, trigger_alert: Alert) -> Alert:
        return Alert(
            alert_id=str(uuid.uuid4()),
            trip_id=trigger_alert.trip_id,
            truck_id=trigger_alert.truck_id,
            timestamp=trigger_alert.timestamp,
            type=AlertType.ROUTE_DEVIATION, # Using existing enum, or could add SOP_VIOLATION
            severity="CRITICAL",
            description=f"SOP ENFORCEMENT: Security Team Notified. Drone Dispatch Initiated. (Triggered by: {trigger_alert.description})",
            location=trigger_alert.location
        )

    def _trigger_driver_contact(self, trigger_alert: Alert) -> Alert:
         return Alert(
            alert_id=str(uuid.uuid4()),
            trip_id=trigger_alert.trip_id,
            truck_id=trigger_alert.truck_id,
            timestamp=trigger_alert.timestamp,
            type=AlertType.SUSPICIOUS_STOP,
            severity="MEDIUM",
            description=f"SOP ENFORCEMENT: Automated Driver Call Initiated. (Triggered by: {trigger_alert.description})",
            location=trigger_alert.location
        )
