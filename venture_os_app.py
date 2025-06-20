
import streamlit as st
import sqlite3
import pandas as pd
import altair as alt
import uuid
from datetime import date, datetime

# Connect to the database
conn = sqlite3.connect("venture_os.db")
cursor = conn.cursor()

# Load projects
projects = pd.read_sql_query("SELECT * FROM Projects", conn)

st.title("Venture OS – Command Center")

# --- Bot Command Console ---
st.sidebar.header("🤖 Bot Command Console")
with st.sidebar.form("bot_command_form"):
    selected_project = st.selectbox("Project", projects["name"].tolist() if not projects.empty else [])
    command = st.text_input("Bot Command")
    submitted = st.form_submit_button("Send Command")

    if submitted and selected_project and command:
        project_id = projects[projects["name"] == selected_project]["project_id"].values[0]
        action_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()

        # Simulate bot response
        simulated_response = f"Command '{command}' executed successfully for project '{selected_project}'."

        cursor.execute(
            "INSERT INTO AutomationActions (action_id, project_id, command, status, response, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (action_id, project_id, command, "completed", simulated_response, timestamp)
        )
        conn.commit()
        st.success("✅ Command sent and logged!")

# --- Display Projects and Metrics ---
st.subheader("📁 Active Projects")
if not projects.empty:
    for _, project in projects.iterrows():
        st.markdown(f"### {project['name']} ({project['type'].capitalize()})")
        st.write(f"Status: {project['status']} | Started: {project['start_date']}")
        st.write(project['description'])

        # Load metrics
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
                ).properties(
                    title=f"{metric_name.capitalize()} over Time"
                )
                st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No metrics found for this project.")
else:
    st.info("No projects found. Add some manually via the sidebar.")

# Close connection
conn.close()
