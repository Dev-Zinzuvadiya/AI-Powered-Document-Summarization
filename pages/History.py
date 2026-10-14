"""Search and manage locally stored summary history."""

import streamlit as st
from utils.helpers import apply_theme, delete_history_entry, get_history

apply_theme()
st.title("Summary History")
st.caption("History is saved locally in data/history.json and is not shared.")

entries = get_history()
query = st.text_input("Search history")

if query:
    needle = query.casefold()
    entries = [
        entry
        for entry in entries
        if needle in entry.get("summary", "").casefold()
        or needle in entry.get("title", "").casefold()
        or needle in entry.get("source", "").casefold()
    ]

if not entries:
    st.info("No saved summaries match your search.")

for entry in entries:
    title = entry.get("title") or "Untitled summary"

    with st.expander(f"{title} · {entry.get('created_at','')}"):
        st.caption(f"Source: {entry.get('source', 'Text')} · {entry.get('engine','')}")
        st.markdown(entry.get("summary", ""))

        if entry.get("key_points"):
            for point in entry["key_points"]:
                st.markdown(f"- {point}")

        if st.button("Delete", key=f"delete_{entry['id']}"):
            delete_history_entry(entry["id"])
            st.rerun()
