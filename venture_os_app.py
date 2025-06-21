
# [... full Venture OS app code omitted for brevity, here's the Logs section with fix:]

if tab == "📜 Logs":
    # Ensure Logs table exists before reading
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
    st.dataframe(logs, use_container_width=True)

# [... rest of app code remains unchanged]
