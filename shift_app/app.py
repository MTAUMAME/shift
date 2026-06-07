import streamlit as st
import pandas as pd
import os

# CSVファイルの保存先設定
DATA_FILE = "shift_data.csv"

st.set_page_config(page_title="シフト入力アプリ", layout="centered")
st.title("📅 シフト希望入力フォーム")

# CSVがなければ作成、あれば読み込み
if os.path.exists(DATA_FILE):
    df = pd.read_csv(DATA_FILE)
else:
    df = pd.DataFrame(columns=["名前", "希望日", "シフト"])

# 入力フォーム
with st.form("input_form", clear_on_submit=True):
    name = st.text_input("氏名")
    date = st.date_input("希望日")
    shift = st.selectbox("シフト", ["早番", "遅番", "夜勤", "休み"])
    
    submitted = st.form_submit_button("登録")

    if submitted:
        if name:
            new_row = pd.DataFrame([[name, str(date), shift]], columns=["名前", "希望日", "シフト"])
            df = pd.concat([df, new_row], ignore_index=True)
            df.to_csv(DATA_FILE, index=False)
            st.success(f"{name}さんの希望を登録しました！")
            st.rerun() # 画面を更新して一覧を最新にする
        else:
            st.warning("氏名を入力してください")

# 一覧表示
st.subheader("登録済みシフト一覧")
if not df.empty:
    st.dataframe(df, use_container_width=True)
else:
    st.info("データはまだありません")