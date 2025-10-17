# frontend/subject_page.py
import streamlit as st

st.set_page_config(page_title="Subject Progress", layout="wide")

def main():
    subject = st.query_params.get("subject", ["math"])[0].capitalize()

    st.title(f"{subject} Progress 📊")

    st.markdown("### Your Recent Performance")
    st.progress(0.6)  # mock progress bar

    st.markdown("""
        #### Topics needing attention:
        - Fractions and Decimals ⚠️
        - Geometry Shapes 🧩

        #### Doing Well:
        - Basic Operations ✅
        - Word Problems 💡
    """)

    st.markdown("---")
    st.markdown("### Quiz History")
    st.table([
        {"Quiz": "Addition & Subtraction", "Score": "80%", "Date": "2025-09-21"},
        {"Quiz": "Geometry Basics", "Score": "60%", "Date": "2025-09-28"},
    ])

    st.markdown("---")
    if st.button("🚀 Start New Quiz"):
        st.success("Starting new quiz... (Coming soon!)")

if __name__ == "__main__":
    main()
