import streamlit as st
import pandas as pd
import os
from datetime import datetime, date, time
import calendar

# --- ページ設定 ---
st.set_page_config(page_title="シフト管理システム", page_icon="📅", layout="wide")

DATA_FILE = "shift_data_v2.csv"

# --- データの読み込みと初期化 ---
def load_data():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        # 読み込み時に日付型に変換
        df["日付"] = pd.to_datetime(df["日付"]).dt.date
        return df
    return pd.DataFrame(columns=["名前", "日付", "開始", "終了", "休み", "備考"])

df = load_data()

st.title("📅 チームシフト管理システム")

# --- タブ構成（一括入力タブを追加） ---
tab1, tab2, tab3, tab4 = st.tabs(["⚡ 1ヶ月一括入力", "✍️ 個別入力", "📊 シフト表ビュー", "⚙️ 管理・データ編集"])

# ==========================================
# 【タブ1】1ヶ月一括入力（今回のおすすめ機能）
# ==========================================
with tab1:
    st.markdown("### 1ヶ月分のシフトを一括で入力・修正します")
    st.caption("💡 変更がない日はそのままでOK。休みの日はチェックを入れます。Excelのようにサクサク入力できます。")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        bulk_name = st.text_input("氏名", key="bulk_name", placeholder="例: 山田 太郎")
    with col2:
        target_year = st.number_input("年", min_value=2024, max_value=2100, value=datetime.now().year)
    with col3:
        target_month = st.number_input("月", min_value=1, max_value=12, value=datetime.now().month)

    if bulk_name:
        # その月の日数と日付リストを生成
        _, days_in_month = calendar.monthrange(target_year, target_month)
        dates = [date(target_year, target_month, day) for day in range(1, days_in_month + 1)]
        
        # 既存データがあるかチェックし、なければデフォルト値で表を作る
        existing_data = df[(df["名前"] == bulk_name) & 
                           (pd.to_datetime(df["日付"]).dt.year == target_year) & 
                           (pd.to_datetime(df["日付"]).dt.month == target_month)]
        
        if existing_data.empty:
            # 新規作成（デフォルト 09:00 - 18:00）
            bulk_df = pd.DataFrame({
                "日付": dates,
                "休み": [False] * days_in_month,
                "開始": ["09:00"] * days_in_month,
                "終了": ["18:00"] * days_in_month,
                "備考": [""] * days_in_month
            })
        else:
            # 既存データを表示用に整形
            bulk_df = existing_data.drop(columns=["名前"]).sort_values("日付")

        # データエディターの表示（休みチェックボックス付き）
        edited_bulk = st.data_editor(
            bulk_df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "日付": st.column_config.DateColumn("日付", disabled=True),
                "休み": st.column_config.CheckboxColumn("休み", default=False),
                "開始": st.column_config.TextColumn("開始時間 (例: 09:00)"),
                "終了": st.column_config.TextColumn("終了時間 (例: 18:00)")
            }
        )

        if st.button("この月のシフトを確定する", type="primary", use_container_width=True):
            # 保存用に名前列を追加
            edited_bulk["名前"] = bulk_name
            # 古い同月データを削除して、新しいデータとガッチャンコする
            df = df.drop(existing_data.index)
            df = pd.concat([df, edited_bulk], ignore_index=True)
            df.to_csv(DATA_FILE, index=False)
            st.success(f"✅ {bulk_name}さんの {target_year}年{target_month}月 のシフトを保存しました！")
            st.rerun()
    else:
        st.info("👆 まずは氏名を入力してください。カレンダーが表示されます。")

# ==========================================
# 【タブ2】個別入力画面（単発の変更用）
# ==========================================
with tab2:
    st.markdown("### 単発のシフト登録・修正")
    with st.form("single_input_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("氏名", placeholder="例: 山田 太郎")
            target_date = st.date_input("日付")
            is_off = st.checkbox("この日は休み")
        with col2:
            start_time = st.time_input("開始時間", value=time(9, 0))
            end_time = st.time_input("終了時間", value=time(18, 0))
            note = st.text_input("備考")
            
        if st.form_submit_button("1日分を登録する", use_container_width=True):
            if not name.strip():
                st.error("⚠️ 氏名を入力してください。")
            else:
                # 既存の同日データを削除（上書きするため）
                df = df[~((df["名前"] == name) & (df["日付"] == target_date))]
                
                # 新しい行を追加
                start_str = start_time.strftime("%H:%M") if not is_off else ""
                end_str = end_time.strftime("%H:%M") if not is_off else ""
                
                new_row = pd.DataFrame([[name, target_date, start_str, end_str, is_off, note]], 
                                       columns=["名前", "日付", "開始", "終了", "休み", "備考"])
                df = pd.concat([df, new_row], ignore_index=True)
                df.to_csv(DATA_FILE, index=False)
                st.success(f"✅ {name}さんの {target_date} のシフトを登録しました！")
                st.rerun()

# ==========================================
# 【タブ3】見やすいシフト表ビュー
# ==========================================
with tab3:
    st.markdown("### 月間シフト表")
    if not df.empty:
        # 表示用に文字列を生成（例: "09:00-18:00" または "休"）
        def format_shift(row):
            if row["休み"]:
                return "休"
            return f"{row['開始']}-{row['終了']}"
            
        display_df = df.copy()
        display_df["シフト表示"] = display_df.apply(format_shift, axis=1)
        
        # クロス集計（縦：名前、横：日付）
        pivot_df = display_df.sort_values("日付").pivot(index="名前", columns="日付", values="シフト表示").fillna("-")
        st.dataframe(pivot_df, use_container_width=True)
    else:
        st.info("まだシフトデータがありません。")

# ==========================================
# 【タブ4】管理画面（直接編集）
# ==========================================
with tab4:
    st.markdown("### 全データの直接編集・削除")
    if not df.empty:
        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)
        if st.button("データベース全体を上書き保存", type="primary"):
            edited_df.to_csv(DATA_FILE, index=False)
            st.success("✅ 保存しました。")
            st.rerun()
        
        st.divider()
        csv = edited_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 CSVダウンロード", csv, "shift_data_full.csv", "text/csv")