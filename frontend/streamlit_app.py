import streamlit as st
import requests

API_URL = "http://localhost:8000"

st.title("Real Estate Lead Form")

name = st.text_input("Name")
phone = st.text_input("Phone")
interest = st.selectbox("Interest", ["Buy", "Sell", "Rent"])

if st.button("Submit"):
    # 1️⃣ Submit lead and get lead_id
    lead_resp = requests.post(f"{API_URL}/lead", json={
        "name": name,
        "phone": phone,
        "interest": interest
    })

    if lead_resp.status_code != 200:
        st.error("Failed to create lead")
    else:
        lead_id = lead_resp.json()["lead_id"]

        # 2️⃣ Start AI Voice Bot workflow with lead_id
        workflow_resp = requests.post(f"{API_URL}/webhook/start-call", json={
            "lead_id": lead_id,      # ← must include
            "name": name,
            "phone": phone,
            "interest": interest
        })

        if workflow_resp.status_code != 200:
            st.error("Failed to start workflow")
        else:
            st.success("Lead submitted & AI Voice Bot started")
