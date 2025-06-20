
import streamlit as st
import sqlite3
import pandas as pd
import openai
import uuid
from datetime import datetime, timedelta
import requests

conn = sqlite3.connect("venture_os.db")
cursor = conn.cursor()

# Create tables if not exist
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
    project_id TEXT, source TEXT, message TEXT,
    timestamp TEXT
)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS Bots (
    bot_id TEXT PRIMARY KEY,
    project_id TEXT, name TEXT, last_checkin TEXT,
    status TEXT, bot_url TEXT
)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS AutomationActions (
    action_id TEXT PRIMARY KEY,
    project_id TEXT, command TEXT, status TEXT,
    response TEXT, timestamp TEXT
)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS Alerts (
    alert_id TEXT PRIMARY KEY,
    project_id TEXT, type TEXT, message TEXT,
    resolved INTEGER, timestamp TEXT
)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS AlertRules (
    rule_id TEXT PRIMARY KEY,
    project_id TEXT, metric_name TEXT,
    threshold_type TEXT, threshold_value REAL
)""")
conn.commit()

st.set_page_config(layout="wide")
st.title("📊 Venture OS")

tab = st.sidebar.radio("Tool", [
    "➕ Add Project", "📥 Manual Metric Entry", "🧠 GPT Summary",
    "🤖 Bot Console", "📜 Logs", "🛎 Alerts", "⚙️ Alert Rules"
])

projects = pd.read_sql_query("SELECT * FROM Projects", conn)

if tab == "➕ Add Project":
    with st.form("add_proj"):
        name = st.text_input("Project Name")
        proj_type = st.selectbox("Type", ["youtube", "tiktok", "bot", "product", "custom"])
        desc = st.text_area("Description")
        status = st.selectbox("Status", ["active", "paused", "retired"])
        url = st.text_input("Bot URL (optional)")
        submitted = st.form_submit_button("Add")
        if submitted:
            pid = str(uuid.uuid4())
            cursor.execute("INSERT INTO Projects VALUES (?, ?, ?, ?, ?, ?, ?)",
                (pid, name, proj_type, str(datetime.now().date()), status, "", desc))
            cursor.execute("INSERT INTO Bots VALUES (?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), pid, f"{name} Bot", datetime.now().isoformat(), "offline", url))
            conn.commit()
            st.success("✅ Project and bot added!")

elif tab == "📥 Manual Metric Entry":
    if projects.empty:
        st.warning("Add a project first.")
    else:
        with st.form("metrics_form"):
            project_name = st.selectbox("Project", projects["name"])
            metric = st.text_input("Metric Name")
            value = st.number_input("Value", step=1.0)
            unit = st.text_input("Unit")
            submitted = st.form_submit_button("Submit")
            if submitted:
                pid = projects[projects["name"] == project_name]["project_id"].values[0]
                cursor.execute("INSERT INTO Metrics VALUES (?, ?, ?, ?, ?, ?)",
                    (str(uuid.uuid4()), pid, metric, value, unit, datetime.now().isoformat()))
                conn.commit()
                st.success("Metric saved.")

elif tab == "🧠 GPT Summary":
    key = st.text_input("OpenAI API Key", type="password")
    if key:
        client = openai.OpenAI(api_key=key)
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        df = pd.read_sql_query(f"""
            SELECT P.name as project_name, M.name, M.value
            FROM Metrics M JOIN Projects P ON M.project_id = P.project_id
            WHERE M.timestamp > '{week_ago}'
        """, conn)
        if not df.empty:
            prompt = "Summarize weekly performance:\n"
            for proj in df["project_name"].unique():
                subset = df[df["project_name"] == proj]
                for _, row in subset.iterrows():
                    prompt += f"{proj} - {row['name']}: {row['value']}\n"
            try:
                res = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=300
                )
                summary = res.choices[0].message.content
                st.text_area("GPT Summary", summary, height=200)
                if st.button("📥 Save to Logs"):
                    cursor.execute("INSERT INTO Logs VALUES (?, ?, ?, ?, ?)",
                        (str(uuid.uuid4()), None, "gpt", summary, datetime.now().isoformat()))
                    conn.commit()
                    st.success("Summary saved.")
            except Exception as e:
                st.error(f"GPT error: {e}")
        else:
            st.info("No recent metrics.")

elif tab == "🤖 Bot Console":
    bots = pd.read_sql_query("SELECT * FROM Bots", conn)
    for _, row in bots.iterrows():
        st.subheader(row['name'])
        with st.form(f"bot_{row['bot_id']}"):
            cmd = st.text_input("Command", key=row["bot_id"])
            submitted = st.form_submit_button("Send")
            if submitted:
                ts = datetime.now().isoformat()
                try:
                    if row['bot_url']:
                        r = requests.post(row['bot_url'], json={"command": cmd}, timeout=5)
                        reply = r.text
                        status = "success" if r.ok else "error"
                    else:
                        reply = f"Simulated: {cmd}"
                        status = "simulated"
                except Exception as e:
                    reply = str(e)
                    status = "failed"
                cursor.execute("INSERT INTO AutomationActions VALUES (?, ?, ?, ?, ?, ?)",
                    (str(uuid.uuid4()), row["project_id"], cmd, status, reply, ts))
                cursor.execute("UPDATE Bots SET last_checkin = ?, status = ? WHERE bot_id = ?",
                    (ts, status, row["bot_id"]))
                conn.commit()
                st.success(f"Bot replied: {reply}")

elif tab == "📜 Logs":
    try:
        df = pd.read_sql_query("SELECT * FROM Logs ORDER BY timestamp DESC", conn)
        st.dataframe(df, use_container_width=True)
    except Exception:
        st.warning("No Logs yet.")

elif tab == "🛎 Alerts":
    try:
        df = pd.read_sql_query("SELECT * FROM Alerts ORDER BY timestamp DESC", conn)
        for _, r in df.iterrows():
            msg = f"{r['timestamp']} — {r['message']}"
            st.warning(msg if not r['resolved'] else f"✅ {msg}")
    except:
        st.info("No alerts.")

elif tab == "⚙️ Alert Rules":
    if projects.empty:
        st.info("No projects.")
    else:
        with st.form("rule_form"):
            project = st.selectbox("Project", projects["name"])
            metric = st.text_input("Metric Name")
            trigger = st.selectbox("Trigger", ["above", "below"])
            value = st.number_input("Threshold", step=1.0)
            if st.form_submit_button("Add Rule"):
                pid = projects[projects["name"] == project]["project_id"].values[0]
                cursor.execute("INSERT INTO AlertRules VALUES (?, ?, ?, ?, ?)",
                    (str(uuid.uuid4()), pid, metric, trigger, value))
                conn.commit()
                st.success("Rule added.")

# Auto-trigger alert checks
rules = pd.read_sql_query("SELECT * FROM AlertRules", conn)
for _, rule in rules.iterrows():
    m = pd.read_sql_query(f"""
        SELECT * FROM Metrics WHERE project_id = '{rule['project_id']}'
        AND name = '{rule['metric_name']}' ORDER BY timestamp DESC LIMIT 1
    """, conn)
    if not m.empty:
        val = m['value'].values[0]
        tval = rule['threshold_value']
        if (rule['threshold_type'] == 'above' and val > tval) or            (rule['threshold_type'] == 'below' and val < tval):
            cursor.execute("INSERT INTO Alerts VALUES (?, ?, ?, ?, ?, ?)", (
                str(uuid.uuid4()), rule['project_id'], "threshold",
                f"{rule['metric_name']} {rule['threshold_type']} {tval} (was {val})",
                0, datetime.now().isoformat()))
            conn.commit()

conn.close()
