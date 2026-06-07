import streamlit as st
import pandas as pd
import os

# 管理画面と同じファイルを参照するようにパスを指定
DATA_FILE = "../data/shift_data.csv"

st.title("シフト希望入力")
with st.form("input", clear_on_submit=True):
    name = st.text_input("名前")
    date = st.date_input("希望日")
    shift = st.selectbox("シフト", ["早番", "遅番", "夜勤", "休み"])
    if st.form_submit_button("登録"):
        if not os.path.exists("../data"): os.makedirs("../data")
        new_data = pd.DataFrame([[name, str(date), shift]], columns=["名前", "希望日", "シフト"])
        new_data.to_csv(DATA_FILE, mode='a', header=not os.path.exists(DATA_FILE), index=False)
        st.success("登録完了")