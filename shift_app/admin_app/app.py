import streamlit as st
import pandas as pd
import os

DATA_FILE = "../data/shift_data.csv"

st.title("シフト管理画面")
if os.path.exists(DATA_FILE):
    df = pd.read_csv(DATA_FILE)
    st.dataframe(df)
else:
    st.info("データがありません")