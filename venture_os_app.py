
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

cursor.execute("""CREATE TABLE IF NOT EXISTS Projects (
    project_id TEXT PRIMARY KEY,
    name TEXT, type TEXT, start_date TEXT,
    status TEXT, icon_url TEXT, description TEXT
)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS Metrics (
    metric_id TEXT PRIMARY KEY,
    project_id TEXT, name TEXT, value REAL,
    unit TEXT, timestamp TEXT
)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS Logs (
    log_id TEXT PRIMARY KEY,
    project_id TEXT, source TEXT,
    message TEXT, timestamp TEXT
)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS Bots (
    bot_id TEXT PRIMARY KEY,
    project_id TEXT, name TEXT,
    status TEXT, last_checkin TEXT
)""")
conn.commit()

tab = st.sidebar.radio("Navigate", [
    "➕ Add Project", "📥 Metrics", "🧠 GPT Summary",
    "🤖 Bot Console", "📜 Logs"
])

if tab == "➕ Add Project":
    with st.form("add_project_form"):
        name = st.text_input("Project Name")
        type_ = st.selectbox("Type", ["YouTube", "TikTok", "Physical Product", "Other"])
        start_date = st.date_input("Start Date")
        status = st.selectbox("Status", ["Planning", "Active", "Paused", "Completed"])
        icon_url = st.text_input("Icon URL")
        description = st.text_area("Description")
        submit = st.form_submit_button("Add Project")
        if submit:
            pid = str(uuid.uuid4())
            cursor.execute("INSERT INTO Projects VALUES (?, ?, ?, ?, ?, ?, ?)",
                (pid, name, type_, start_date.isoformat(), status, icon_url, description))
            conn.commit()
            st.success(f"Project {name} added!")

elif tab == "📥 Metrics":
    df = pd.read_sql("SELECT * FROM Projects", conn)
    if df.empty:
        st.info("Add a project to begin.")
    else:
        project = st.selectbox("Select Project", df["name"])
        pid = df[df["name"] == project]["project_id"].values[0]
        existing_metrics = pd.read_sql(f"SELECT DISTINCT name FROM Metrics WHERE project_id = '{pid}'", conn)
        options = sorted(existing_metrics["name"].tolist()) if not existing_metrics.empty else []
        metric = st.selectbox("Metric Name", options + ["(New Metric)"])
        new_metric = ""
        if metric == "(New Metric)":
            new_metric = st.text_input("Enter New Metric").strip().lower()
        name_to_use = new_metric if new_metric else metric
        with st.form("add_metric_form"):
            val = st.number_input("Value", step=1.0)
            unit = st.text_input("Unit (e.g., views, dollars)")
            submitted = st.form_submit_button("Submit")
            if submitted:
                name_to_use = name_to_use.lower()
                existing = pd.read_sql(f"""
                    SELECT metric_id FROM Metrics
                    WHERE project_id = '{pid}' AND LOWER(name) = '{name_to_use}' AND unit = '{unit}'
                    ORDER BY timestamp DESC LIMIT 1
                """, conn)
                timestamp = datetime.now().isoformat()
                if not existing.empty:
                    metric_id = existing["metric_id"].values[0]
                    cursor.execute("UPDATE Metrics SET value = ?, timestamp = ? WHERE metric_id = ?",
                        (val, timestamp, metric_id))
                else:
                    cursor.execute("INSERT INTO Metrics VALUES (?, ?, ?, ?, ?, ?)", (
                        str(uuid.uuid4()), pid, name_to_use, val, unit, timestamp
                    ))
                conn.commit()
                st.success("Metric recorded!")
        metrics = pd.read_sql(f"SELECT * FROM Metrics WHERE project_id = '{pid}'", conn)
        st.dataframe(metrics)

elif tab == "🧠 GPT Summary":
    api_key = st.text_input("OpenAI API Key", type="password")
    df = pd.read_sql("SELECT * FROM Projects", conn)
    if df.empty:
        st.warning("No projects found.")
    else:
        project = st.selectbox("Pick Project", df["name"])
        pid = df[df["name"] == project]["project_id"].values[0]
        metrics = pd.read_sql(f"SELECT * FROM Metrics WHERE project_id = '{pid}'", conn)
        summary_text = (
            "You are a startup performance analyst. "
            "Summarize the following weekly project metrics:\n\n"
        )
        for _, row in metrics.iterrows():
            summary_text += f"{row['name']}: {row['value']} {row['unit']} on {row['timestamp']}\n"
        if st.button("🧠 Summarize with GPT"):
            try:
                client = openai.OpenAI(api_key=api_key)
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": summary_text}],
                    max_tokens=300
                )
                final_summary = response.choices[0].message.content
                st.text_area("GPT Summary", final_summary, height=200)
                cursor.execute("INSERT INTO Logs VALUES (?, ?, ?, ?, ?)", (
                    str(uuid.uuid4()), pid, "gpt", final_summary, datetime.now().isoformat()
                ))
                conn.commit()
            except Exception as e:
                st.error("OpenAI error: " + str(e))

elif tab == "🤖 Bot Console":
    bots = pd.read_sql("SELECT * FROM Bots", conn)
    st.dataframe(bots if not bots.empty else pd.DataFrame(columns=["bot_id", "project_id", "name", "status", "last_checkin"]))

elif tab == "📜 Logs":
    try:
        logs = pd.read_sql("SELECT * FROM Logs ORDER BY timestamp DESC", conn)
        st.dataframe(logs)
    except Exception as e:
        st.error(f"Failed to load logs: {str(e)}")
