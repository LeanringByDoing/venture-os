
import streamlit as st
import sqlite3
import pandas as pd
import uuid
from datetime import datetime
import openai
import os

st.set_page_config(layout="wide")
st.title("🧭 Venture OS")

# Safe DB connect
conn = sqlite3.connect("venture_os.db", check_same_thread=False)
cursor = conn.cursor()

# Ensure all tables exist
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
cursor.execute("""CREATE TABLE IF NOT EXISTS Alerts (
    alert_id TEXT PRIMARY KEY,
    project_id TEXT, metric TEXT,
    condition TEXT, threshold REAL,
    message TEXT, triggered_at TEXT
)""")
conn.commit()

# Define sidebar first
tab = st.sidebar.radio("Navigate", [
    "➕ Add Project", "📥 Metrics", "🧠 GPT Summary",
    "🤖 Bot Console", "📜 Logs", "🛎 Alerts", "⚙️ Alert Rules"
])

# Now render tab contents
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
        with st.form("add_metric_form"):
            metric = st.text_input("Metric Name").strip().lower()
            val = st.number_input("Value", step=1.0)
            unit = st.text_input("Unit (e.g., views, dollars)")
            submitted = st.form_submit_button("Submit")
            if submitted:
                existing = pd.read_sql(f"""
                    SELECT metric_id FROM Metrics
                    WHERE project_id = '{pid}' AND name = '{metric}' AND unit = '{unit}'
                    ORDER BY timestamp DESC LIMIT 1
                """, conn)
                timestamp = datetime.now().isoformat()
                if not existing.empty:
                    metric_id = existing["metric_id"].values[0]
                    cursor.execute("""
                        UPDATE Metrics SET value = ?, timestamp = ? WHERE metric_id = ?
                    """, (val, timestamp, metric_id))
                else:
                    cursor.execute("INSERT INTO Metrics VALUES (?, ?, ?, ?, ?, ?)", (
                        str(uuid.uuid4()), pid, metric, val, unit, timestamp
                    ))
                conn.commit()
                st.success("Metric recorded!")
        metrics = pd.read_sql(f"SELECT * FROM Metrics WHERE project_id = '{pid}'", conn)
        st.dataframe(metrics)

elif tab == "🧠 GPT Summary":
    df = pd.read_sql("SELECT * FROM Projects", conn)
    if df.empty:
        st.warning("No projects found.")
    else:
        project = st.selectbox("Pick Project", df["name"])
        pid = df[df["name"] == project]["project_id"].values[0]
        metrics = pd.read_sql(f"SELECT * FROM Metrics WHERE project_id = '{pid}'", conn)
        summary_text = "You are a startup performance analyst. Summarize the following weekly project metrics:

"
        for _, row in metrics.iterrows():
            summary_text += f"{row['name']}: {row['value']} {row['unit']} on {row['timestamp']}
"
        if st.button("🧠 Summarize with GPT"):
            try:
                client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
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
                st.error("OpenAI error or key missing.")

elif tab == "🤖 Bot Console":
    bots = pd.read_sql("SELECT * FROM Bots", conn)
    st.dataframe(bots if not bots.empty else pd.DataFrame(columns=["bot_id", "project_id", "name", "status", "last_checkin"]))

elif tab == "📜 Logs":
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Logs (
        log_id TEXT PRIMARY KEY,
        project_id TEXT,
        source TEXT,
        message TEXT,
        timestamp TEXT
    )
    """)
    conn.commit()
    logs = pd.read_sql("SELECT * FROM Logs ORDER BY timestamp DESC", conn)
    st.dataframe(logs)

elif tab == "🛎 Alerts":
    alerts = pd.read_sql("SELECT * FROM Alerts ORDER BY triggered_at DESC", conn)
    st.dataframe(alerts)

elif tab == "⚙️ Alert Rules":
    df = pd.read_sql("SELECT * FROM Projects", conn)
    if df.empty:
        st.warning("No projects yet.")
    else:
        project = st.selectbox("Choose Project", df["name"])
        pid = df[df["name"] == project]["project_id"].values[0]
        metric = st.text_input("Metric Name").strip().lower()
        condition = st.selectbox("Condition", [">", "<", ">=", "<=", "=="])
        threshold = st.number_input("Threshold")
        message = st.text_input("Alert Message")
        if st.button("Save Rule"):
            val = pd.read_sql(f"""
                SELECT value FROM Metrics WHERE project_id = '{pid}' AND name = '{metric}'
                ORDER BY timestamp DESC LIMIT 1
            """, conn)
            if not val.empty:
                last_val = val["value"].values[0]
                if eval(f"{last_val} {condition} {threshold}"):
                    cursor.execute("INSERT INTO Alerts VALUES (?, ?, ?, ?, ?, ?, ?)", (
                        str(uuid.uuid4()), pid, metric, condition,
                        threshold, message, datetime.now().isoformat()
                    ))
                    conn.commit()
                    st.success("Alert triggered and saved.")
                else:
                    st.info("Condition not met yet.")
