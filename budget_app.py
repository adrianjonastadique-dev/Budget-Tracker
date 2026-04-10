import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Smart Budget", layout="wide")

# ==========================================
# --- ISOLATED BUDGET DATABASE CONNECTION ---
# ==========================================
conn = st.connection("budget_gsheets", type=GSheetsConnection)

if "budget_auth" not in st.session_state:
    st.session_state.budget_auth = False

# ==========================================
# --- SECURE LOGIN ---
# ==========================================
if not st.session_state.budget_auth:
    st.title("💼 Smart Finance Tracker")
    st.info("Enter your Client ID to access your financial dashboard.")
    
    entered_user = st.text_input("Username / Client ID")
    entered_pwd = st.text_input("Password", type="password")
    
    if st.button("Secure Login"):
        if entered_user and entered_pwd:
            try:
                users_db = conn.read(worksheet="Users", ttl=0).dropna(subset=["Username"])
                user_match = users_db[users_db["Username"].astype(str) == entered_user.strip()]
                
                if not user_match.empty and str(user_match.iloc[0]["Password"]).strip() == entered_pwd.strip():
                    st.session_state.budget_auth = True
                    st.session_state.username = entered_user.strip()
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials.")
            except Exception as e:
                st.error("🚨 Database error. Ensure the 'Users' tab is set up correctly in your Budget_DB.")
    st.stop()

# ==========================================
# --- 1. THE INCOME ENGINE (SIDEBAR) ---
# ==========================================
dk = datetime.date.today().strftime("%Y%m%d")

with st.sidebar:
    st.header(f"👤 {st.session_state.username}")
    st.divider()
    st.header("💰 Income Engine")
    
    salary_type = st.radio("Pay Frequency:", ["Weekly", "Bi-Monthly", "Once a Month"], key="freq")
    
    if salary_type == "Weekly":
        with st.expander("📝 Enter Weekly Pay", expanded=True):
            weekly_pay = st.number_input("Average Weekly Net (₱)", min_value=0.0, step=500.0, key="wp")
            base_salary = (weekly_pay or 0) * 4 
    elif salary_type == "Bi-Monthly":
        with st.expander("📝 Enter Bi-Monthly Paychecks", expanded=True):
            pay1 = st.number_input("1st Paycheck (₱)", min_value=0.0, step=1000.0, key="p1")
            pay2 = st.number_input("2nd Paycheck (₱)", min_value=0.0, step=1000.0, key="p2")
            base_salary = (pay1 or 0) + (pay2 or 0)
    else:
        with st.expander("📝 Enter Monthly Salary", expanded=True):
            salary_input = st.number_input("Total Monthly Net (₱)", min_value=0.0, step=1000.0, key="si")
            base_salary = salary_input or 0

    side_hustle = st.number_input("Business / Side Hustle (₱)", min_value=0.0, step=1000.0, key="sh")
    base_income = base_salary + (side_hustle or 0)
    st.success(f"**Baseline Income: ₱{base_income:,.2f}**")

# ==========================================
# --- 2. FETCH LIVE CLOUD DATA ---
# ==========================================
global_db = conn.read(worksheet="Sheet1", ttl=0).dropna(how="all")
if "Username" not in global_db.columns:
    global_db = pd.DataFrame(columns=["Username", "Date", "Type", "Category", "Description", "Amount"])

global_db["Date"] = global_db["Date"].astype(str)
user_log = global_db[global_db["Username"] == st.session_state.username].copy()

if not user_log.empty:
    user_log["Date_Obj"] = pd.to_datetime(user_log["Date"])
    current_month = datetime.date.today().replace(day=1)
    this_month_log = user_log[user_log["Date_Obj"].dt.date >= current_month]
else:
    this_month_log = user_log

# ==========================================
# --- 3. LIVE TRANSACTION LOGGER ---
# ==========================================
st.title("💸 Smart Finance Tracker")
st.subheader("🧾 Log Transaction")

EXPENSE_CATS = [
    "Housing", "Electricity", "Water", "Internet", "Groceries", 
    "Business Ops", "Car Payment", "Credit Cards", "Subscriptions", 
    "Investments", "Transportation", "Leisure", "Misc"
]

with st.form("transaction_form", clear_on_submit=True):
    c1, c2 = st.columns([1, 2])
    with c1: 
        t_date = st.date_input("Date", datetime.date.today())
        t_type = st.radio("Type", ["Expense", "Extra Income"], horizontal=True)
    with c2:
        t_cat = st.selectbox("Category", ["Bonus/Gift", "Refund", "Other"] if t_type == "Extra Income" else EXPENSE_CATS)
        t_desc = st.text_input("Description (Optional)")
        t_amount = st.number_input("Amount (₱)", min_value=0.0, step=100.0)
        
    if st.form_submit_button("➕ Save Transaction"):
        if t_amount > 0:
            new_entry = pd.DataFrame([{
                "Username": st.session_state.username,
                "Date": t_date.strftime("%Y-%m-%d"),
                "Type": t_type,
                "Category": t_cat,
                "Description": t_desc,
                "Amount": t_amount
            }])
            updated_db = pd.concat([global_db, new_entry], ignore_index=True)
            conn.update(worksheet="Sheet1", data=updated_db)
            st.cache_data.clear()
            st.rerun()
        else:
            st.error("Amount must be greater than zero.")

st.divider()

# ==========================================
# --- 4. CALCULATIONS & EMERGENCY DRAIN ---
# ==========================================
total_logged_income = this_month_log[this_month_log["Type"] == "Extra Income"]["Amount"].sum() if not this_month_log.empty else 0
total_expenses = this_month_log[this_month_log["Type"] == "Expense"]["Amount"].sum() if not this_month_log.empty else 0

total_income = base_income + total_logged_income

st.write("### 🚨 Unplanned / Emergency Expenses")
safe_emergency = st.number_input("Total Emergency Spend this cycle (₱)", min_value=0.0, step=500.0, key="emg")

actual_remaining = total_income - total_expenses - (safe_emergency or 0)

# ==========================================
# --- 5. CASH FLOW ANALYTICS ---
# ==========================================
st.subheader("📊 Cash Flow Analysis")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Income", f"₱{total_income:,.2f}")
m2.metric("Total Expenses", f"₱{total_expenses:,.2f}")
m3.metric("Emergency Drain", f"₱{(safe_emergency or 0):,.2f}", delta=-float(safe_emergency or 0), delta_color="inverse")
m4.metric("Actual Savings", f"₱{actual_remaining:,.2f}", delta=float(actual_remaining))

chart_col, hist_col = st.columns(2)

with chart_col:
    st.write("**Expense Breakdown**")
    expense_data = this_month_log[this_month_log["Type"] == "Expense"]
    
    if not expense_data.empty:
        fig = px.pie(expense_data, names="Category", values="Amount", hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig)
    else:
        empty_data = pd.DataFrame({"Category": ["Awaiting Data"], "Amount": [1]})
        fig = px.pie(empty_data, names="Category", values="Amount", hole=0.4, color_discrete_sequence=["#e0e0e0"])
        fig.update_traces(textinfo='none', hoverinfo='skip')
        st.plotly_chart(fig)

with hist_col:
    st.write("**☁️ Cloud Ledger (This Month)**")
    if not this_month_log.empty:
        display_log = this_month_log.sort_values(by="Date", ascending=False)
        for original_index, row in display_log.iterrows():
            icon = "🟢" if row["Type"] == "Extra Income" else "🔴"
            col_icon, col_desc, col_amt, col_del = st.columns([1, 4, 3, 1])
            with col_icon: st.write(icon)
            with col_desc: st.write(f"**{row['Category']}**\n{row['Description']}")
            with col_amt: st.write(f"₱ {row['Amount']:,.2f}")
            with col_del:
                if st.button("❌", key=f"del_{original_index}"):
                    global_db = global_db.drop(original_index)
                    conn.update(worksheet="Sheet1", data=global_db)
                    st.cache_data.clear()
                    st.rerun()
    else:
        st.info("No transactions logged this month.")

# ==========================================
# --- 6. SINKING FUNDS & GOALS ---
# ==========================================
st.write("---")
st.write("### 🎯 Custom Sinking Funds & Goals")

if actual_remaining > 0:
    st.write(f"You have a surplus of **₱{actual_remaining:,.2f}** to allocate.")
    if 'goal_count' not in st.session_state:
        st.session_state.goal_count = 0

    col_btn1, col_btn2, _ = st.columns([1, 1, 4])
    with col_btn1:
        if st.button("➕ Add Goal"):
            st.session_state.goal_count += 1
    with col_btn2:
        if st.session_state.goal_count > 0:
            if st.button("➖ Remove Goal"):
                st.session_state.goal_count -= 1

    if st.session_state.goal_count > 0:
        col_g1, col_g2 = st.columns(2)
        total_allocated = 0
        goal_data = [] 
        
        with col_g1:
            for i in range(st.session_state.goal_count):
                g_name = st.text_input(f"Goal {i+1} Name", value="", key=f"name_{i}")
                g_pct = st.slider(f"{g_name or f'Goal {i+1}'} (%)", 0, 100, 0, key=f"pct_{i}")
                total_allocated += g_pct
                goal_data.append((g_name, g_pct))
                
        with col_g2:
            if total_allocated > 100:
                st.error(f"⚠️ You allocated {total_allocated}%. Adjust to 100% or less.")
            else:
                for i, (name, pct) in enumerate(goal_data):
                    val = actual_remaining * (pct / 100)
                    st.caption(f"**{name or f'Goal {i+1}'}**: ₱{val:,.2f}")
                    st.progress(pct / 100)
else:
    st.info("💡 No surplus savings to allocate this cycle.")
