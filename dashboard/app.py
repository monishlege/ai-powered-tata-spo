import streamlit as st
import requests
import pandas as pd
import time
import subprocess
import os

st.set_page_config(
    page_title="Tata Steel Cargo Monitor",
    page_icon="🚛",
    layout="wide"
)

BASE_URL = "http://localhost:8000"

# --- Sidebar ---
st.sidebar.title("🚛 Fleet Monitor")
st.sidebar.markdown("---")

# Fetch Trucks
try:
    trucks_resp = requests.get(f"{BASE_URL}/api/v1/trucks")
    if trucks_resp.status_code == 200:
        trucks = trucks_resp.json()
    else:
        trucks = []
except requests.exceptions.ConnectionError:
    st.sidebar.error("❌ Backend Offline")
    trucks = []

selected_truck = st.sidebar.selectbox("Select Vehicle", trucks) if trucks else None

st.sidebar.markdown("---")
st.sidebar.subheader("Controls")
if st.sidebar.button("🚀 Run Simulation Scenario"):
    # Trigger simulation script in background
    subprocess.Popen(["python", "simulate_scenario.py"], cwd=os.getcwd())
    st.sidebar.success("Simulation Started!")

st.sidebar.markdown("---")
auto_refresh = st.sidebar.checkbox("Auto Refresh", value=True)

# --- Main Content ---
st.title("🛡️ Anti-Pilferage Intelligence Center")

if not selected_truck:
    st.info("Waiting for active trips... Click 'Run Simulation Scenario' to generate data.")
    if auto_refresh:
        time.sleep(2)
        st.rerun()
else:
    # Fetch Data
    try:
        status_resp = requests.get(f"{BASE_URL}/api/v1/status/{selected_truck}")
        alerts_resp = requests.get(f"{BASE_URL}/api/v1/alerts?truck_id={selected_truck}")
        
        status_data = status_resp.json()
        alerts_data = alerts_resp.json()
        
        telemetry = status_data.get("last_telemetry")
        
        if telemetry:
            # 1. Key Metrics
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Status", "STOPPED" if status_data["is_stopped"] else "MOVING", 
                        delta_color="off" if status_data["is_stopped"] else "normal")
            col2.metric("Speed", f"{telemetry['speed_kmh']} km/h")
            col3.metric("Weight", f"{telemetry['weight_kg']} kg")
            col4.metric("Last Update", telemetry['timestamp'].split('T')[1][:8])

            # 2. Map
            st.subheader("📍 Live Tracking")
            lat = telemetry['location']['latitude']
            lon = telemetry['location']['longitude']
            map_data = pd.DataFrame({'lat': [lat], 'lon': [lon]})
            st.map(map_data, zoom=10)
            
        else:
            st.warning("No telemetry received yet.")

        # 3. Intelligent Alerts
        st.subheader("🚨 Intelligence Log")
        if alerts_data:
            for alert in reversed(alerts_data): # Newest first
                with st.expander(f"{alert['severity']} | {alert['type']} | {alert['timestamp'].split('T')[1][:8]}", expanded=True):
                    st.write(f"**Description:** {alert['description']}")
                    if "SOP ENFORCEMENT" in alert['description']:
                        st.markdown("✅ **Action Taken:** SOP Protocol Executed")
        else:
            st.success("No anomalies detected. Operations normal.")

    except Exception as e:
        st.error(f"Error fetching data: {e}")

    if auto_refresh:
        time.sleep(2)
        st.rerun()
