import streamlit as st
import pandas as pd
import os
from datetime import datetime, date
import calendar

# --- ページ設定 ---
st.set_page_config(page_title="シフト管理システム", page_icon="📅", layout="wide")

# --- スマホ・リッチUI対応のカスタムCSS ---
st.markdown("""
<style>
    html, body, [class*="css"]  { font-size: 16px; }
    .stButton>button { border-radius: 8px; font-weight: bold; padding: 0.5rem 1rem; }
    .cal-table { width: 100%; border-collapse: collapse; font-size: 0.9rem; table-layout: fixed; }
    .cal-th { background-color: #f0f2f6; border: 1px solid #ddd; padding: 8px; text-align: center; color: #333;}
    .cal-td { border: 1px solid #ddd; padding: 4px; vertical-align: top; height: 100px; background-color: #fff;}
    .cal-day { font-weight: bold; background: #fafafa; border-bottom: 1px solid #eee; text-align: right; padding-right: 5px; color: #555;}
    .cal-shift { background-color: #e6f3ff; color: #0055a4; padding: 4px; margin: 2px 0; border-radius: 4px; font-size: 0.8rem; font-weight: 500;}
    .cal-shift-off { background-color: #ffeeee; color: #cc0000; padding: 4px; margin: 2px 0; border-radius: 4px; font-size: 0.8rem; font-weight: 500;}
</style>
""", unsafe_allow_html=True)

DATA_FILE = "shift_data_v2.csv"
USER_FILE = "users.csv"

TIME_OPTIONS = [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 30)]

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

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

# ==========================================
# 🔐 ログイン画面
# ==========================================
if not st.session_state.logged_in:
    st.title("🔐 シフトログイン")
    tab_login, tab_signup = st.tabs(["ログイン", "新規登録"])
    
    with tab_login:
        with st.form("login_form"):
            username = st.text_input("ユーザー名")
            password = st.text_input("パスワード", type="password")
            if st.form_submit_button("ログイン", use_container_width=True):
                match = users_df[(users_df["ユーザー名"] == username) & (users_df["パスワード"] == password)]
                if not match.empty:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("⚠️ ユーザー名またはパスワードが違います")
                    
    with tab_signup:
        with st.form("signup_form"):
            new_user = st.text_input("希望ユーザー名")
            new_pass = st.text_input("パスワード", type="password")
            if st.form_submit_button("登録", use_container_width=True):
                if new_user in users_df["ユーザー名"].values:
                    st.error("⚠️ その名前は既に使われています")
                elif new_user and new_pass:
                    new_user_df = pd.DataFrame([[new_user, new_pass]], columns=["ユーザー名", "パスワード"])
                    users_df = pd.concat([users_df, new_user_df], ignore_index=True)
                    users_df.to_csv(USER_FILE, index=False)
                    st.success("✅ 登録完了！「ログイン」タブからログインしてください")
    st.stop()

# ==========================================
# 📱 メインアプリケーション
# ==========================================
current_user = st.session_state.username

col1, col2 = st.columns([3, 1])
col1.markdown(f"### 📅 シフトシステム (👤 {current_user})")
if col2.button("ログアウト", use_container_width=True):
    st.session_state.logged_in = False
    st.rerun()

st.divider()

tab1, tab2, tab3, tab4 = st.tabs(["⚡ 一括入力", "✍️ 個別入力", "📆 カレンダー", "⚙️ 管理"])

# ==========================================
# 【タブ1】1ヶ月一括入力（修正箇所）
# ==========================================
with tab1:
    col_y, col_m = st.columns(2)
    target_year = col_y.selectbox("年", range(2024, 2030), index=datetime.now().year - 2024)
    target_month = col_m.selectbox("月", range(1, 13), index=datetime.now().month - 1)

    _, days_in_month = calendar.monthrange(target_year, target_month)
    dates = [date(target_year, target_month, day) for day in range(1, days_in_month + 1)]
    
    existing_data = df[(df["名前"] == current_user) & 
                        (pd.to_datetime(df["日付"]).dt.year == target_year) & 
                        (pd.to_datetime(df["日付"]).dt.month == target_month)]
    
    is_update = not existing_data.empty

    if not is_update:
        bulk_df = pd.DataFrame({
            "日付": dates,
            "休み": [False] * days_in_month,
            "開始": ["09:00"] * days_in_month,
            "終了": ["18:00"] * days_in_month,
            "備考": [""] * days_in_month
        })
    else:
        bulk_df = existing_data.drop(columns=["名前"]).sort_values("日付")

    st.caption("💡 開始・終了時間はタップしてプルダウンから選択できます。")

    # 修正: bulk_df.style.apply() を外し、純粋なデータフレームを渡す
    edited_bulk = st.data_editor(
        bulk_df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "日付": st.column_config.DateColumn("日付", disabled=True),
            "休み": st.column_config.CheckboxColumn("休み"),
            "開始": st.column_config.SelectboxColumn("開始", options=TIME_OPTIONS),
            "終了": st.column_config.SelectboxColumn("終了", options=TIME_OPTIONS),
            "備考": st.column_config.TextColumn("備考")
        }
    )

    # エラーチェック（開始時刻 >= 終了時刻 の行があるか）
    error_rows = edited_bulk[(~edited_bulk["休み"]) & (edited_bulk["開始"] >= edited_bulk["終了"])]
    has_error = not error_rows.empty

    if has_error:
        st.error("🚨 【入力エラー】終了時間が開始時間より早い（または同じ）日があります。時間を修正してください。")
    
    btn_text = "🔄 更新する" if is_update else "✅ 登録する"
    
    if st.button(btn_text, type="primary", use_container_width=True, disabled=has_error):
        edited_bulk["名前"] = current_user
        df = df.drop(existing_data.index)
        df = pd.concat([df, edited_bulk], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)
        st.success("保存しました！")
        st.rerun()

# ==========================================
# 【タブ2】個別入力
# ==========================================
with tab2:
    target_date = st.date_input("日付を選択")
    single_existing = df[(df["名前"] == current_user) & (df["日付"] == target_date)]
    is_single_update = not single_existing.empty

    default_off = False
    default_start = "09:00"
    default_end = "18:00"
    default_note = ""

    if is_single_update:
        row = single_existing.iloc[0]
        default_off = bool(row["休み"])
        default_start = row["開始"] if row["開始"] in TIME_OPTIONS else "09:00"
        default_end = row["終了"] if row["終了"] in TIME_OPTIONS else "18:00"
        default_note = row["備考"] if pd.notna(row["備考"]) else ""

    with st.form("single_input_form"):
        is_off = st.checkbox("この日は休み", value=default_off)
        c1, c2 = st.columns(2)
        start_time = c1.selectbox("開始", options=TIME_OPTIONS, index=TIME_OPTIONS.index(default_start))
        end_time = c2.selectbox("終了", options=TIME_OPTIONS, index=TIME_OPTIONS.index(default_end))
        note = st.text_input("備考", value=default_note)
        
        is_single_error = (not is_off) and (start_time >= end_time)
        if is_single_error:
            st.error("🚨 終了時間は開始時間より後にしてください")
            
        if st.form_submit_button("保存する", use_container_width=True):
            if is_single_error:
                st.warning("時間を修正してから保存してください。")
            else:
                df = df[~((df["名前"] == current_user) & (df["日付"] == target_date))]
                start_str = start_time if not is_off else ""
                end_str = end_time if not is_off else ""
                new_row = pd.DataFrame([[current_user, target_date, start_str, end_str, is_off, note]], 
                                       columns=["名前", "日付", "開始", "終了", "休み", "備考"])
                df = pd.concat([df, new_row], ignore_index=True)
                df.to_csv(DATA_FILE, index=False)
                st.success("保存しました！")
                st.rerun()

# ==========================================
# 【タブ3】📆 カレンダービュー
# ==========================================
with tab3:
    st.markdown("### チーム全体のカレンダー")
    cal_y, cal_m = st.columns(2)
    c_year = cal_y.selectbox("表示年", range(2024, 2030), index=datetime.now().year - 2024, key="cy")
    c_month = cal_m.selectbox("表示月", range(1, 13), index=datetime.now().month - 1, key="cm")

    cal_html = '<table class="cal-table"><thead><tr>'
    for day_name in ["月", "火", "水", "木", "金", "土", "日"]:
        cal_html += f'<th class="cal-th">{day_name}</th>'
    cal_html += '</tr></thead><tbody>'

    cal_matrix = calendar.monthcalendar(c_year, c_month)
    
    for week in cal_matrix:
        cal_html += '<tr>'
        for day in week:
            if day == 0:
                cal_html += '<td class="cal-td" style="background:#f9f9f9;"></td>'
            else:
                cal_html += f'<td class="cal-td"><div class="cal-day">{day}</div>'
                
                day_date = date(c_year, c_month, day)
                day_shifts = df[df["日付"] == day_date]
                
                for _, r in day_shifts.iterrows():
                    if r["休み"]:
                        cal_html += f'<div class="cal-shift-off">{r["名前"]}: 休</div>'
                    else:
                        cal_html += f'<div class="cal-shift">{r["名前"]}<br>{r["開始"]}-{r["終了"]}</div>'
                cal_html += '</td>'
        cal_html += '</tr>'
    cal_html += '</tbody></table>'

    st.markdown(cal_html, unsafe_allow_html=True)

# ==========================================
# 【タブ4】管理画面
# ==========================================
with tab4:
    if not df.empty:
        st.caption("※管理用。全データを直接編集できます。")
        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)
        if st.button("データベース上書き保存", type="primary"):
            edited_df.to_csv(DATA_FILE, index=False)
            st.success("保存しました。")
            st.rerun()