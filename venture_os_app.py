
import streamlit as st
import sqlite3
import pandas as pd
import uuid
from datetime import datetime
import openai
import os

st.set_page_config(layout="wide")
st.title("🧭 Venture OS")

conn = sqlite3.connect("venture_os.db", check_same_thread=False)
cursor = conn.cursor()

# Ensure tables exist
cursor.execute("""CREATE TABLE IF NOT EXISTS Projects (
    project_id TEXT PRIMARY KEY,
    name TEXT,
    type TEXT,
    start_date TEXT,
    status TEXT,
    icon_url TEXT,
    description TEXT
)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS Metrics (
    metric_id TEXT PRIMARY KEY,
    project_id TEXT,
    name TEXT,
    value REAL,
    unit TEXT,
    timestamp TEXT
)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS Logs (
    log_id TEXT PRIMARY KEY,
    project_id TEXT,
    source TEXT,
    message TEXT,
    timestamp TEXT
)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS Bots (
    bot_id TEXT PRIMARY KEY,
    project_id TEXT,
    name TEXT,
    status TEXT,
    last_checkin TEXT
)""")
conn.commit()

tab = st.sidebar.radio("Navigate", [
    "➕ Add Project", "📥 Metrics", "📊 Charts", "🧠 GPT Summary", "🤖 Bot Console", "📜 Logs"
])

if tab == "📊 Charts":
    df = pd.read_sql("SELECT * FROM Projects", conn)
    if df.empty:
        st.info("Add a project to begin.")
    else:
        project = st.selectbox("Select Project", df["name"])
        pid = df[df["name"] == project]["project_id"].values[0]
        metrics = pd.read_sql(f"SELECT * FROM Metrics WHERE project_id = '{pid}' ORDER BY timestamp", conn)
        if metrics.empty:
            st.warning("No metrics found for this project.")
        else:
            metric_names = sorted(metrics["name"].unique())
            selected_metric = st.selectbox("Metric to chart", metric_names)
            filtered = metrics[metrics["name"] == selected_metric]
            filtered["timestamp"] = pd.to_datetime(filtered["timestamp"])
            filtered = filtered.sort_values("timestamp")
            st.line_chart(filtered.set_index("timestamp")["value"])
