import streamlit as st
import pandas as pd
import os

# --- ページ設定 ---
st.set_page_config(page_title="シフト管理システム", page_icon="📅", layout="wide")

DATA_FILE = "shift_data.csv"

# --- データの読み込み ---
def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    return pd.DataFrame(columns=["名前", "希望日", "シフト", "備考"])

df = load_data()

st.title("📅 チームシフト管理システム")

# --- タブ機能で画面を切り替え（3画面に拡張） ---
tab1, tab2, tab3 = st.tabs(["✍️ 希望入力", "📊 シフト表ビュー", "⚙️ 管理・データ編集"])

# ==========================================
# 【タブ1】入力画面
# ==========================================
with tab1:
    st.markdown("### シフト希望の提出")
    
    with st.form("input_form", clear_on_submit=True):
        # カラムを使って横並びのレイアウトにする
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("氏名", placeholder="例: 山田 太郎")
            date = st.date_input("希望日")
        
        with col2:
            shift = st.selectbox("シフト", ["早番", "遅番", "夜勤", "休み"])
            note = st.text_input("備考", placeholder="例: 15時以降希望、など")
            
        submitted = st.form_submit_button("シフトを登録する", use_container_width=True)

        if submitted:
            # バリデーション1: 名前の未入力チェック
            if not name.strip():
                st.error("⚠️ 氏名を入力してください。")
            else:
                # バリデーション2: 同一人物・同一日の重複チェック
                if not df[(df["名前"] == name) & (df["希望日"] == str(date))].empty:
                    st.warning(f"⚠️ {name}さんの {date} の希望は既に提出されています。管理画面から修正してください。")
                else:
                    new_row = pd.DataFrame([[name, str(date), shift, note]], columns=["名前", "希望日", "シフト", "備考"])
                    df = pd.concat([df, new_row], ignore_index=True)
                    df.to_csv(DATA_FILE, index=False)
                    st.success(f"✅ {name}さんの希望を登録しました！")
                    st.rerun()

# ==========================================
# 【タブ2】見やすいシフト表ビュー
# ==========================================
with tab2:
    st.markdown("### 月間シフト表")
    st.caption("※ 提出されたデータを「縦：名前」「横：日付」の形式で表示します。")
    
    if not df.empty:
        # 日付順に並び替えてから、クロス集計（ピボットテーブル）を作成
        df_sorted = df.sort_values(by="希望日")
        pivot_df = df_sorted.pivot(index="名前", columns="希望日", values="シフト").fillna("-")
        
        # 表を大きく表示
        st.dataframe(pivot_df, use_container_width=True)
    else:
        st.info("まだシフトデータが提出されていません。")

# ==========================================
# 【タブ3】管理画面（直接編集）
# ==========================================
with tab3:
    st.markdown("### 登録データの編集・削除")
    st.caption("💡 表のセルをクリックして直接文字を修正できます。行の左側にチェックを入れ、キーボードの「Delete」キーを押すとデータ削除が可能です。")
    
    if not df.empty:
        # データエディター機能（Excelのように編集可能）
        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="data_editor")

        # 変更保存ボタン
        if st.button("変更を保存する", type="primary"):
            edited_df.to_csv(DATA_FILE, index=False)
            st.success("✅ 変更を保存しました。")
            st.rerun()

        st.divider()
        
        # CSVダウンロード機能
        csv = edited_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 最新の全データをCSVでダウンロード", csv, "shift_data_full.csv", "text/csv")
    else:
        st.info("データはまだありません。")