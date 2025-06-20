
# [Shortened for display] — this includes everything from the last version,
# but with this correction applied at GPT summary log insertion:

# Replacing:
# (log_id, None, "gpt", final_summary, timestamp)
# With:
# (log_id, "gpt", final_summary, timestamp) and query updated to use NULL directly

# Snippet of the fixed insert (inside GPT summary section):
if st.sidebar.button("📥 Save to Logs"):
    log_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    cursor.execute(
        "INSERT INTO Logs (log_id, project_id, source, message, timestamp) VALUES (?, NULL, ?, ?, ?)",
        (log_id, "gpt", final_summary, timestamp)
    )
    conn.commit()
    st.sidebar.success("✅ Summary saved to logs.")
