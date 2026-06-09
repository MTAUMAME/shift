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
    .next-shift-card { background: #fff; border: 1px solid #eee; border-left: 4px solid #32CD32; padding: 10px; border-radius: 8px; margin-bottom: 8px; font-size: 0.9rem;}
    div[data-testid="stForm"] > div { padding: 0; }
    
    .cal-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; table-layout: fixed; }
    .cal-th { background-color: #f0f2f6; border: 1px solid #ddd; padding: 6px; text-align: center; color: #333;}
    .cal-td { border: 1px solid #ddd; padding: 2px; vertical-align: top; height: 110px; background-color: #fff;}
    .cal-day { font-weight: bold; background: #fafafa; border-bottom: 1px solid #eee; text-align: right; padding-right: 5px; color: #555;}
    
    /* 💡 新規追加：人数不足アラート用のバッジ */
    .shortage-alert { background-color: #ff4b4b; color: white; font-size: 0.65rem; font-weight: bold; padding: 2px 0; text-align: center; border-radius: 3px; margin-bottom: 3px; }
    .ok-alert { background-color: #e6ffe6; color: #008000; font-size: 0.65rem; font-weight: bold; padding: 2px 0; text-align: center; border-radius: 3px; margin-bottom: 3px; }
    
    .cal-shift { background-color: #e6f3ff; color: #0055a4; padding: 4px; margin: 2px 0; border-radius: 4px; font-size: 0.7rem; border-left: 4px solid #0055a4; line-height: 1.2;}
    .cal-shift-off { background-color: #ffeeee; color: #cc0000; padding: 4px; margin: 2px 0; border-radius: 4px; font-size: 0.7rem; border-left: 4px solid #cc0000;}
    .cal-shift-night { background-color: #3b2e5a; color: #fff; padding: 4px; margin: 2px 0; border-radius: 4px; font-size: 0.7rem; border-left: 4px solid #ffcc00; line-height: 1.2;}
    .role-badge { display: inline-block; font-size: 0.55rem; background: #fff; color: #333; padding: 1px 3px; border-radius: 3px; border: 1px solid #ccc; margin-bottom: 2px;}
</style>
""", unsafe_allow_html=True)

# --- ファイル定義 ---
DATA_FILE = "shift_data_v2.csv"
USER_FILE = "users.csv"
REQ_STAFF_FILE = "req_staff.csv" # 新規：曜日ごとの必要人数データ
ADMIN_SECRET_CODE = "admin123"

TIME_OPTIONS = [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 30)]
ROLE_OPTIONS = ["未定", "ホール", "キッチン", "レジ", "リーダー"]
REST_OPTIONS = ["なし", "45分", "1時間", "1.5時間"]
WEEKDAYS_JP = ["月", "火", "水", "木", "金", "土", "日"]

# --- 労働時間計算関数 ---
def calculate_work_hours(start_str, end_str, rest_str):
    if not start_str or not end_str:
        return 0.0
    try:
        s = datetime.strptime(start_str, "%H:%M")
        e = datetime.strptime(end_str, "%H:%M")
        diff = (e - s).total_seconds() / 3600
        if diff < 0:
            diff += 24.0 # 夜勤対応
        rest_h = 0.0
        if rest_str == "45分": rest_h = 0.75
        elif rest_str == "1時間": rest_h = 1.0
        elif rest_str == "1.5時間": rest_h = 1.5
        return max(0, diff - rest_h)
    except:
        return 0.0

# --- データ読み込み（マイグレーション強化） ---
def load_data():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        df["日付"] = pd.to_datetime(df["日付"], errors='coerce').dt.date
        if "休み" in df.columns:
            df["休み"] = df["休み"].astype(str).str.lower().isin(["true", "1", "t", "y", "yes"])
        else:
            df["休み"] = False
        for col in ["役割", "休憩"]:
            if col not in df.columns: df[col] = ""
        df["開始"] = df["開始"].fillna("").astype(str).replace("nan", "")
        df["終了"] = df["終了"].fillna("").astype(str).replace("nan", "")
        df["役割"] = df["役割"].fillna("").astype(str).replace("nan", "")
        df["休憩"] = df["休憩"].fillna("").astype(str).replace("nan", "")
        df["備考"] = df["備考"].fillna("").astype(str).replace("nan", "")
        return df
    return pd.DataFrame(columns=["名前", "日付", "役割", "開始", "終了", "休憩", "休み", "備考"])

def load_users():
    if os.path.exists(USER_FILE):
        df = pd.read_csv(USER_FILE).astype(str)
        if "権限" not in df.columns: df["権限"] = "一般"
        if "時給" not in df.columns: df["時給"] = "1000" # 新規：時給列の追加（初期値1000円）
        return df
    return pd.DataFrame(columns=["ユーザー名", "パスワード", "権限", "時給"])

def load_req_staff():
    if os.path.exists(REQ_STAFF_FILE):
        return pd.read_csv(REQ_STAFF_FILE)
    # 初期データ作成
    return pd.DataFrame({"曜日": WEEKDAYS_JP, "必要人数": [2, 2, 2, 2, 3, 4, 4]})

df = load_data()
users_df = load_users()
req_staff_df = load_req_staff()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = "一般"
if "flash_msg" not in st.session_state:
    st.session_state.flash_msg = None

# ==========================================
# 🔐 ログイン / 登録画面
# ==========================================
if not st.session_state.logged_in:
    st.title("🔐 シフトログイン")
    tab_login, tab_signup = st.tabs(["ログイン", "新規ユーザー登録"])
    
    with tab_login:
        with st.form("login_form"):
            username = st.text_input("ユーザー名")
            password = st.text_input("パスワード", type="password")
            if st.form_submit_button("ログイン", use_container_width=True):
                match = users_df[(users_df["ユーザー名"] == username) & (users_df["パスワード"] == password)]
                if not match.empty:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.role = match.iloc[0]["権限"]
                    st.rerun()
                else:
                    st.error("🚨 ユーザー名またはパスワードが違います")
                    
    with tab_signup:
        with st.form("signup_form"):
            new_user = st.text_input("希望ユーザー名")
            new_pass = st.text_input("パスワード（4文字以上）", type="password")
            admin_code = st.text_input("管理者コード（※一般スタッフは空欄）", type="password")
            if st.form_submit_button("登録", use_container_width=True):
                if len(new_pass) < 4:
                    st.error("🚨 パスワードは4文字以上にしてください")
                elif new_user in users_df["ユーザー名"].values:
                    st.error("🚨 そのユーザー名は既に使われています")
                elif new_user and new_pass:
                    role = "管理者" if admin_code == ADMIN_SECRET_CODE else "一般"
                    try:
                        new_user_df = pd.DataFrame([[new_user, new_pass, role, "1000"]], columns=["ユーザー名", "パスワード", "権限", "時給"])
                        users_df = pd.concat([users_df, new_user_df], ignore_index=True)
                        users_df.to_csv(USER_FILE, index=False)
                        st.success(f"✅ 登録完了！ログインしてください。")
                    except Exception as e:
                        st.error(f"❌ 登録失敗: {e}")
    st.stop()

# ==========================================
# 📱 メインアプリケーション
# ==========================================
current_user = st.session_state.username
is_admin = (st.session_state.role == "管理者")

if st.session_state.flash_msg:
    st.toast(st.session_state.flash_msg, icon="✅")
    st.session_state.flash_msg = None

col_title, col_btn = st.columns([3, 1])
col_title.markdown(f"## 📱 シフトアプリ <span style='font-size:0.5em; background:#eee; padding:2px 8px; border-radius:10px;'>{st.session_state.role}</span>", unsafe_allow_html=True)
if col_btn.button("ログアウト", use_container_width=True):
    st.session_state.logged_in = False
    st.rerun()

# --- 💡【新機能】ダッシュボード：時給と見込み給与の計算 ---
now = datetime.now()
today = date.today()
current_month_data = df[(df["名前"] == current_user) & 
                        (pd.to_datetime(df["日付"]).dt.year == now.year) & 
                        (pd.to_datetime(df["日付"]).dt.month == now.month) &
                        (df["休み"] == False)]

work_days = len(current_month_data)
total_hours = sum(calculate_work_hours(r["開始"], r["終了"], r["休憩"]) for _, r in current_month_data.iterrows())

# 時給を取得して計算
user_wage_str = users_df[users_df["ユーザー名"] == current_user].iloc[0]["時給"]
try:
    user_wage = int(user_wage_str)
except:
    user_wage = 1000 # エラー時はデフォルト

estimated_salary = int(total_hours * user_wage)

st.markdown(f"#### 👤 {current_user} さんの状況 (時給: {user_wage}円)")
m1, m2, m3 = st.columns(3)
m1.metric("出勤予定", f"{work_days} 日")
m2.metric("労働時間", f"{total_hours:.1f} h")
m3.metric("見込み給与", f"{estimated_salary:,} 円") # 3桁区切りで表示

st.divider()

# 直近のシフト表示機能とLINE共有機能
with st.expander("📲 自分のシフトをLINEで共有する / 直近の予定"):
    upcoming_7_days = df[(df["名前"] == current_user) & (df["日付"] >= today) & (df["日付"] <= today + timedelta(days=6))].sort_values("日付")
    line_text = f"【{current_user}のシフト予定】\n"
    
    if upcoming_7_days.empty:
        line_text += "直近1週間のシフトは未登録です。\n"
        st.info("直近の出勤予定はありません。")
    else:
        for _, r in upcoming_7_days.iterrows():
            wd = WEEKDAYS_JP[pd.to_datetime(r["日付"]).weekday()]
            d_str = r["日付"].strftime('%m/%d')
            if r["休み"]:
                line_text += f"{d_str}({wd}) 休み\n"
            else:
                line_text += f"{d_str}({wd}) {r['開始']}〜{r['終了']} ({r['役割']})\n"
                st.markdown(f"<div class='next-shift-card'><b>{d_str} ({wd})</b> | 🕒 {r['開始']}〜{r['終了']} ({r['役割']})</div>", unsafe_allow_html=True)
                
    st.text_area("以下のテキストをコピーして貼り付けてください", value=line_text, height=120)

st.divider()

tabs = st.tabs(["✍️ 1週間入力", "📆 チームカレンダー", "👑 管理者機能"] if is_admin else ["✍️ 1週間入力", "📆 チームカレンダー"])

# ==========================================
# 【タブ1】1週間カード型入力
# ==========================================
with tabs[0]:
    selected_date = st.date_input("基準となる日付を選択", value=today)
    start_date = selected_date - timedelta(days=selected_date.weekday()) 
    
    prev_start = start_date - timedelta(days=7)
    prev_end = prev_start + timedelta(days=6)
    
    if st.button(f"⏪ 前週 ({prev_start.strftime('%m/%d')}〜) のシフトをコピー", use_container_width=True):
        prev_data = df[(df["名前"] == current_user) & (df["日付"] >= prev_start) & (df["日付"] <= prev_end)]
        if prev_data.empty:
            st.warning("⚠️ コピー元の前週データが登録されていません。")
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
                st.session_state.flash_msg = "前週のシフトを反映しました！"
                st.rerun()
            except Exception as e:
                st.error(f"❌ データのコピーに失敗: {e}")

    with st.form("weekly_card_form"):
        form_data = []
        for i in range(7):
            d = start_date + timedelta(days=i)
            existing = df[(df["名前"] == current_user) & (df["日付"] == d)]
            def_off = False; def_start = "09:00"; def_end = "18:00"; def_role = "未定"; def_rest = "なし"; def_note = ""
            
            if not existing.empty:
                r = existing.iloc[0]
                def_off = bool(r["休み"])
                def_start = r["開始"] if r["開始"] in TIME_OPTIONS else "09:00"
                def_end = r["終了"] if r["終了"] in TIME_OPTIONS else "18:00"
                def_role = r["役割"] if r["役割"] in ROLE_OPTIONS else "未定"
                def_rest = r["休憩"] if r["休憩"] in REST_OPTIONS else "なし"
                def_note = r["備考"]
            
            with st.container(border=True):
                st.markdown(f"**{d.strftime('%m/%d')} ({WEEKDAYS_JP[d.weekday()]})**")
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
            work_days_count = 0
            
            for data in form_data:
                d, is_off, role_val, start_val, end_val, rest_val, note_val = data
                if not is_off:
                    work_days_count += 1
                    if start_val == end_val:
                        st.error(f"🚨 {d.strftime('%m/%d')} : 開始時間と終了時間が同じです。")
                        has_error = True
                    else:
                        work_hours = calculate_work_hours(start_val, end_val, "なし")
                        if work_hours > 8.0 and rest_val == "なし":
                            st.error(f"🚨 {d.strftime('%m/%d')} : 労働時間が8時間を超えるため休憩が必要です。")
                            has_error = True
                            
            if work_days_count == 7:
                st.error("🚨 7連勤以上のシフトは登録できません。必ず週に1日以上の「休み」を入れてください。")
                has_error = True
            
            if not has_error:
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
                    st.session_state.flash_msg = "シフトを保存しました！"
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 保存エラー: {e}")

# ==========================================
# 【タブ2】📆 チームカレンダー（人数不足アラート対応）
# ==========================================
with tabs[1]:
    st.markdown("### チームカレンダー")
    cal_y, cal_m = st.columns(2)
    c_year = cal_y.selectbox("表示年", range(2024, 2030), index=now.year - 2024, key="cy")
    c_month = cal_m.selectbox("表示月", range(1, 13), index=now.month - 1, key="cm")

    cal_html = '<table class="cal-table"><thead><tr>'
    for day_name in WEEKDAYS_JP:
        cal_html += f'<th class="cal-th">{day_name}</th>'
    cal_html += '</tr></thead><tbody>'

    cal_matrix = calendar.monthcalendar(c_year, c_month)
    for week in cal_matrix:
        cal_html += '<tr>'
        for day in week:
            if day == 0:
                cal_html += '<td class="cal-td" style="background:#f9f9f9;"></td>'
            else:
                day_date = date(c_year, c_month, day)
                weekday_idx = day_date.weekday()
                wd_str = WEEKDAYS_JP[weekday_idx]
                
                # 💡【新機能】必要人数のチェックロジック
                req_count = req_staff_df[req_staff_df["曜日"] == wd_str]["必要人数"].values[0]
                day_shifts = df[df["日付"] == day_date]
                working_staff = day_shifts[day_shifts["休み"] == False]
                actual_count = len(working_staff)
                
                alert_html = ""
                if actual_count < req_count:
                    shortage = req_count - actual_count
                    alert_html = f'<div class="shortage-alert">⚠️あと{shortage}人不足</div>'
                else:
                    alert_html = f'<div class="ok-alert">✅充足 ({actual_count}/{req_count})</div>'

                cal_html += f'<td class="cal-td"><div class="cal-day">{day}</div>{alert_html}'
                
                for _, r in day_shifts.iterrows():
                    if r["休み"]:
                        cal_html += f'<div class="cal-shift-off">{r["名前"]}: 休</div>'
                    else:
                        role_html = f'<span class="role-badge">{r["役割"]}</span><br>' if r["役割"] and r["役割"] != "未定" else ""
                        is_night = r["開始"] > r["終了"] if r["開始"] and r["終了"] else False
                        shift_class = "cal-shift-night" if is_night else "cal-shift"
                        night_mark = "(翌)" if is_night else ""
                        cal_html += f'<div class="{shift_class}">{r["名前"]}<br>{role_html}{r["開始"]}-{r["終了"]}{night_mark}</div>'
                cal_html += '</td>'
        cal_html += '</tr>'
    cal_html += '</tbody></table>'
    st.markdown(cal_html, unsafe_allow_html=True)

# ==========================================
# 【タブ3】👑 管理者機能（時給設定・必要人数設定）
# ==========================================
if is_admin:
    with tabs[2]:
        st.markdown("#### 1. 曜日ごとの「必要人数」設定")
        st.caption("カレンダーのアラートに連動します。編集してエンターを押すと保存されます。")
        edited_req = st.data_editor(req_staff_df, hide_index=True, use_container_width=True)
        if st.button("必要人数を更新", type="primary", key="btn_req"):
            edited_req.to_csv(REQ_STAFF_FILE, index=False)
            st.success("必要人数を保存しました！カレンダーに反映されます。")
            st.rerun()
            
        st.divider()

        st.markdown("#### 2. スタッフのアカウント・時給管理")
        st.caption("スタッフの時給や権限を編集できます。※パスワードの取り扱いには注意してください。")
        edited_users = st.data_editor(users_df, num_rows="dynamic", hide_index=True, use_container_width=True)
        if st.button("アカウント情報を更新", type="primary", key="btn_users"):
            edited_users.to_csv(USER_FILE, index=False)
            st.success("アカウント情報を保存しました！")
            st.rerun()

        st.divider()

        st.markdown("#### 3. 今月稼働時間 ＆ 給与集計（CSV出力）")
        if not df.empty:
            this_month_df = df[(pd.to_datetime(df["日付"]).dt.year == now.year) & 
                               (pd.to_datetime(df["日付"]).dt.month == now.month) & 
                               (df["休み"] == False)].copy()
                               
            if not this_month_df.empty:
                this_month_df["実働時間"] = this_month_df.apply(lambda row: calculate_work_hours(row["開始"], row["終了"], row["休憩"]), axis=1)
                summary_df = this_month_df.groupby("名前")["実働時間"].sum().reset_index()
                
                # 時給を結合して給与計算
                summary_df = summary_df.merge(users_df[["ユーザー名", "時給"]], left_on="名前", right_on="ユーザー名", how="left")
                summary_df["時給"] = pd.to_numeric(summary_df["時給"], errors='coerce').fillna(1000)
                summary_df["見込み給与(円)"] = (summary_df["実働時間"] * summary_df["時給"]).astype(int)
                
                summary_df = summary_df[["名前", "実働時間", "時給", "見込み給与(円)"]].sort_values("実働時間", ascending=False).reset_index(drop=True)
                
                st.dataframe(summary_df, use_container_width=True)
                
                csv_data = summary_df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 この集計データをCSVでダウンロード", csv_data, f"salary_summary_{now.year}_{now.month}.csv", "text/csv")
            else:
                st.info("今月の稼働データがありません。")