import requests
import time
import random
import threading
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"

def create_geopoint(lat, lon):
    return {"latitude": lat, "longitude": lon}

class TruckSimulator:
    def __init__(self, truck_id, start_lat, start_lon, dest_lat, dest_lon, scenario_type="normal", weight=20000.0):
        self.truck_id = truck_id
        self.lat = start_lat
        self.lon = start_lon
        self.dest_lat = dest_lat
        self.dest_lon = dest_lon
        self.weight = weight
        self.scenario_type = scenario_type # 'normal', 'theft', 'minor'
        self.current_time = datetime.now()
        self.trip_id = f"TRIP-{random.randint(1000,9999)}"
        self.running = True

    def register(self):
        trip_data = {
            "trip_id": self.trip_id,
            "truck_id": self.truck_id,
            "start_location": create_geopoint(self.lat, self.lon),
            "destination_location": create_geopoint(self.dest_lat, self.dest_lon),
            "authorized_stops": [
                {
                    "location": create_geopoint(22.4327, 87.8672),
                    "radius_meters": 200,
                    "max_duration_minutes": 30,
                    "name": "Kolaghat Rest Point"
                }
            ],
            "total_expected_weight_kg": self.weight,
            "weight_tolerance_kg": 50.0
        }
        try:
            requests.post(f"{BASE_URL}/api/v1/trips", json=trip_data)
            print(f"[{self.truck_id}] Trip Registered ({self.scenario_type})")
        except:
            print(f"[{self.truck_id}] API Offline")

    def send_telemetry(self, speed, ignition, desc):
        # Add some noise to weight
        noise = random.uniform(-2.0, 2.0)
        current_weight = self.weight + noise
        
        telemetry = {
            "truck_id": self.truck_id,
            "timestamp": self.current_time.isoformat(),
            "location": create_geopoint(self.lat, self.lon),
            "weight_kg": current_weight,
            "speed_kmh": speed,
            "ignition_on": ignition
        }
        try:
            requests.post(f"{BASE_URL}/api/v1/telemetry", json=telemetry)
            print(f"[{self.truck_id}] {desc} (Wt: {current_weight:.1f}kg)")
        except:
            pass
        
        self.current_time += timedelta(minutes=1)

    def run_scenario(self):
        print(f"--- Starting Simulation for {self.truck_id} ---")
        self.register()
        time.sleep(1)
        
        if self.scenario_type == "theft":
            self._run_theft_scenario()
        else:
            self._run_normal_scenario()

    def _run_normal_scenario(self):
        # 1. Drive Normal (smaller steps, faster telemetry for smooth movement)
        for i in range(60):
            self.lon += 0.004
            self.lat -= 0.001  # Moving southeast towards Kolkata
            self.send_telemetry(45.0, True, "Driving")
            time.sleep(1)
            
        # 2. Authorized Stop
        print(f"[{self.truck_id}] Arrived at Authorized Stop")
        # Snap to authorized location (Midway Dhaba)
        old_lat, old_lon = self.lat, self.lon
        self.lat, self.lon = 22.6000, 87.0000 
        
        for _ in range(15):
            self.send_telemetry(0.0, False, "Resting at Dhaba")
            time.sleep(1)
            
        # Resume
        self.lat, self.lon = old_lat, old_lon # Back to road (approx)
        self.lat -= 0.01
        self.lon += 0.04
        self.send_telemetry(40.0, True, "Resuming Trip")
        time.sleep(1)
        
        # Finish
        for _ in range(80):
            self.lon += 0.004
            self.lat -= 0.001
            self.send_telemetry(50.0, True, "Cruising to Kolkata")
            time.sleep(1)

    def _run_theft_scenario(self):
        # 1. Drive Normal initially
        for _ in range(40):
            self.lon += 0.004
            self.lat -= 0.001
            self.send_telemetry(45.0, True, "Driving Normal")
            time.sleep(1)

        # 2. Deviation
        print(f"[{self.truck_id}] DEVIATING FROM ROUTE...")
        for _ in range(30):
            self.lat += 0.002  # Go North/Off-route slowly
            self.send_telemetry(40.0, True, "Route Deviation")
            time.sleep(1)
            
        # 3. Suspicious Stop
        print(f"[{self.truck_id}] SUSPICIOUS STOP...")
        for _ in range(20):  # Shorter cycle but more frequent telemetry
            self.send_telemetry(0.0, True, "Unauthorized Stop")
            time.sleep(1)
            
        # 4. Theft Event (Weight Drop)
        print(f"[{self.truck_id}] !!! THEFT EVENT !!!")
        self.weight -= 500.0 # Drop 500kg
        self.send_telemetry(0.0, False, "Weight Drop Detected")
        time.sleep(2)  # Pause for impact
        
        # 5. Fleeing
        print(f"[{self.truck_id}] Returning to route...")
        for _ in range(30):
            self.lat -= 0.002  # Return to main path gradually
            self.send_telemetry(50.0, True, "Returning to Route")
            time.sleep(1)


def run_simulation():
    # 1. KA-01-AB-1234: Normal Trip
    t1 = TruckSimulator("KA-01-AB-1234", 22.8046, 86.2029, 22.5726, 88.3639, scenario_type="normal", weight=25000.0)
    
    # 2. KA-02-XY-5678: Theft Scenario (Matches Dashboard Narrative)
    t2 = TruckSimulator("KA-02-XY-5678", 22.8046, 86.2029, 22.5726, 88.3639, scenario_type="theft", weight=22000.0)
    
    # 3. KA-03-GH-9012: Normal Trip (Another vehicle for scale)
    t3 = TruckSimulator("KA-03-GH-9012", 22.8046, 86.2029, 22.5726, 88.3639, scenario_type="normal", weight=21000.0)
    
    # Threads
    threads = []
    for t in [t1, t2, t3]:
        th = threading.Thread(target=t.run_scenario)
        threads.append(th)
        th.start()
        
    for th in threads:
        th.join()
        
    print("\nAll Simulations Complete.")

if __name__ == "__main__":
    run_simulation()
