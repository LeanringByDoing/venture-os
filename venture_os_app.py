
import streamlit as st
import sqlite3
import pandas as pd
import openai
import uuid
from datetime import datetime, timedelta
import requests

# --- DB Setup ---
conn = sqlite3.connect("venture_os.db")
cursor = conn.cursor()
cursor.executescript("""
CREATE TABLE IF NOT EXISTS Projects (
    project_id TEXT PRIMARY KEY, name TEXT, type TEXT,
    start_date TEXT, status TEXT, icon_url TEXT, description TEXT
);
CREATE TABLE IF NOT EXISTS Metrics (
    metric_id TEXT PRIMARY KEY, project_id TEXT, name TEXT,
    value REAL, unit TEXT, timestamp TEXT
);
CREATE TABLE IF NOT EXISTS Logs (
    log_id TEXT PRIMARY KEY, project_id TEXT, source TEXT,
    message TEXT, timestamp TEXT
);
CREATE TABLE IF NOT EXISTS Bots (
    bot_id TEXT PRIMARY KEY, project_id TEXT, name TEXT,
    last_checkin TEXT, status TEXT, bot_url TEXT
);
CREATE TABLE IF NOT EXISTS AutomationActions (
    action_id TEXT PRIMARY KEY, project_id TEXT, command TEXT,
    status TEXT, response TEXT, timestamp TEXT
);
CREATE TABLE IF NOT EXISTS Alerts (
    alert_id TEXT PRIMARY KEY, project_id TEXT, type TEXT,
    message TEXT, resolved INTEGER, timestamp TEXT
);
CREATE TABLE IF NOT EXISTS AlertRules (
    rule_id TEXT PRIMARY KEY, project_id TEXT, metric_name TEXT,
    threshold_type TEXT, threshold_value REAL
);
""")
conn.commit()

# --- Auto-seed demo if empty ---
if pd.read_sql("SELECT COUNT(*) as count FROM Projects", conn)["count"][0] == 0:
    pid = str(uuid.uuid4())
    cursor.execute("INSERT INTO Projects VALUES (?, ?, ?, ?, ?, ?, ?)", (
        pid, "Demo Project", "bot", str(datetime.now().date()), "active", "", "Auto-seeded project"
    ))
    cursor.execute("INSERT INTO Bots VALUES (?, ?, ?, ?, ?, ?)", (
        str(uuid.uuid4()), pid, "Demo Bot", datetime.now().isoformat(), "offline", ""
    ))
    conn.commit()

st.set_page_config(layout="wide")
st.title("🧭 Venture OS – Unified Command")

tab = st.sidebar.radio("Navigate", [
    "➕ Add Project", "📥 Metrics", "🧠 GPT Summary", "🤖 Bot Console",
    "📜 Logs", "🛎 Alerts", "⚙️ Alert Rules"
])

projects = pd.read_sql("SELECT * FROM Projects", conn)

# --- Add Project ---
if tab == "➕ Add Project":
    with st.form("add_project"):
        name = st.text_input("Project Name")
        type_ = st.selectbox("Type", ["youtube", "tiktok", "bot", "product", "custom"])
        desc = st.text_area("Description")
        status = st.selectbox("Status", ["active", "paused", "retired"])
        bot_url = st.text_input("Bot URL (optional)")
        if st.form_submit_button("Create"):
            pid = str(uuid.uuid4())
            cursor.execute("INSERT INTO Projects VALUES (?, ?, ?, ?, ?, ?, ?)", (
                pid, name, type_, str(datetime.now().date()), status, "", desc
            ))
            cursor.execute("INSERT INTO Bots VALUES (?, ?, ?, ?, ?, ?)", (
                str(uuid.uuid4()), pid, f"{name} Bot", datetime.now().isoformat(), "offline", bot_url
            ))
            conn.commit()
            st.success("Project created!")

# --- Metrics ---
elif tab == "📥 Metrics":
    if not projects.empty:
        with st.form("metrics"):
            pname = st.selectbox("Project", projects["name"])
            metric = st.text_input("Metric Name")
            val = st.number_input("Value")
            unit = st.text_input("Unit")
            if st.form_submit_button("Save"):
                pid = projects[projects["name"] == pname]["project_id"].values[0]
                cursor.execute("INSERT INTO Metrics VALUES (?, ?, ?, ?, ?, ?)", (
                    str(uuid.uuid4()), pid, metric, val, unit, datetime.now().isoformat()
                ))
                conn.commit()
                st.success("Saved.")

# --- GPT Summary ---
elif tab == "🧠 GPT Summary":
    key = st.text_input("OpenAI API Key", type="password")
    if key:
        client = openai.OpenAI(api_key=key)
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        df = pd.read_sql(f"""
            SELECT P.name as project_name, M.name, M.value
            FROM Metrics M JOIN Projects P ON M.project_id = P.project_id
            WHERE M.timestamp > '{week_ago}'
        """, conn)
        if not df.empty:
            prompt = "Summarize weekly metrics:\n"
            for project in df["project_name"].unique():
                subset = df[df["project_name"] == project]
                for _, row in subset.iterrows():
                    prompt += f"{project} - {row['name']}: {row['value']}\n"
            try:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=300
                )
                summary = response.choices[0].message.content
                st.text_area("GPT Summary", summary, height=200)
                if st.button("📥 Save to Logs"):
                    cursor.execute("INSERT INTO Logs VALUES (?, ?, ?, ?, ?)", (
                        str(uuid.uuid4()), None, "gpt", summary, datetime.now().isoformat()
                    ))
                    conn.commit()
                    st.success("Saved.")
            except Exception as e:
                st.error(f"GPT Error: {e}")
        else:
            st.info("No recent metrics.")

# --- Bot Console ---
elif tab == "🤖 Bot Console":
    bots = pd.read_sql("SELECT * FROM Bots", conn)
    for _, bot in bots.iterrows():
        st.subheader(bot["name"])
        with st.form(f"bot_{bot['bot_id']}"):
            cmd = st.text_input("Command", key=bot["bot_id"])
            if st.form_submit_button("Send"):
                ts = datetime.now().isoformat()
                try:
                    if bot["bot_url"]:
                        r = requests.post(bot["bot_url"], json={"command": cmd}, timeout=5)
                        reply = r.text
                        status = "success" if r.ok else "error"
                    else:
                        reply = f"Simulated: {cmd}"
                        status = "simulated"
                except Exception as e:
                    reply = str(e)
                    status = "failed"
                cursor.execute("INSERT INTO AutomationActions VALUES (?, ?, ?, ?, ?, ?)", (
                    str(uuid.uuid4()), bot["project_id"], cmd, status, reply, ts
                ))
                cursor.execute("UPDATE Bots SET last_checkin = ?, status = ? WHERE bot_id = ?", (
                    ts, status, bot["bot_id"]
                ))
                conn.commit()
                st.success(f"Bot Reply: {reply}")

# --- Logs ---
elif tab == "📜 Logs":
    logs = pd.read_sql("SELECT * FROM Logs ORDER BY timestamp DESC", conn)
    st.dataframe(logs, use_container_width=True)

# --- Alerts ---
elif tab == "🛎 Alerts":
    alerts = pd.read_sql("SELECT * FROM Alerts ORDER BY timestamp DESC", conn)
    for _, row in alerts.iterrows():
        alert = f"{row['timestamp']} – {row['message']}"
        st.warning("✅ " + alert if row["resolved"] else alert)

# --- Alert Rules ---
elif tab == "⚙️ Alert Rules":
    if not projects.empty:
        with st.form("add_rule"):
            pname = st.selectbox("Project", projects["name"])
            metric = st.text_input("Metric Name")
            rule = st.selectbox("Trigger", ["above", "below"])
            threshold = st.number_input("Value", step=1.0)
            if st.form_submit_button("Add Rule"):
                pid = projects[projects["name"] == pname]["project_id"].values[0]
                cursor.execute("INSERT INTO AlertRules VALUES (?, ?, ?, ?, ?)", (
                    str(uuid.uuid4()), pid, metric, rule, threshold
                ))
                conn.commit()
                st.success("Rule added.")

# --- Trigger Checks ---
rules = pd.read_sql("SELECT * FROM AlertRules", conn)
for _, rule in rules.iterrows():
    q = f"""
        SELECT * FROM Metrics WHERE project_id = '{rule['project_id']}'
        AND name = '{rule['metric_name']}' ORDER BY timestamp DESC LIMIT 1
    """
    df = pd.read_sql(q, conn)
    if not df.empty:
        val = df["value"].values[0]
        triggered = (
            (rule["threshold_type"] == "above" and val > rule["threshold_value"]) or
            (rule["threshold_type"] == "below" and val < rule["threshold_value"])
        )
        if triggered:
            cursor.execute("INSERT INTO Alerts VALUES (?, ?, ?, ?, ?, ?)", (
                str(uuid.uuid4()), rule["project_id"], "threshold",
                f"{rule['metric_name']} {rule['threshold_type']} {rule['threshold_value']} (was {val})",
                0, datetime.now().isoformat()
            ))
            conn.commit()

conn.close()
