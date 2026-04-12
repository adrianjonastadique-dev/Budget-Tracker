import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import calendar
import time
import uuid
import random
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Smart Budget", layout="wide")

# Hide Streamlit branding for a clean UI
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# ==========================================
# --- ISOLATED BUDGET DATABASE CONNECTION ---
# ==========================================
conn = st.connection("budget_gsheets", type=GSheetsConnection)

if "budget_auth" not in st.session_state:
    st.session_state.budget_auth = False

# ==========================================
# --- SECURE LOGIN & REGISTRATION ---
# ==========================================
if not st.session_state.budget_auth:
    st.title("💼 Smart Finance Tracker")
    
    tab_login, tab_register = st.tabs(["🔑 Secure Login", "📝 Create Account"])
    
    # --- TAB 1: LOGIN ---
    with tab_login:
        st.info("Enter your Client ID to access your financial dashboard.")
        
        st.markdown(
            """
            <style>
            div[data-testid="stTextInput"]:has(input[aria-label="honeypot"]) {
                display: none;
            }
            </style>
            """,
            unsafe_allow_html=True
        )
        honeypot = st.text_input("honeypot", key="hp_input", label_visibility="hidden")
        
        entered_user = st.text_input("Username / Client ID", key="log_user")
        entered_pwd = st.text_input("Password", type="password", key="log_pwd")
        
        if st.button("Secure Login"):
            if honeypot:
                st.error("🤖 Bot activity detected.")
                st.stop()
                
            current_time = time.time()
            if "last_login_attempt" in st.session_state:
                if current_time - st.session_state.last_login_attempt < 3:
                    st.warning("⏳ Please wait a few seconds before trying again.")
                    st.stop()
            st.session_state.last_login_attempt = current_time

            if entered_user and entered_pwd:
                try:
                    users_db = conn.read(worksheet="Users", ttl=600)
                    
                    if "Session_ID" not in users_db.columns:
                        users_db["Session_ID"] = ""
                        
                    users_db = users_db.dropna(subset=["Username"])
                    user_match = users_db[users_db["Username"].astype(str) == entered_user.strip()]
                    
                    if not user_match.empty and str(user_match.iloc[0]["Password"]).strip() == entered_pwd.strip():
                        new_session_id = str(uuid.uuid4())
                        row_idx = users_db.index[users_db["Username"].astype(str) == entered_user.strip()].tolist()[0]
                        users_db.at[row_idx, "Session_ID"] = new_session_id
                        conn.update(worksheet="Users", data=users_db)
                        st.cache_data.clear()
                        
                        st.session_state.budget_auth = True
                        st.session_state.username = entered_user.strip()
                        st.session_state.session_id = new_session_id
                        
                        income_cols = [
                            "Pay_Frequency", "Inc_Weekly", "Inc_BiMonth_1", "Inc_BiMonth_2", "Inc_Monthly",
                            "S_Pay_Frequency", "S_Inc_Weekly", "S_Inc_BiMonth_1", "S_Inc_BiMonth_2", "S_Inc_Monthly",
                            "Side_Hustle"
                        ]
                        for col in income_cols:
                            if col in user_match.columns:
                                val = user_match.iloc[0][col]
                                if pd.isna(val):
                                    st.session_state[col] = "Monthly" if "Frequency" in col else 0.0
                                else:
                                    st.session_state[col] = val
                            else:
                                st.session_state[col] = "Monthly" if "Frequency" in col else 0.0

                        st.success("✅ Login successful!")
                        time.sleep(0.5) 
                        st.rerun()
                    else:
                        st.error("❌ Invalid credentials.")
                except Exception as e:
                    st.error(f"🚨 Database error: Ensure the 'Users' tab is set up correctly. Details: {e}")
                    
    # --- TAB 2: REGISTRATION ---
    with tab_register:
        st.info("Register a new account to start tracking your finances.")
        
        new_user = st.text_input("Choose a Username / Client ID", key="reg_user")
        new_pwd = st.text_input("Choose a Password", type="password", key="reg_pwd")
        confirm_pwd = st.text_input("Confirm Password", type="password", key="reg_confirm")
        
        if "captcha_a" not in st.session_state:
            st.session_state.captcha_a = random.randint(1, 10)
            st.session_state.captcha_b = random.randint(1, 10)
            
        captcha_ans = st.text_input(f"🤖 Verification: What is {st.session_state.captcha_a} + {st.session_state.captcha_b}?", key="reg_captcha")
        
        if st.button("Register Account", type="primary"):
            if new_user and new_pwd and confirm_pwd and captcha_ans:
                if new_pwd != confirm_pwd:
                    st.error("❌ Passwords do not match.")
                elif not captcha_ans.isdigit() or int(captcha_ans) != (st.session_state.captcha_a + st.session_state.captcha_b):
                    st.error("❌ Incorrect verification answer. Please try again.")
                else:
                    try:
                        users_db = conn.read(worksheet="Users", ttl=600)
                        
                        if "Username" in users_db.columns and new_user.strip() in users_db["Username"].astype(str).values:
                            st.error("❌ Username already exists. Please choose another.")
                        else:
                            new_profile = {
                                "Username": new_user.strip(),
                                "Password": new_pwd.strip(),
                                "Session_ID": "",
                                "Join_Date": datetime.date.today().strftime("%Y-%m-%d"),
                                "Pay_Frequency": "Monthly",
                                "Inc_Weekly": 0.0,
                                "Inc_BiMonth_1": 0.0,
                                "Inc_BiMonth_2": 0.0,
                                "Inc_Monthly": 0.0,
                                "S_Pay_Frequency": "Monthly",
                                "S_Inc_Weekly": 0.0,
                                "S_Inc_BiMonth_1": 0.0,
                                "S_Inc_BiMonth_2": 0.0,
                                "S_Inc_Monthly": 0.0,
                                "Side_Hustle": 0.0
                            }
                            
                            updated_users = pd.concat([users_db, pd.DataFrame([new_profile])], ignore_index=True)
                            conn.update(worksheet="Users", data=updated_users)
                            st.cache_data.clear() 
                            
                            st.success("✅ Account created successfully! You can now switch to the Login tab.")
                            
                            st.session_state.captcha_a = random.randint(1, 10)
                            st.session_state.captcha_b = random.randint(1, 10)
                    except Exception as e:
                        st.error(f"🚨 Registration error: {e}")
            else:
                st.warning("⚠️ Please fill out all fields.")
    st.stop()

# ==========================================
# --- 1. THE PERMANENT INCOME ENGINE ---
# ==========================================
if "show_success" in st.session_state and st.session_state.show_success:
    st.success("✅ Dashboard Snapshot Safely Synced to Cloud!")
    st.session_state.show_success = False

if "p_inc_w" not in st.session_state: st.session_state.p_inc_w = float(st.session_state.get("Inc_Weekly", 0.0))
if "p_inc_b1" not in st.session_state: st.session_state.p_inc_b1 = float(st.session_state.get("Inc_BiMonth_1", 0.0))
if "p_inc_b2" not in st.session_state: st.session_state.p_inc_b2 = float(st.session_state.get("Inc_BiMonth_2", 0.0))
if "p_inc_m" not in st.session_state: st.session_state.p_inc_m = float(st.session_state.get("Inc_Monthly", 0.0))

if "s_inc_w" not in st.session_state: st.session_state.s_inc_w = float(st.session_state.get("S_Inc_Weekly", 0.0))
if "s_inc_b1" not in st.session_state: st.session_state.s_inc_b1 = float(st.session_state.get("S_Inc_BiMonth_1", 0.0))
if "s_inc_b2" not in st.session_state: st.session_state.s_inc_b2 = float(st.session_state.get("S_Inc_BiMonth_2", 0.0))
if "s_inc_m" not in st.session_state: st.session_state.s_inc_m = float(st.session_state.get("S_Inc_Monthly", 0.0))

with st.sidebar:
    st.header(f"👤 {st.session_state.username}")
    st.divider()
    st.header("💰 Income Engine")
    
    tab_primary, tab_secondary = st.tabs(["Primary", "Secondary"])
    
    # --- PRIMARY INCOME ---
    with tab_primary:
        saved_freq = st.session_state.get("Pay_Frequency", "Monthly")
        if saved_freq not in ["Weekly", "Bi-Monthly", "Monthly"]:
            saved_freq = "Monthly"
            
        freq_idx = ["Weekly", "Bi-Monthly", "Monthly"].index(saved_freq)
        p_salary_type = st.radio("Pay Frequency:", ["Weekly", "Bi-Monthly", "Monthly"], index=freq_idx, key="p_freq")
        
        if "last_p_freq" not in st.session_state:
            st.session_state.last_p_freq = saved_freq
            
        if p_salary_type != st.session_state.last_p_freq:
            old_freq = st.session_state.last_p_freq
            m_val = 0.0
            if old_freq == "Weekly":
                m_val = st.session_state.p_inc_w * 4
            elif old_freq == "Bi-Monthly":
                m_val = st.session_state.p_inc_b1 + st.session_state.p_inc_b2
            else:
                m_val = st.session_state.p_inc_m
                
            if p_salary_type == "Weekly":
                st.session_state.p_inc_w = m_val / 4
            elif p_salary_type == "Bi-Monthly":
                st.session_state.p_inc_b1 = m_val / 2
                st.session_state.p_inc_b2 = m_val / 2
            else:
                st.session_state.p_inc_m = m_val
                
            st.session_state.last_p_freq = p_salary_type
            st.rerun()

        if p_salary_type == "Weekly":
            with st.expander("📝 Enter Weekly Pay", expanded=True):
                current_w = st.number_input("Average Weekly Net (₱)", min_value=0.0, step=500.0, key="p_inc_w")
                p_base_salary = current_w * 4 
        elif p_salary_type == "Bi-Monthly":
            with st.expander("📝 Enter Bi-Monthly Paychecks", expanded=True):
                current_b1 = st.number_input("1st Paycheck (₱)", min_value=0.0, step=1000.0, key="p_inc_b1")
                current_b2 = st.number_input("2nd Paycheck (₱)", min_value=0.0, step=1000.0, key="p_inc_b2")
                p_base_salary = current_b1 + current_b2
        else:
            with st.expander("📝 Enter Monthly Salary", expanded=True):
                current_m = st.number_input("Total Monthly Net (₱)", min_value=0.0, step=1000.0, key="p_inc_m")
                p_base_salary = current_m

    # --- SECONDARY INCOME ---
    with tab_secondary:
        s_saved_freq = st.session_state.get("S_Pay_Frequency", "Monthly")
        if s_saved_freq not in ["Weekly", "Bi-Monthly", "Monthly"]:
            s_saved_freq = "Monthly"
            
        s_freq_idx = ["Weekly", "Bi-Monthly", "Monthly"].index(s_saved_freq)
        s_salary_type = st.radio("Pay Frequency:", ["Weekly", "Bi-Monthly", "Monthly"], index=s_freq_idx, key="s_freq")
        
        if "last_s_freq" not in st.session_state:
            st.session_state.last_s_freq = s_saved_freq
            
        if s_salary_type != st.session_state.last_s_freq:
            old_freq = st.session_state.last_s_freq
            m_val = 0.0
            if old_freq == "Weekly":
                m_val = st.session_state.s_inc_w * 4
            elif old_freq == "Bi-Monthly":
                m_val = st.session_state.s_inc_b1 + st.session_state.s_inc_b2
            else:
                m_val = st.session_state.s_inc_m
                
            if s_salary_type == "Weekly":
                st.session_state.s_inc_w = m_val / 4
            elif s_salary_type == "Bi-Monthly":
                st.session_state.s_inc_b1 = m_val / 2
                st.session_state.s_inc_b2 = m_val / 2
            else:
                st.session_state.s_inc_m = m_val
                
            st.session_state.last_s_freq = s_salary_type
            st.rerun()

        if s_salary_type == "Weekly":
            with st.expander("📝 Enter Weekly Pay", expanded=True):
                s_current_w = st.number_input("Average Weekly Net (₱)", min_value=0.0, step=500.0, key="s_inc_w")
                s_base_salary = s_current_w * 4 
        elif s_salary_type == "Bi-Monthly":
            with st.expander("📝 Enter Bi-Monthly Paychecks", expanded=True):
                s_current_b1 = st.number_input("1st Paycheck (₱)", min_value=0.0, step=1000.0, key="s_inc_b1")
                s_current_b2 = st.number_input("2nd Paycheck (₱)", min_value=0.0, step=1000.0, key="s_inc_b2")
                s_base_salary = s_current_b1 + s_current_b2
        else:
            with st.expander("📝 Enter Monthly Salary", expanded=True):
                s_current_m = st.number_input("Total Monthly Net (₱)", min_value=0.0, step=1000.0, key="s_inc_m")
                s_base_salary = s_current_m

    side = float(st.session_state.get("Side_Hustle", 0.0))
    side_hustle = st.number_input("Business / Side Hustle (₱)", value=side, min_value=0.0, step=1000.0, key="sh")
    
    base_income = p_base_salary + s_base_salary + side_hustle
    
    st.success(f"**Total Monthly Income: ₱{base_income:,.2f}**")
    
    if st.button("💾 Save Income Profile", use_container_width=True):
        try:
            users_db = conn.read(worksheet="Users", ttl=600)
            row_idx = users_db.index[users_db["Username"].astype(str) == st.session_state.username].tolist()[0]
            
            income_cols = [
                "Pay_Frequency", "Inc_Weekly", "Inc_BiMonth_1", "Inc_BiMonth_2", "Inc_Monthly",
                "S_Pay_Frequency", "S_Inc_Weekly", "S_Inc_BiMonth_1", "S_Inc_BiMonth_2", "S_Inc_Monthly",
                "Side_Hustle"
            ]
            for col in income_cols:
                if col not in users_db.columns:
                    users_db[col] = 0.0 if "Frequency" not in col else "Monthly"
            
            users_db.at[row_idx, "Pay_Frequency"] = p_salary_type
            users_db.at[row_idx, "Inc_Weekly"] = st.session_state.p_inc_w
            users_db.at[row_idx, "Inc_BiMonth_1"] = st.session_state.p_inc_b1
            users_db.at[row_idx, "Inc_BiMonth_2"] = st.session_state.p_inc_b2
            users_db.at[row_idx, "Inc_Monthly"] = st.session_state.p_inc_m
            
            users_db.at[row_idx, "S_Pay_Frequency"] = s_salary_type
            users_db.at[row_idx, "S_Inc_Weekly"] = st.session_state.s_inc_w
            users_db.at[row_idx, "S_Inc_BiMonth_1"] = st.session_state.s_inc_b1
            users_db.at[row_idx, "S_Inc_BiMonth_2"] = st.session_state.s_inc_b2
            users_db.at[row_idx, "S_Inc_Monthly"] = st.session_state.s_inc_m
            
            users_db.at[row_idx, "Side_Hustle"] = side_hustle
            conn.update(worksheet="Users", data=users_db)
            
            st.session_state["Pay_Frequency"] = p_salary_type
            st.session_state["Inc_Weekly"] = st.session_state.p_inc_w
            st.session_state["Inc_BiMonth_1"] = st.session_state.p_inc_b1
            st.session_state["Inc_BiMonth_2"] = st.session_state.p_inc_b2
            st.session_state["Inc_Monthly"] = st.session_state.p_inc_m
            
            st.session_state["S_Pay_Frequency"] = s_salary_type
            st.session_state["S_Inc_Weekly"] = st.session_state.s_inc_w
            st.session_state["S_Inc_BiMonth_1"] = st.session_state.s_inc_b1
            st.session_state["S_Inc_BiMonth_2"] = st.session_state.s_inc_b2
            st.session_state["S_Inc_Monthly"] = st.session_state.s_inc_m
            
            st.session_state["Side_Hustle"] = side_hustle
            
            st.cache_data.clear()
            st.toast("✅ Income Profile Saved to Cloud!")
        except Exception as e:
            st.error(f"Failed to save to database: {e}")

# ==========================================
# --- 2. DYNAMIC BUCKET ENGINE ---
# ==========================================
st.title("💸 Smart Finance Tracker")
st.write("### 📅 Select Budget Cycle")

col_m, col_y, col_type, col_bucket = st.columns(4)
today = datetime.date.today()

with col_m:
    month_names = list(calendar.month_name)[1:]
    selected_month_name = st.selectbox("Month", options=month_names, index=today.month - 1)
    selected_month = month_names.index(selected_month_name) + 1
    
with col_y:
    selected_year = st.selectbox("Year", options=[today.year - 1, today.year, today.year + 1], index=1)
    
with col_type:
    cycle_type = st.selectbox("Cycle Type", ["Monthly", "Bi-Monthly", "Weekly"])

_, last_day = calendar.monthrange(selected_year, selected_month)

if cycle_type == "Monthly":
    buckets = [("Full Month", datetime.date(selected_year, selected_month, 1), datetime.date(selected_year, selected_month, last_day))]
    income_divisor = 1
elif cycle_type == "Bi-Monthly":
    buckets = [
        ("1st Cutoff (1st - 15th)", datetime.date(selected_year, selected_month, 1), datetime.date(selected_year, selected_month, 15)),
        (f"2nd Cutoff (16th - {last_day}th)", datetime.date(selected_year, selected_month, 16), datetime.date(selected_year, selected_month, last_day))
    ]
    income_divisor = 2
elif cycle_type == "Weekly":
    buckets = []
    current_day = 1
    week_num = 1
    while current_day <= last_day:
        end_day = min(current_day + 6, last_day)
        buckets.append((f"Week {week_num} ({current_day} - {end_day})", datetime.date(selected_year, selected_month, current_day), datetime.date(selected_year, selected_month, end_day)))
        current_day += 7
        week_num += 1
    income_divisor = len(buckets)

with col_bucket:
    bucket_names = [b[0] for b in buckets]
    selected_bucket_name = st.selectbox("Select Specific Bucket", bucket_names)

for b in buckets:
    if b[0] == selected_bucket_name:
        start_date = b[1]
        end_date = b[2]
        break

bucket_base_income = base_income / income_divisor

# ==========================================
# --- 3. SEAMLESS BACKGROUND AUTO-CONVERTER ---
# ==========================================
global_db = conn.read(worksheet="Sheet1", ttl=600).dropna(how="all")

if "Username" not in global_db.columns:
    global_db = pd.DataFrame(columns=["Username", "Date", "Type", "Category", "Description", "Amount", "Cycle_Mode"])
if "Cycle_Mode" not in global_db.columns:
    global_db["Cycle_Mode"] = "Monthly"

global_db["Date"] = pd.to_datetime(global_db["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
global_db["Amount"] = global_db["Amount"].astype(str).str.replace(r"[^\d.]", "", regex=True)
global_db["Amount"] = pd.to_numeric(global_db["Amount"], errors="coerce").fillna(0.0)

month_start = datetime.date(selected_year, selected_month, 1)
month_end = datetime.date(selected_year, selected_month, last_day)

month_records = global_db[
    (global_db["Username"] == st.session_state.username) & 
    (pd.to_datetime(global_db["Date"], errors="coerce").dt.date >= month_start) & 
    (pd.to_datetime(global_db["Date"], errors="coerce").dt.date <= month_end)
]

modes_used = month_records["Cycle_Mode"].dropna().unique()
active_mode = modes_used[0] if len(modes_used) > 0 else None

if active_mode and cycle_type != active_mode:
    if active_mode == "Monthly" and cycle_type == "Bi-Monthly":
        st.toast("🔄 Auto-distributing Monthly data to Bi-Monthly...")
        mask_delete = ~((global_db["Username"] == st.session_state.username) & 
                        (pd.to_datetime(global_db["Date"], errors="coerce").dt.date >= month_start) & 
                        (pd.to_datetime(global_db["Date"], errors="coerce").dt.date <= month_end) & 
                        (global_db["Cycle_Mode"] == "Monthly"))
        cleaned_db = global_db[mask_delete]
        
        new_converted_rows = []
        monthly_data = month_records[month_records["Cycle_Mode"] == "Monthly"]
        
        date_1st = datetime.date(selected_year, selected_month, 1).strftime("%Y-%m-%d")
        date_16th = datetime.date(selected_year, selected_month, 16).strftime("%Y-%m-%d")

        for _, row in monthly_data.iterrows():
            half_amt = float(row["Amount"]) / 2
            row1 = row.to_dict(); row1["Date"] = date_1st; row1["Amount"] = half_amt; row1["Cycle_Mode"] = "Bi-Monthly"
            row2 = row.to_dict(); row2["Date"] = date_16th; row2["Amount"] = half_amt; row2["Cycle_Mode"] = "Bi-Monthly"
            new_converted_rows.extend([row1, row2])
            
        updated_db = pd.concat([cleaned_db, pd.DataFrame(new_converted_rows)], ignore_index=True)
        conn.update(worksheet="Sheet1", data=updated_db)
        
        st.session_state.pop("loaded_date_range", None) 
        st.cache_data.clear()
        st.rerun() 
        
    elif active_mode == "Bi-Monthly" and cycle_type == "Monthly":
        st.toast("🔄 Auto-consolidating Bi-Monthly data to Monthly...")
        mask_delete = ~((global_db["Username"] == st.session_state.username) & 
                        (pd.to_datetime(global_db["Date"], errors="coerce").dt.date >= month_start) & 
                        (pd.to_datetime(global_db["Date"], errors="coerce").dt.date <= month_end) & 
                        (global_db["Cycle_Mode"] == "Bi-Monthly"))
        cleaned_db = global_db[mask_delete]
        
        new_converted_rows = []
        bimonthly_data = month_records[month_records["Cycle_Mode"] == "Bi-Monthly"]
        
        grouped = bimonthly_data.groupby(["Category", "Type", "Description"])["Amount"].sum
