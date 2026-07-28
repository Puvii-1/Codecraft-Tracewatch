"""
Streamlit UI for CodeCraft.
Run with: streamlit run app.py
"""
import streamlit as st
from agents.graph import run_codecraft

st.set_page_config(page_title="CodeCraft — Multi-Agent Code Generator", page_icon="", layout="wide")

st.title(" CodeCraft")
st.caption("A multi-agent system: Planner → Coder → Reviewer, looping until the code passes review.")

with st.sidebar:
    st.header("Settings")
    max_iterations = st.slider("Max fix attempts per file", 1, 5, 3)
    st.markdown("---")
    st.markdown(
        "**How it works**\n\n"
        "1.  Planner splits your request into files\n"
        "2.  Coder writes each file\n"
        "3.  Reviewer checks it (syntax + LLM review)\n"
        "4.  If rejected, Coder fixes it and Reviewer checks again\n"
        "5. Repeats until approved or max attempts reached"
    )

user_request = st.text_area(
    "What do you want built?",
    placeholder="e.g. Build a simple command-line expense tracker with add, list, and total commands",
    height=100,
)

if st.button(" Generate", type="primary", disabled=not user_request.strip()):
    with st.spinner("Agents are working..."):
        try:
            result = run_codecraft(user_request, max_iterations=max_iterations)
        except ValueError as e:
            st.error(str(e))
            st.stop()

    status = result["status"]
    if status == "done":
        st.success("All tasks completed and approved!")
    elif status == "failed":
        st.warning("Some tasks hit the max retry limit. Partial results below.")

    tab_files, tab_log = st.tabs([" Generated Files", " Agent Activity Log"])

    with tab_files:
        for filename, code in result["code_files"].items():
            with st.expander(f"`{filename}`", expanded=True):
                st.code(code, language="python")
                st.download_button(
                    f"Download {filename}",
                    code,
                    file_name=filename,
                    key=f"dl_{filename}",
                )

    with tab_log:
        for entry in result["history"]:
            st.text(entry)