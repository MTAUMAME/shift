import streamlit as st
import pandas as pd
import os
from datetime import datetime, date, time
import calendar

# --- ページ設定 ---
st.set_page_config(page_title="シフト管理システム", page_icon="📅", layout="wide")

DATA_FILE = "shift_data_v2.csv"
USER_FILE = "users.csv"

# --- データの読み込みと初期化 ---
def load_data():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        df["日付"] = pd.to_datetime(df["日付"]).dt.date
        return df
    return pd.DataFrame(columns=["名前", "日付", "開始", "終了", "休み", "備考"])

def load_users():
    if os.path.exists(USER_FILE):
        return pd.read_csv(USER_FILE).astype(str)
    return pd.DataFrame(columns=["ユーザー名", "パスワード"])

df = load_data()
users_df = load_users()

# --- セッションステートの初期化（ログイン状態の管理） ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

# ==========================================
# 🔐 ログイン / ユーザー登録画面
# ==========================================
if not st.session_state.logged_in:
    st.title("🔐 シフト管理システムへログイン")
    
    login_tab, signup_tab = st.tabs(["ログイン", "新規ユーザー登録"])
    
    with login_tab:
        with st.form("login_form"):
            username = st.text_input("ユーザー名")
            password = st.text_input("パスワード", type="password")
            submit = st.form_submit_button("ログイン", use_container_width=True)
            
            if submit:
                # ユーザー認証
                match = users_df[(users_df["ユーザー名"] == username) & (users_df["パスワード"] == password)]
                if not match.empty:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.success("ログインしました！")
                    st.rerun()
                else:
                    st.error("⚠️ ユーザー名またはパスワードが間違っています。")
                    
    with signup_tab:
        with st.form("signup_form"):
            new_user = st.text_input("希望するユーザー名")
            new_pass = st.text_input("パスワード", type="password")
            submit_signup = st.form_submit_button("アカウントを作成", use_container_width=True)
            
            if submit_signup:
                if not new_user or not new_pass:
                    st.warning("⚠️ ユーザー名とパスワードを入力してください。")
                elif new_user in users_df["ユーザー名"].values:
                    st.error("⚠️ そのユーザー名は既に使われています。")
                else:
                    # 新規ユーザーの保存
                    new_user_df = pd.DataFrame([[new_user, new_pass]], columns=["ユーザー名", "パスワード"])
                    users_df = pd.concat([users_df, new_user_df], ignore_index=True)
                    users_df.to_csv(USER_FILE, index=False)
                    st.success(f"✅ {new_user} さんのアカウントを作成しました。「ログイン」タブからログインしてください。")
    
    # ログインしていない場合はここで処理を停止し、メイン画面を見せない
    st.stop()

# ==========================================
# 📱 メインアプリケーション（ログイン成功後）
# ==========================================
current_user = st.session_state.username

# ヘッダー周り（ログアウト機能）
col_title, col_logout = st.columns([4, 1])
with col_title:
    st.title("📅 チームシフト管理システム")
with col_logout:
    st.write(f"👤 **{current_user}** さん")
    if st.button("ログアウト", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()

st.divider()

# --- タブ構成 ---
tab1, tab2, tab3, tab4 = st.tabs(["⚡ 1ヶ月一括入力", "✍️ 個別入力", "📊 シフト表ビュー", "⚙️ 管理・データ編集"])

# ==========================================
# 【タブ1】1ヶ月一括入力（自身のアカウント専用）
# ==========================================
with tab1:
    st.markdown("### 1ヶ月分のシフトを一括入力・編集")
    
    col1, col2 = st.columns(2)
    with col1:
        target_year = st.number_input("年", min_value=2024, max_value=2100, value=datetime.now().year)
    with col2:
        target_month = st.number_input("月", min_value=1, max_value=12, value=datetime.now().month)

    # その月の日数と日付リストを生成
    _, days_in_month = calendar.monthrange(target_year, target_month)
    dates = [date(target_year, target_month, day) for day in range(1, days_in_month + 1)]
    
    # ★ ログイン中のユーザーの既存データを検索
    existing_data = df[(df["名前"] == current_user) & 
                        (pd.to_datetime(df["日付"]).dt.year == target_year) & 
                        (pd.to_datetime(df["日付"]).dt.month == target_month)]
    
    is_update = not existing_data.empty # データがあれば「更新モード」

    if not is_update:
        st.info("💡 この月のシフトはまだ登録されていません。新規作成します。")
        bulk_df = pd.DataFrame({
            "日付": dates,
            "休み": [False] * days_in_month,
            "開始": ["09:00"] * days_in_month,
            "終了": ["18:00"] * days_in_month,
            "備考": [""] * days_in_month
        })
    else:
        st.warning("🔄 この月のシフトは既に登録済みです。内容を編集して更新できます。")
        bulk_df = existing_data.drop(columns=["名前"]).sort_values("日付")

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

    # ボタンのテキストを動的に変更
    btn_text = "🔄 この内容でシフトを更新する" if is_update else "✅ この内容でシフトを新規登録する"
    
    if st.button(btn_text, type="primary", use_container_width=True):
        edited_bulk["名前"] = current_user
        # 古い同月データを削除して上書き
        df = df.drop(existing_data.index)
        df = pd.concat([df, edited_bulk], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)
        st.success(f"保存完了: {target_year}年{target_month}月のシフトを保存しました！")
        st.rerun()

# ==========================================
# 【タブ2】個別入力画面（単発の変更用）
# ==========================================
with tab2:
    st.markdown("### 単発のシフト登録・修正")
    
    target_date = st.date_input("日付を選択")
    
    # 選択した日付の既存データを検索
    single_existing = df[(df["名前"] == current_user) & (df["日付"] == target_date)]
    is_single_update = not single_existing.empty

    # 既存データがあれば初期値として設定
    default_off = False
    default_start = time(9, 0)
    default_end = time(18, 0)
    default_note = ""

    if is_single_update:
        st.warning("🔄 この日は既に登録済みです。内容を編集できます。")
        row = single_existing.iloc[0]
        default_off = bool(row["休み"])
        if not default_off:
            default_start = datetime.strptime(row["開始"], "%H:%M").time() if pd.notna(row["開始"]) and row["開始"] else time(9,0)
            default_end = datetime.strptime(row["終了"], "%H:%M").time() if pd.notna(row["終了"]) and row["終了"] else time(18,0)
        default_note = row["備考"] if pd.notna(row["備考"]) else ""

    with st.form("single_input_form"):
        is_off = st.checkbox("この日は休み", value=default_off)
        col1, col2 = st.columns(2)
        with col1:
            start_time = st.time_input("開始時間", value=default_start)
        with col2:
            end_time = st.time_input("終了時間", value=default_end)
            
        note = st.text_input("備考", value=default_note)
        
        single_btn_text = "更新する" if is_single_update else "登録する"
        
        if st.form_submit_button(single_btn_text, use_container_width=True):
            df = df[~((df["名前"] == current_user) & (df["日付"] == target_date))]
            start_str = start_time.strftime("%H:%M") if not is_off else ""
            end_str = end_time.strftime("%H:%M") if not is_off else ""
            
            new_row = pd.DataFrame([[current_user, target_date, start_str, end_str, is_off, note]], 
                                   columns=["名前", "日付", "開始", "終了", "休み", "備考"])
            df = pd.concat([df, new_row], ignore_index=True)
            df.to_csv(DATA_FILE, index=False)
            st.success(f"✅ {target_date} のシフトを保存しました！")
            st.rerun()

# ==========================================
# 【タブ3】見やすいシフト表ビュー
# ==========================================
with tab3:
    st.markdown("### 月間シフト表（全員分）")
    if not df.empty:
        def format_shift(row):
            if row["休み"]:
                return "休"
            return f"{row['開始']}-{row['終了']}"
            
        display_df = df.copy()
        display_df["シフト表示"] = display_df.apply(format_shift, axis=1)
        pivot_df = display_df.sort_values("日付").pivot(index="名前", columns="日付", values="シフト表示").fillna("-")
        st.dataframe(pivot_df, use_container_width=True)
    else:
        st.info("まだシフトデータがありません。")

# ==========================================
# 【タブ4】管理画面（直接編集）
# ==========================================
with tab4:
    st.markdown("### 全データの直接編集・削除（管理者用機能）")
    if not df.empty:
        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)
        if st.button("データベース全体を上書き保存", type="primary"):
            edited_df.to_csv(DATA_FILE, index=False)
            st.success("✅ 保存しました。")
            st.rerun()
        
        st.divider()
        csv = edited_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 CSVダウンロード", csv, "shift_data_full.csv", "text/csv")