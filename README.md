# AI-Led Prevention of Pilferage in Rebar Transportation

## Problem Statement
Steel rebars are high-value assets susceptible to theft during transit. Current tracking methods (GPS/manual) are insufficient. This project aims to provide an AI-led solution to prevent pilferage by integrating disparate data streams (GPS, Weight) and applying decision logic.

## Solution Architecture
The solution consists of:
1.  **Data Simulation**: A module to simulate truck movements, GPS coordinates, and weight sensor data.
2.  **Intelligence Engine**: 
    - **Anomaly Detection**: Identifies suspicious stops and weight-to-location mismatches.
    - **SOP Enforcer**: Triggers alerts based on defined rules (e.g., weight drop outside geofence).
3.  **Backend API**: A FastAPI application to receive telemetry and serve alerts.
4.  **Dashboard**: (Optional) Visualization of truck status.

## Key Features
- Real-time monitoring of transit events.
- Detection of "Suspicious Stop-Duration".
- Detection of unauthorized weight changes.
- Automated alerting based on SOPs.

## Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Run the server: `uvicorn app.main:app --reload`
3. Run the simulation (in a new terminal): `python simulate_scenario.py`

## Project Structure
- `app/`: Contains the backend logic and API.
  - `main.py`: FastAPI entry point.
  - `logic.py`: Core intelligence engine (SOPs, Anomaly Detection).
  - `models.py`: Data models.
- `simulate_scenario.py`: Script to generate mock telemetry and demonstrate the solution.
