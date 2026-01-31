import os
import streamlit as st

os.environ["GOOGLE_API_KEY"] = st.secrets["GOOGLE_AI_API_KEY"]
