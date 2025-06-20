
import streamlit as st
import sqlite3
import pandas as pd

# Connect to the database
conn = sqlite3.connect("venture_os.db")
cursor = conn.cursor()

# Load projects
projects = pd.read_sql_query("SELECT * FROM Projects", conn)

# Display project list
st.title("Venture OS – Command Center")
st.subheader("📁 Active Projects")
if not projects.empty:
    for _, row in projects.iterrows():
        st.markdown(f"### {row['name']} ({row['type'].capitalize()})")
        st.write(f"Status: {row['status']} | Started: {row['start_date']}")
        st.write(row['description'])
else:
    st.info("No projects found. Add some manually via DB or future UI.")

# Add new project section (future development)
st.markdown("---")
st.subheader("➕ Add New Project (coming soon)")

# Close connection
conn.close()
