import streamlit as st
import pandas as pd
import os

# データの保存先（同じ階層のファイルを参照）
DATA_FILE = "shift_data.csv"

st.set_page_config(page_title="シフト管理システム", layout="centered")

# --- データの初期化 ---
if os.path.exists(DATA_FILE):
    df = pd.read_csv(DATA_FILE)
else:
    df = pd.DataFrame(columns=["名前", "希望日", "シフト"])

# --- タブ機能で画面を切り替え ---
tab1, tab2 = st.tabs(["希望入力", "管理者画面"])

# --- 【タブ1】入力画面 ---
with tab1:
    st.header("📅 シフト希望入力")
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
                st.rerun()
            else:
                st.warning("氏名を入力してください")

# --- 【タブ2】管理画面 ---
with tab2:
    st.header("📋 登録済みシフト一覧")
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        
        # CSVダウンロード機能もここに集約
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("CSVをダウンロード", csv, "shift_list.csv", "text/csv")
    else:
        st.info("データはまだありません")