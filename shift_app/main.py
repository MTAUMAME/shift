import streamlit as st
import pandas as pd
import os
from datetime import datetime, date, timedelta
import calendar

# --- ページ設定 ---
st.set_page_config(page_title="シフト管理システム", page_icon="📅", layout="centered")

# --- カスタムCSS ---
st.markdown("""
<style>
    html, body, [class*="css"]  { font-size: 16px; font-family: 'Helvetica Neue', Arial, sans-serif; }
    .stButton>button { border-radius: 12px; font-weight: bold; padding: 0.6rem 1rem; transition: 0.2s; }
    div[data-testid="stMetric"] { background-color: #f0f7ff; padding: 15px 20px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-left: 5px solid #007BFF; }
    div[data-testid="stForm"] > div { padding: 0; }
    .cal-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; table-layout: fixed; }
    .cal-th { background-color: #f0f2f6; border: 1px solid #ddd; padding: 6px; text-align: center; color: #333;}
    .cal-td { border: 1px solid #ddd; padding: 2px; vertical-align: top; height: 95px; background-color: #fff;}
    .cal-day { font-weight: bold; background: #fafafa; border-bottom: 1px solid #eee; text-align: right; padding-right: 5px; color: #555;}
    .cal-shift { background-color: #e6f3ff; color: #0055a4; padding: 4px; margin: 2px 0; border-radius: 4px; font-size: 0.75rem; border-left: 4px solid #0055a4; line-height: 1.3;}
    .cal-shift-off { background-color: #ffeeee; color: #cc0000; padding: 4px; margin: 2px 0; border-radius: 4px; font-size: 0.75rem; border-left: 4px solid #cc0000;}
    .role-badge { display: inline-block; font-size: 0.6rem; background: #fff; color: #333; padding: 1px 4px; border-radius: 3px; border: 1px solid #ccc; margin-bottom: 2px;}
</style>
""", unsafe_allow_html=True)

DATA_FILE = "shift_data_v2.csv"
USER_FILE = "users.csv"

TIME_OPTIONS = [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 30)]
ROLE_OPTIONS = ["未定", "ホール", "キッチン", "レジ", "リーダー"]
REST_OPTIONS = ["なし", "45分", "1時間", "1.5時間"]

def load_data():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        df["日付"] = pd.to_datetime(df["日付"], errors='coerce').dt.date
        if "休み" in df.columns:
            df["休み"] = df["休み"].astype(str).str.lower().isin(["true", "1", "t", "y", "yes"])
        else:
            df["休み"] = False
        for col in ["役割", "休憩"]:
            if col not in df.columns:
                df[col] = ""
        df["開始"] = df["開始"].fillna("").astype(str).replace("nan", "")
        df["終了"] = df["終了"].fillna("").astype(str).replace("nan", "")
        df["役割"] = df["役割"].fillna("").astype(str).replace("nan", "")
        df["休憩"] = df["休憩"].fillna("").astype(str).replace("nan", "")
        df["備考"] = df["備考"].fillna("").astype(str).replace("nan", "")
        return df
    return pd.DataFrame(columns=["名前", "日付", "役割", "開始", "終了", "休憩", "休み", "備考"])

def load_users():
    if os.path.exists(USER_FILE):
        return pd.read_csv(USER_FILE).astype(str)
    return pd.DataFrame(columns=["ユーザー名", "パスワード"])

df = load_data()
users_df = load_users()

# --- セッションステート（ログイン情報と通知メッセージ用） ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
if "flash_msg" not in st.session_state:
    st.session_state.flash_msg = None

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
                    st.error("🚨 [ERR-AUTH01] ユーザー名またはパスワードが違います")
    with tab_signup:
        with st.form("signup_form"):
            new_user = st.text_input("希望ユーザー名")
            new_pass = st.text_input("パスワード", type="password")
            if st.form_submit_button("登録", use_container_width=True):
                if new_user in users_df["ユーザー名"].values:
                    st.error("🚨 [ERR-AUTH02] その名前は既に使われています")
                elif new_user and new_pass:
                    try:
                        new_user_df = pd.DataFrame([[new_user, new_pass]], columns=["ユーザー名", "パスワード"])
                        users_df = pd.concat([users_df, new_user_df], ignore_index=True)
                        users_df.to_csv(USER_FILE, index=False)
                        st.success("✅ 登録完了！ログインしてください")
                    except Exception as e:
                        st.error(f"❌ [ERR-SYS00] ユーザー登録に失敗しました。詳細: {e}")
    st.stop()

# ==========================================
# 📱 メインアプリケーション
# ==========================================
current_user = st.session_state.username

# リロード後に通知があれば表示して消す
if st.session_state.flash_msg:
    st.toast(st.session_state.flash_msg, icon="✅")
    st.session_state.flash_msg = None

col_title, col_btn = st.columns([3, 1])
col_title.markdown("## 📱 シフトアプリ")
if col_btn.button("ログアウト", use_container_width=True):
    st.session_state.logged_in = False
    st.rerun()

# --- ダッシュボード ---
st.markdown(f"#### 👤 {current_user} さんの今月の状況")
now = datetime.now()
current_month_data = df[(df["名前"] == current_user) & 
                        (pd.to_datetime(df["日付"]).dt.year == now.year) & 
                        (pd.to_datetime(df["日付"]).dt.month == now.month)]

work_days = len(current_month_data[current_month_data["休み"] == False])
total_hours = 0.0

for _, row in current_month_data[current_month_data["休み"] == False].iterrows():
    try:
        s = datetime.strptime(row["開始"], "%H:%M")
        e = datetime.strptime(row["終了"], "%H:%M")
        diff = (e - s).total_seconds() / 3600
        
        rest_str = str(row["休憩"])
        rest_h = 0.0
        if rest_str == "45分": rest_h = 0.75
        elif rest_str == "1時間": rest_h = 1.0
        elif rest_str == "1.5時間": rest_h = 1.5
        
        diff = max(0, diff - rest_h)
        if diff > 0:
            total_hours += diff
    except:
        pass

m1, m2 = st.columns(2)
m1.metric("今月の出勤日数", f"{work_days} 日")
m2.metric("想定労働時間", f"{total_hours:.1f} 時間")

st.divider()

tab1, tab2, tab3 = st.tabs(["✍️ 1週間入力", "📆 チームカレンダー", "⚙️ 管理"])

# ==========================================
# 【タブ1】1週間カード型入力
# ==========================================
with tab1:
    st.markdown("### 📝 シフト入力（1週間分）")
    
    selected_date = st.date_input("基準となる日付を選択", value=date.today())
    start_date = selected_date - timedelta(days=selected_date.weekday()) 
    
    st.info(f"📅 【自動調整】 **{start_date.strftime('%Y/%m/%d')} (月) 〜** の1週間を表示しています")
    
    # 前週コピ機能
    prev_start = start_date - timedelta(days=7)
    prev_end = prev_start + timedelta(days=6)
    
    if st.button(f"⏪ 前週 ({prev_start.strftime('%m/%d')}〜) のシフトをコピーする", use_container_width=True):
        prev_data = df[(df["名前"] == current_user) & (df["日付"] >= prev_start) & (df["日付"] <= prev_end)]
        
        if prev_data.empty:
            st.warning("⚠️ [ERR-CPY01] コピー元の前週データが登録されていません。")
        else:
            try:
                current_end = start_date + timedelta(days=6)
                df = df[~((df["名前"] == current_user) & (df["日付"] >= start_date) & (df["日付"] <= current_end))]
                
                new_rows = []
                for _, row in prev_data.iterrows():
                    r = row.copy()
                    r["日付"] = r["日付"] + timedelta(days=7)
                    new_rows.append(r)
                    
                df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
                df.to_csv(DATA_FILE, index=False)
                
                st.session_state.flash_msg = "前週のシフトを反映しました！下のカードで微調整が可能です。"
                st.rerun()
            except Exception as e:
                st.error(f"❌ [ERR-SYS01] データのコピー・保存に失敗しました。詳細: {e}")

    with st.form("weekly_card_form"):
        form_data = []
        
        for i in range(7):
            d = start_date + timedelta(days=i)
            weekdays = ["月", "火", "水", "木", "金", "土", "日"]
            
            existing = df[(df["名前"] == current_user) & (df["日付"] == d)]
            def_off = False
            def_start = "09:00"
            def_end = "18:00"
            def_role = "未定"
            def_rest = "なし"
            def_note = ""
            
            if not existing.empty:
                r = existing.iloc[0]
                def_off = bool(r["休み"])
                def_start = r["開始"] if r["開始"] in TIME_OPTIONS else "09:00"
                def_end = r["終了"] if r["終了"] in TIME_OPTIONS else "18:00"
                def_role = r["役割"] if r["役割"] in ROLE_OPTIONS else "未定"
                def_rest = r["休憩"] if r["休憩"] in REST_OPTIONS else "なし"
                def_note = r["備考"]
            
            with st.container(border=True):
                st.markdown(f"**{d.strftime('%m/%d')} ({weekdays[d.weekday()]})**")
                is_off = st.toggle("この日は休み", value=def_off, key=f"off_{i}")
                
                c1, c2, c3, c4 = st.columns(4)
                role_val = c1.selectbox("役割", ROLE_OPTIONS, index=ROLE_OPTIONS.index(def_role), key=f"role_{i}")
                start_val = c2.selectbox("開始", TIME_OPTIONS, index=TIME_OPTIONS.index(def_start), key=f"start_{i}")
                end_val = c3.selectbox("終了", TIME_OPTIONS, index=TIME_OPTIONS.index(def_end), key=f"end_{i}")
                rest_val = c4.selectbox("休憩", REST_OPTIONS, index=REST_OPTIONS.index(def_rest), key=f"rest_{i}")
                
                note_val = st.text_input("備考", value=def_note, key=f"note_{i}", placeholder="例: 早退希望")
                
                form_data.append((d, is_off, role_val, start_val, end_val, rest_val, note_val))

        st.markdown("<br>", unsafe_allow_html=True)
        submitted = st.form_submit_button("✅ 1週間分をまとめて保存", use_container_width=True, type="primary")

        if submitted:
            has_error = False
            for data in form_data:
                d, is_off, role_val, start_val, end_val, rest_val, note_val = data
                if not is_off and start_val >= end_val:
                    has_error = True
                    break
            
            if has_error:
                st.error("🚨 [ERR-VAL01] 終了時間が開始時間より早い（または同じ）日があります。時間を修正してください。")
            else:
                try:
                    for data in form_data:
                        d, is_off, role_val, start_val, end_val, rest_val, note_val = data
                        df = df[~((df["名前"] == current_user) & (df["日付"] == d))]
                        
                        start_str = start_val if not is_off else ""
                        end_str = end_val if not is_off else ""
                        
                        new_row = pd.DataFrame([[current_user, d, role_val, start_str, end_str, rest_val, is_off, note_val]], 
                                               columns=["名前", "日付", "役割", "開始", "終了", "休憩", "休み", "備考"])
                        df = pd.concat([df, new_row], ignore_index=True)
                    
                    df.to_csv(DATA_FILE, index=False)
                    st.session_state.flash_msg = "1週間分のシフトを保存しました！"
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ [ERR-SYS02] データの保存に失敗しました。詳細: {e}")

# ==========================================
# 【タブ2】📆 チームカレンダー
# ==========================================
with tab2:
    st.markdown("### チームカレンダー")
    cal_y, cal_m = st.columns(2)
    c_year = cal_y.selectbox("表示年", range(2024, 2030), index=now.year - 2024, key="cy")
    c_month = cal_m.selectbox("表示月", range(1, 13), index=now.month - 1, key="cm")

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
                        role_html = f'<span class="role-badge">{r["役割"]}</span><br>' if r["役割"] and r["役割"] != "未定" else ""
                        cal_html += f'<div class="cal-shift">{r["名前"]}<br>{role_html}{r["開始"]}-{r["終了"]}</div>'
                cal_html += '</td>'
        cal_html += '</tr>'
    cal_html += '</tbody></table>'

    st.markdown(cal_html, unsafe_allow_html=True)

# ==========================================
# 【タブ3】管理画面
# ==========================================
with tab3:
    if not df.empty:
        st.caption("※全データを直接編集できます。")
        edit_df = df.copy()
        edit_df["日付"] = pd.to_datetime(edit_df["日付"]).dt.date
        edit_df["休み"] = edit_df["休み"].astype(bool)
        
        cols = ["名前", "日付", "役割", "開始", "終了", "休憩", "休み", "備考"]
        edit_df = edit_df[cols]
        
        edited_df = st.data_editor(edit_df, num_rows="dynamic", use_container_width=True)
        if st.button("データベース上書き保存", type="primary"):
            try:
                edited_df.to_csv(DATA_FILE, index=False)
                st.session_state.flash_msg = "データベースを上書き保存しました。"
                st.rerun()
            except Exception as e:
                st.error(f"❌ [ERR-SYS03] データベースの保存に失敗しました。詳細: {e}")