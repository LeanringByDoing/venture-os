
import streamlit as st
import sqlite3
import pandas as pd
import os

st.set_page_config(layout="wide")
st.title("🧭 Venture OS")

# Safe DB connection
try:
    conn = sqlite3.connect("venture_os.db")
    cursor = conn.cursor()

    # Ensure key tables exist
    cursor.execute("CREATE TABLE IF NOT EXISTS Projects (project_id TEXT PRIMARY KEY, name TEXT, type TEXT, start_date TEXT, status TEXT, icon_url TEXT, description TEXT)")
    conn.commit()

    # Load project list
    projects = pd.read_sql("SELECT * FROM Projects", conn)

except Exception as e:
    st.error(f"Database error: {e}")
    projects = pd.DataFrame()

# Safe Sidebar
tab = st.sidebar.radio("Navigate", [
    "➕ Add Project", "📥 Metrics", "🧠 GPT Summary",
    "🤖 Bot Console", "📜 Logs", "🛎 Alerts", "⚙️ Alert Rules"
])

st.success(f"Active tab: {tab}")
st.info("This build guarantees sidebar tabs are always visible.")

# Placeholder for each section
if tab == "➕ Add Project":
    st.subheader("Add Project (UI Placeholder)")
elif tab == "📥 Metrics":
    st.subheader("Metrics (UI Placeholder)")
elif tab == "🧠 GPT Summary":
    st.subheader("GPT Summary (UI Placeholder)")
elif tab == "🤖 Bot Console":
    st.subheader("Bot Console (UI Placeholder)")
elif tab == "📜 Logs":
    st.subheader("Logs (UI Placeholder)")
elif tab == "🛎 Alerts":
    st.subheader("Alerts (UI Placeholder)")
elif tab == "⚙️ Alert Rules":
    st.subheader("Alert Rules (UI Placeholder)")

