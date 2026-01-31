import os
import streamlit as st

os.environ["GOOGLE_API_KEY"] = st.secrets["GOOGLE_AI_API_KEY"]

st.set_page_config(
    page_title = "IM4U 코딩 비서",
    page_icon = ":computer:",
    layout = "wide"
)