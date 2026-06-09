import streamlit as st
import pandas as pd
import os
from datetime import datetime, date, timedelta
import calendar

# --- ページ設定 ---
st.set_page_config(page_title="シフト管理システム", page_icon="📅", layout="centered") # スマホ向けにcenteredに変更

# --- スマホ・リッチUI対応のカスタムCSS ---
st.markdown("""
<style>
    /* 全体フォントサイズとテーマカラーの設定 */
    html, body, [class*="css"]  { font-size: 16px; font-family: 'Helvetica Neue', Arial, sans-serif; }
    
    /* ボタンの丸みとリッチ化 */
    .stButton>button { border-radius: 12px; font-weight: bold; padding: 0.6rem 1rem; transition: 0.2s; }
    
    /* メトリック（ダッシュボードの数字）のリッチ化 */
    div[data-testid="stMetric"] {
        background-color: #f0f7ff; 
        padding: 15px 20px; 
        border-radius: 15px; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border-left: 5px solid #007BFF;
    }
    
    /* カードコンテナのスタイル調整 */
    div[data-testid="stForm"] > div { padding: 0; }
    
    /* カレンダービュー用 */
    .cal-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; table-layout: fixed; }
    .cal-th { background-color: #f0f2f6; border: 1px solid #ddd; padding: 6px; text-align: center; color: #333;}
    .cal-td { border: 1px solid #ddd; padding: 2px; vertical-align: top; height: 80px; background-color: #fff;}
    .cal-day { font-weight: bold; background: #fafafa; border-bottom: 1px solid #eee; text-align: right; padding-right: 5px; color: #555;}
    .cal-shift { background-color: #e6f3ff; color: #0055a4; padding: 2px; margin: 1px 0; border-radius: 3px; font-size: 0.75rem;}
    .cal-shift-off { background-color: #ffeeee; color: #cc0000; padding: 2px; margin: 1px 0; border-radius: 3px; font-size: 0.75rem;}
</style>
""", unsafe_allow_html=True)

DATA_FILE = "shift_data_v2.csv"
USER_FILE = "users.csv"

TIME_OPTIONS = [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 30)]

# --- データの読み込みと厳格な型変換 ---
def load_data():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        df["日付"] = pd.to_datetime(df["日付"], errors='coerce').dt.date
        if "休み" in df.columns:
            df["休み"] = df["休み"].astype(str).str.lower().isin(["true", "1", "t", "y", "yes"])
        else:
            df["休み"] = False
        df["開始"] = df["開始"].fillna("").astype(str).replace("nan", "")
        df["終了"] = df["終了"].fillna("").astype(str).replace("nan", "")
        df["備考"] = df["備考"].fillna("").astype(str).replace("nan", "")
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
                    st.success("✅ 登録完了！ログインしてください")
    st.stop()

# ==========================================
# 📱 メインアプリケーション
# ==========================================
current_user = st.session_state.username

col_title, col_btn = st.columns([3, 1])
col_title.markdown(f"## 📱 シフトアプリ")
if col_btn.button("ログアウト", use_container_width=True):
    st.session_state.logged_in = False
    st.rerun()

# 💡【改善アイデア3】ダッシュボード領域
st.markdown(f"#### 👤 {current_user} さんの今月の状況")
now = datetime.now()
current_month_data = df[(df["名前"] == current_user) & 
                        (pd.to_datetime(df["日付"]).dt.year == now.year) & 
                        (pd.to_datetime(df["日付"]).dt.month == now.month)]

# 出勤日数と想定勤務時間の計算
work_days = len(current_month_data[current_month_data["休み"] == False])
total_hours = 0.0

for _, row in current_month_data[current_month_data["休み"] == False].iterrows():
    try:
        s = datetime.strptime(row["開始"], "%H:%M")
        e = datetime.strptime(row["終了"], "%H:%M")
        diff = (e - s).total_seconds() / 3600
        if diff > 0:
            total_hours += diff
    except:
        pass

# リッチなメトリック表示
m1, m2 = st.columns(2)
m1.metric("今月の出勤予定日数", f"{work_days} 日")
m2.metric("想定勤務時間", f"{total_hours:.1f} 時間")

st.divider()

# タブ構成（カード入力タブをメインに）
tab1, tab2, tab3 = st.tabs(["✍️ 1週間カード入力", "📆 チームカレンダー", "⚙️ 管理"])

# ==========================================
# 💡【改善アイデア2】スマホ向け：1週間カード型入力
# ==========================================
with tab1:
    st.markdown("### 📝 シフト入力（1週間分）")
    st.caption("週の開始日を選ぶと、7日分の入力カードが表示されます。")
    
    start_date = st.date_input("週の開始日", value=date.today())
    
    with st.form("weekly_card_form"):
        form_data = []
        
        # 7日分のカードを縦に生成
        for i in range(7):
            d = start_date + timedelta(days=i)
            weekdays = ["月", "火", "水", "木", "金", "土", "日"]
            
            # 既存データの取得
            existing = df[(df["名前"] == current_user) & (df["日付"] == d)]
            def_off = False
            def_start = "09:00"
            def_end = "18:00"
            def_note = ""
            
            if not existing.empty:
                r = existing.iloc[0]
                def_off = bool(r["休み"])
                def_start = r["開始"] if r["開始"] in TIME_OPTIONS else "09:00"
                def_end = r["終了"] if r["終了"] in TIME_OPTIONS else "18:00"
                def_note = r["備考"]
            
            # カード風のUI（st.container(border=True) を使用）
            with st.container(border=True):
                # 日付と曜日
                st.markdown(f"**{d.strftime('%m/%d')} ({weekdays[d.weekday()]})**")
                
                # モバイルフレンドリーなトグルスイッチ
                is_off = st.toggle("この日は休み", value=def_off, key=f"off_{i}")
                
                c1, c2 = st.columns(2)
                start_val = c1.selectbox("開始", TIME_OPTIONS, index=TIME_OPTIONS.index(def_start), key=f"start_{i}")
                end_val = c2.selectbox("終了", TIME_OPTIONS, index=TIME_OPTIONS.index(def_end), key=f"end_{i}")
                note_val = st.text_input("備考（任意）", value=def_note, key=f"note_{i}", placeholder="例: 早退希望など")
                
                form_data.append((d, is_off, start_val, end_val, note_val))

        st.markdown("<br>", unsafe_allow_html=True)
        submitted = st.form_submit_button("✅ 1週間分をまとめて保存する", use_container_width=True, type="primary")

        if submitted:
            has_error = False
            for data in form_data:
                d, is_off, start_val, end_val, note_val = data
                if not is_off and start_val >= end_val:
                    has_error = True
                    break
            
            if has_error:
                st.error("🚨 【エラー】終了時間が開始時間より早い（または同じ）日があります。修正してください。")
            else:
                # 7日分のデータを一気に更新
                for data in form_data:
                    d, is_off, start_val, end_val, note_val = data
                    # 古いデータを削除
                    df = df[~((df["名前"] == current_user) & (df["日付"] == d))]
                    
                    start_str = start_val if not is_off else ""
                    end_str = end_val if not is_off else ""
                    
                    new_row = pd.DataFrame([[current_user, d, start_str, end_str, is_off, note_val]], 
                                           columns=["名前", "日付", "開始", "終了", "休み", "備考"])
                    df = pd.concat([df, new_row], ignore_index=True)
                
                df.to_csv(DATA_FILE, index=False)
                st.success("✅ 保存が完了しました！上のダッシュボードも更新されます。")
                st.rerun()

# ==========================================
# 【タブ2】📆 チームカレンダー
# ==========================================
with tab2:
    st.markdown("### チーム全体のカレンダー")
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
                        cal_html += f'<div class="cal-shift">{r["名前"]}<br>{r["開始"]}-{r["終了"]}</div>'
                cal_html += '</td>'
        cal_html += '</tr>'
    cal_html += '</tbody></table>'

    st.markdown(cal_html, unsafe_allow_html=True)

# ==========================================
# 【タブ3】管理画面
# ==========================================
with tab3:
    if not df.empty:
        st.caption("※管理用。全データを直接編集できます。")
        # 直接編集用のデータフレーム型推論対策
        edit_df = df.copy()
        edit_df["日付"] = pd.to_datetime(edit_df["日付"]).dt.date
        edit_df["休み"] = edit_df["休み"].astype(bool)
        
        edited_df = st.data_editor(edit_df, num_rows="dynamic", use_container_width=True)
        if st.button("データベース上書き保存", type="primary"):
            edited_df.to_csv(DATA_FILE, index=False)
            st.success("保存しました。")
            st.rerun()