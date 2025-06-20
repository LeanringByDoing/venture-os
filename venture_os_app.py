
import streamlit as st
import sqlite3
import pandas as pd
import altair as alt
import uuid
from datetime import date, datetime, timedelta
import openai

conn = sqlite3.connect("venture_os.db")
cursor = conn.cursor()

# Drop and recreate Logs if schema is wrong or table is missing
try:
    cursor.execute("PRAGMA table_info(Logs)")
    cols = cursor.fetchall()
    expected_cols = {'log_id', 'project_id', 'source', 'message', 'timestamp'}
    actual_cols = set(c[1] for c in cols)
    if actual_cols != expected_cols:
        cursor.execute("DROP TABLE IF EXISTS Logs")
        raise Exception("Recreating Logs table")
except:
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Logs (
        log_id TEXT PRIMARY KEY,
        project_id TEXT,
        source TEXT,
        message TEXT,
        timestamp TEXT
    )""")

# Ensure remaining tables exist
cursor.execute("""
CREATE TABLE IF NOT EXISTS Metrics (
    metric_id TEXT PRIMARY KEY,
    project_id TEXT,
    name TEXT,
    value REAL,
    unit TEXT,
    timestamp TEXT
)""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS Projects (
    project_id TEXT PRIMARY KEY,
    name TEXT,
    type TEXT,
    start_date TEXT,
    status TEXT,
    icon_url TEXT,
    description TEXT
)""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS AutomationActions (
    action_id TEXT PRIMARY KEY,
    project_id TEXT,
    command TEXT,
    status TEXT,
    response TEXT,
    timestamp TEXT
)""")
conn.commit()

projects = pd.read_sql_query("SELECT * FROM Projects", conn)

st.title("Venture OS – Command Center")
st.sidebar.title("🛠 Tools")
tab = st.sidebar.radio("Select Tool", [
    "➕ Add Project",
    "📥 Manual Metric Entry",
    "🧠 GPT Weekly Summary",
    "📜 View Logs",
    "🧾 Project History",
    "🤖 Bot Console"
])

if tab == "🧠 GPT Weekly Summary":
    openai_api_key = st.sidebar.text_input("OpenAI API Key", type="password")
    if openai_api_key:
        client = openai.OpenAI(api_key=openai_api_key)
        one_week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        recent_metrics = pd.read_sql_query(
            f"""
            SELECT P.name as project_name, M.name, M.value, M.unit, M.timestamp
            FROM Metrics M
            JOIN Projects P ON M.project_id = P.project_id
            WHERE M.timestamp >= '{one_week_ago}'
            ORDER BY M.timestamp DESC
            """, conn
        )
        if not recent_metrics.empty:
            summary_text = "You are a startup performance analyst. Summarize the following weekly project metrics:\n\n"
            for project in recent_metrics["project_name"].unique():
                summary_text += f"Project: {project}\n"
                pdata = recent_metrics[recent_metrics["project_name"] == project]
                for mname in pdata["name"].unique():
                    vals = pdata[pdata["name"] == mname]["value"]
                    summary_text += f"  - {mname}: {vals.sum():.2f}\n"
                summary_text += "\n"
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You analyze startup project metrics and write smart, concise weekly summaries."},
                    {"role": "user", "content": summary_text}
                ],
                max_tokens=300
            )
            final_summary = response.choices[0].message.content
            st.sidebar.markdown("### 📋 GPT Summary")
            st.sidebar.markdown(final_summary)
            if st.sidebar.button("📥 Save to Logs"):
                log_id = str(uuid.uuid4())
                timestamp = datetime.now().isoformat()
                cursor.execute(
                    "INSERT INTO Logs (log_id, source, message, timestamp) VALUES (?, ?, ?, ?)",
                    (log_id, "gpt", final_summary, timestamp)
                )
                conn.commit()
                st.sidebar.success("✅ Summary saved to logs.")
        else:
            st.sidebar.info("No metrics in the last 7 days.")
    else:
        st.sidebar.warning("Enter OpenAI API key to generate summary.")

elif tab == "📜 View Logs":
    try:
        logs = pd.read_sql_query("SELECT * FROM Logs ORDER BY timestamp DESC", conn)
        if logs.empty:
            st.info("No logs found.")
        else:
            logs['timestamp'] = pd.to_datetime(logs['timestamp'])
            st.dataframe(logs[["timestamp", "source", "message"]])
    except Exception as e:
        st.error("Log table is missing or corrupt. Reload app or check database.")

conn.close()
