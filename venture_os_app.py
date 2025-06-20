
import streamlit as st
import sqlite3
import pandas as pd
import altair as alt
import uuid
from datetime import date, datetime, timedelta
import openai

conn = sqlite3.connect("venture_os.db")
cursor = conn.cursor()

# === Auto-heal logs if needed ===
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

# === Tables ===
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
CREATE TABLE IF NOT EXISTS Metrics (
    metric_id TEXT PRIMARY KEY,
    project_id TEXT,
    name TEXT,
    value REAL,
    unit TEXT,
    timestamp TEXT
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
cursor.execute("""
CREATE TABLE IF NOT EXISTS Bots (
    bot_id TEXT PRIMARY KEY,
    project_id TEXT,
    name TEXT,
    last_checkin TEXT,
    status TEXT
)""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS Alerts (
    alert_id TEXT PRIMARY KEY,
    project_id TEXT,
    type TEXT,
    message TEXT,
    resolved INTEGER,
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
    "🤖 Bot Console",
    "🛎 Alerts Center"
])

# === Tools ===

if tab == "➕ Add Project":
    with st.sidebar.form("add_project_form"):
        name = st.text_input("Project Name")
        proj_type = st.selectbox("Project Type", ["youtube", "tiktok", "flip", "bot", "custom"])
        start_date = st.date_input("Start Date", value=date.today())
        status = st.selectbox("Status", ["active", "paused", "retired"])
        description = st.text_area("Project Description")
        submitted = st.form_submit_button("Add Project")
        if submitted:
            pid = str(uuid.uuid4())
            cursor.execute(
                "INSERT INTO Projects (project_id, name, type, start_date, status, icon_url, description) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (pid, name, proj_type, str(start_date), status, "", description)
            )
            cursor.execute(
                "INSERT INTO Bots (bot_id, project_id, name, last_checkin, status) VALUES (?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), pid, f"{name} Bot", datetime.now().isoformat(), "offline")
            )
            conn.commit()
            st.success("✅ Project & Bot added!")

elif tab == "📥 Manual Metric Entry":
    with st.sidebar.form("manual_metric"):
        selected = st.selectbox("Project", projects["name"].tolist() if not projects.empty else [])
        metric_name = st.text_input("Metric Name")
        value = st.number_input("Value", step=1.0)
        unit = st.text_input("Unit", value="")
        submitted = st.form_submit_button("Submit Metric")
        if submitted and selected and metric_name:
            pid = projects[projects["name"] == selected]["project_id"].values[0]
            cursor.execute(
                "INSERT INTO Metrics (metric_id, project_id, name, value, unit, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), pid, metric_name, value, unit, datetime.now().isoformat())
            )
            conn.commit()
            st.success("✅ Metric saved!")

elif tab == "🧠 GPT Weekly Summary":
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
    logs = pd.read_sql_query("SELECT * FROM Logs ORDER BY timestamp DESC", conn)
    if logs.empty:
        st.info("No logs found.")
    else:
        logs['timestamp'] = pd.to_datetime(logs['timestamp'])
        st.dataframe(logs[["timestamp", "source", "message"]])

elif tab == "🧾 Project History":
    for _, project in projects.iterrows():
        st.markdown(f"## {project['name']}")
        st.write(f"Status: {project['status']} | Started: {project['start_date']}")
        st.write(project['description'])
        metrics = pd.read_sql_query(
            f"SELECT name, value, unit, timestamp FROM Metrics WHERE project_id = '{project['project_id']}'",
            conn
        )
        if not metrics.empty:
            metrics['timestamp'] = pd.to_datetime(metrics['timestamp'])
            for metric_name in metrics['name'].unique():
                mdata = metrics[metrics['name'] == metric_name]
                chart = alt.Chart(mdata).mark_line(point=True).encode(
                    x='timestamp:T',
                    y='value:Q',
                    tooltip=['timestamp:T', 'value:Q']
                ).properties(title=f"{metric_name}")
                st.altair_chart(chart, use_container_width=True)

elif tab == "🤖 Bot Console":
    st.markdown("### 🤖 Bot Command Interface")
    bots = pd.read_sql_query("SELECT * FROM Bots", conn)
    if not bots.empty:
        for _, row in bots.iterrows():
            st.markdown(f"**{row['name']}** ({row['status']})")
            with st.form(f"bot_{row['bot_id']}"):
                cmd = st.text_input("Command", key=f"cmd_{row['bot_id']}")
                if st.form_submit_button("Send Command"):
                    action_id = str(uuid.uuid4())
                    timestamp = datetime.now().isoformat()
                    response = f"Simulated response to '{cmd}'"
                    cursor.execute(
                        "INSERT INTO AutomationActions (action_id, project_id, command, status, response, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                        (action_id, row["project_id"], cmd, "completed", response, timestamp)
                    )
                    cursor.execute(
                        "UPDATE Bots SET last_checkin = ?, status = ? WHERE bot_id = ?",
                        (timestamp, "online", row["bot_id"])
                    )
                    conn.commit()
                    st.success(f"✅ Bot responded: {response}")

elif tab == "🛎 Alerts Center":
    st.markdown("### 🔔 Alert Feed")
    alerts = pd.read_sql_query("SELECT * FROM Alerts ORDER BY timestamp DESC", conn)
    if alerts.empty:
        st.info("No alerts yet.")
    else:
        alerts['timestamp'] = pd.to_datetime(alerts['timestamp'])
        for _, alert in alerts.iterrows():
            if not alert["resolved"]:
                st.warning(f"[{alert['timestamp'].strftime('%Y-%m-%d %H:%M')}] {alert['message']}")

# Simulated auto-alert if any project has no metric in 3 days
for _, proj in projects.iterrows():
    pid = proj["project_id"]
    recent = pd.read_sql_query(f"SELECT * FROM Metrics WHERE project_id = '{pid}' ORDER BY timestamp DESC LIMIT 1", conn)
    if recent.empty or (datetime.now() - datetime.fromisoformat(recent['timestamp'].values[0])).days > 3:
        message = f"Project '{proj['name']}' has no metrics in over 3 days."
        existing = pd.read_sql_query(f"SELECT * FROM Alerts WHERE project_id = '{pid}' AND message = '{message}'", conn)
        if existing.empty:
            cursor.execute(
                "INSERT INTO Alerts (alert_id, project_id, type, message, resolved, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), pid, "no-metrics", message, 0, datetime.now().isoformat())
            )
conn.commit()
conn.close()
