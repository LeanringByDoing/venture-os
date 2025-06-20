
import streamlit as st
import sqlite3
import pandas as pd
import altair as alt
import uuid
from datetime import date, datetime, timedelta
import openai

# Connect to the database
conn = sqlite3.connect("venture_os.db")
cursor = conn.cursor()

# --- Auto-patch: ensure Logs table exists ---
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

# Load projects
projects = pd.read_sql_query("SELECT * FROM Projects", conn)

st.title("Venture OS – Command Center")

# Sidebar Tabs
st.sidebar.title("🛠 Tools")
tab = st.sidebar.radio("Select Tool", ["➕ Add Project", "🤖 Bot Console", "🧠 GPT Weekly Summary"])

# Add Project
if tab == "➕ Add Project":
    with st.sidebar.form("add_project_form"):
        name = st.text_input("Project Name")
        proj_type = st.selectbox("Project Type", ["youtube", "tiktok", "flip", "bot", "custom"])
        start_date = st.date_input("Start Date", value=date.today())
        status = st.selectbox("Status", ["active", "paused", "retired"])
        description = st.text_area("Project Description")
        submitted = st.form_submit_button("Add Project")
        if submitted:
            cursor.execute(
                "INSERT INTO Projects (project_id, name, type, start_date, status, icon_url, description) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), name, proj_type, str(start_date), status, "", description)
            )
            conn.commit()
            st.success("✅ Project added! Refresh the page to view.")

# Bot Console
elif tab == "🤖 Bot Console":
    with st.sidebar.form("bot_command_form"):
        selected_project = st.selectbox("Project", projects["name"].tolist() if not projects.empty else [])
        command = st.text_input("Bot Command")
        submitted = st.form_submit_button("Send Command")

        if submitted and selected_project and command:
            project_id = projects[projects["name"] == selected_project]["project_id"].values[0]
            action_id = str(uuid.uuid4())
            timestamp = datetime.now().isoformat()
            simulated_response = f"Command '{command}' executed successfully for project '{selected_project}'."
            cursor.execute(
                "INSERT INTO AutomationActions (action_id, project_id, command, status, response, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                (action_id, project_id, command, "completed", simulated_response, timestamp)
            )
            conn.commit()
            st.success("✅ Command sent and logged!")

# GPT Summary
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
                project_data = recent_metrics[recent_metrics["project_name"] == project]
                for metric_name in project_data["name"].unique():
                    values = project_data[project_data["name"] == metric_name]["value"]
                    summary_text += f"  - {metric_name}: {values.sum():.2f}\n"
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
                    "INSERT INTO Logs (log_id, project_id, source, message, timestamp) VALUES (?, ?, ?, ?, ?)",
                    (log_id, None, "gpt", final_summary, timestamp)
                )
                conn.commit()
                st.sidebar.success("✅ Summary saved to logs.")
        else:
            st.sidebar.info("No metrics in the last 7 days.")
    else:
        st.sidebar.warning("Enter your OpenAI API key to generate a GPT summary.")

# Display Projects and Metrics
st.subheader("📁 Active Projects")
if not projects.empty:
    for _, project in projects.iterrows():
        st.markdown(f"### {project['name']} ({project['type'].capitalize()})")
        st.write(f"Status: {project['status']} | Started: {project['start_date']}")
        st.write(project['description'])

        metrics = pd.read_sql_query(
            f"SELECT name, value, unit, timestamp FROM Metrics WHERE project_id = '{project['project_id']}'",
            conn
        )

        if not metrics.empty:
            st.subheader("📊 Metrics")
            metrics['timestamp'] = pd.to_datetime(metrics['timestamp'])
            for metric_name in metrics['name'].unique():
                metric_data = metrics[metrics['name'] == metric_name]
                chart = alt.Chart(metric_data).mark_line(point=True).encode(
                    x='timestamp:T',
                    y='value:Q',
                    tooltip=['timestamp:T', 'value:Q']
                ).properties(title=f"{metric_name.capitalize()} over Time")
                st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No metrics found for this project.")
else:
    st.info("No projects found. Add some manually via the sidebar.")

# Close connection
conn.close()
