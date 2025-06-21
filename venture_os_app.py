
import streamlit as st
import sqlite3
import pandas as pd
import altair as alt
import uuid
from datetime import date

# Connect to the database
conn = sqlite3.connect("venture_os.db")
cursor = conn.cursor()

# Load projects
projects = pd.read_sql_query("SELECT * FROM Projects", conn)

st.title("Venture OS – Command Center")

# --- Add New Project UI ---
st.sidebar.header("➕ Add New Project")
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

# --- Display Existing Projects ---
st.subheader("📁 Active Projects")
if not projects.empty:
    for _, project in projects.iterrows():
        st.markdown(f"### {project['name']} ({project['type'].capitalize()})")
        st.write(f"Status: {project['status']} | Started: {project['start_date']}")
        st.write(project['description'])

        # Load metrics for this project
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
