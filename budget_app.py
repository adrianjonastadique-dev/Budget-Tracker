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
# --- 2. GLOBAL DATE RANGE FILTER ---
# ==========================================
st.title("💸 Smart Finance Tracker")

col_filter, _ = st.columns([1, 2])
with col_filter:
    today = datetime.date.today()
    first_day = today.replace(day=1)
    # Streamlit returns a tuple of dates when selecting a range
    selected_dates = st.date_input("📅 Dashboard Date Range (From - To)", value=(first_day, today))

# Safety check: if user clicks only the start date, treat it as a 1-day range
if len(selected_dates) == 2:
    start_date, end_date = selected_dates
else:
    start_date = end_date = selected_dates[0]

# ==========================================
# --- 3. FETCH & FILTER CLOUD DATA ---
# ==========================================
global_db = conn.read(worksheet="Sheet1", ttl=0).dropna(how="all")
if "Username" not in global_db.columns:
    global_db = pd.DataFrame(columns=["Username", "Date", "Type", "Category", "Description", "Amount"])

global_db["Date"] = global_db["Date"].astype(str)
user_log = global_db[global_db["Username"] == st.session_state.username].copy()

# Filter the database using your selected From - To dates
if not user_log.empty:
    user_log["Date_Obj"] = pd.to_datetime(user_log["Date"]).dt.date
    filtered_log = user_log[(user_log["Date_Obj"] >= start_date) & (user_log["Date_Obj"] <= end_date)]
else:
    filtered_log = user_log

# ==========================================
# --- 4. LIVE TRANSACTION GRID ---
# ==========================================
st.subheader("🧾 Log Transactions")

with st.form("transaction_form", clear_on_submit=True):
    entry_date = st.date_input("📅 Date of Transactions", datetime.date.today())
    
    col1, col2 = st.columns(2)
    with col1:
        st.write("**🏡 Core Living**")
        housing = st.number_input("🏠 Rent / Mortgage", value=None, step=500.0)
        electricity = st.number_input("⚡ Electricity", value=None, step=500.0)
        water = st.number_input("💧 Water", value=None, step=100.0)
        internet = st.number_input("🌐 Internet", value=None, step=100.0)
        groceries = st.number_input("🛒 Groceries", value=None, step=500.0)
        business_ops = st.number_input("⚙️ Business Ops", value=None, step=500.0)

    with col2:
        st.write("**💳 Debt, Subs & Lifestyle**")
        car_payment = st.number_input("🚘 Car Payment", value=None, step=1000.0)
        credit_card = st.number_input("💳 Credit Cards", value=None, step=500.0)
        subscriptions = st.number_input("📺 Subscriptions", value=None, step=100.0)
        investments = st.number_input("📈 Investments", value=None, step=500.0)
        transpo = st.number_input("🚗 Gas & Auto", value=None, step=500.0)
        leisure = st.number_input("🍔 Dining Out", value=None, step=500.0)
        
    st.divider()
    st.write("**🚨 Unplanned & Extra**")
    c_ext1, c_ext2 = st.columns(2)
    with c_ext1:
        emergency_spend = st.number_input("🚨 Emergency Spend", value=None, step=500.0)
    with c_ext2:
        extra_income = st.number_input("💰 Extra / Unexpected Income", value=None, step=500.0)

    if st.form_submit_button("➕ Save Transactions"):
        new_rows = []
        date_str = entry_date.strftime("%Y-%m-%d")
        
        # Helper function to compile only filled entries
        def add_tx(cat, amt, tx_type="Expense"):
            if amt is not None and amt > 0:
                new_rows.append({
                    "Username": st.session_state.username,
                    "Date": date_str,
                    "Type": tx_type,
                    "Category": cat,
                    "Description": "",
                    "Amount": amt
                })
                
        add_tx("Housing", housing)
        add_tx("Electricity", electricity)
        add_tx("Water", water)
        add_tx("Internet", internet)
        add_tx("Groceries", groceries)
        add_tx("Business Ops", business_ops)
        add_tx("Car Payment", car_payment)
        add_tx("Credit Cards", credit_card)
        add_tx("Subscriptions", subscriptions)
        add_tx("Investments", investments)
        add_tx("Transportation", transpo)
        add_tx("Leisure", leisure)
        add_tx("Emergency Spend", emergency_spend)
        add_tx("Extra Income", extra_income, "Extra Income")
        
        if new_rows:
            updated_db = pd.concat([global_db, pd.DataFrame(new_rows)], ignore_index=True)
            conn.update(worksheet="Sheet1", data=updated_db)
            st.cache_data.clear()
            st.rerun()
        else:
            st.warning("Please enter an amount in at least one category to save.")

st.divider()

# ==========================================
# --- 5. CALCULATIONS & EMERGENCY DRAIN ---
# ==========================================
extra_income_log = filtered_log[filtered_log["Type"] == "Extra Income"]
total_extra_income = extra_income_log["Amount"].sum() if not extra_income_log.empty else 0

expense_log = filtered_log[filtered_log["Type"] == "Expense"]

emergency_log = expense_log[expense_log["Category"] == "Emergency Spend"]
total_emergency = emergency_log["Amount"].sum() if not emergency_log.empty else 0

baseline_expense_log = expense_log[expense_log["Category"] != "Emergency Spend"]
total_baseline_expenses = baseline_expense_log["Amount"].sum() if not baseline_expense_log.empty else 0

total_income = base_income + total_extra_income
actual_remaining = total_income - total_baseline_expenses - total_emergency

# ==========================================
# --- 6. CASH FLOW ANALYTICS ---
# ==========================================
st.subheader("📊 Cash Flow Analysis")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Income", f"₱{total_income:,.2f}")
m2.metric("Baseline Expenses", f"₱{total_baseline_expenses:,.2f}")
m3.metric("Emergency Drain", f"₱{total_emergency:,.2f}", delta=-float(total_emergency), delta_color="inverse")
m4.metric("Actual Savings", f"₱{actual_remaining:,.2f}", delta=float(actual_remaining))

chart_col, hist_col = st.columns(2)

with chart_col:
    st.write(f"**Expense Breakdown ({start_date.strftime('%b %d')} - {end_date.strftime('%b %d')})**")
    if not baseline_expense_log.empty:
        fig = px.pie(baseline_expense_log, names="Category", values="Amount", hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig)
    else:
        empty_data = pd.DataFrame({"Category": ["Awaiting Data"], "Amount": [1]})
        fig = px.pie(empty_data, names="Category", values="Amount", hole=0.4, color_discrete_sequence=["#e0e0e0"])
        fig.update_traces(textinfo='none', hoverinfo='skip')
        st.plotly_chart(fig)

with hist_col:
    st.write(f"**☁️ Cloud Ledger ({start_date.strftime('%b %d')} - {end_date.strftime('%b %d')})**")
    if not filtered_log.empty:
        display_log = filtered_log.sort_values(by="Date", ascending=False)
        for original_index, row in display_log.iterrows():
            icon = "🟢" if row["Type"] == "Extra Income" else "🔴"
            col_icon, col_desc, col_amt, col_del = st.columns([1, 4, 3, 1])
            with col_icon: st.write(icon)
            with col_desc: st.write(f"**{row['Category']}**\n{row['Date']}")
            with col_amt: st.write(f"₱ {row['Amount']:,.2f}")
            with col_del:
                if st.button("❌", key=f"del_{original_index}"):
                    global_db = global_db.drop(original_index)
                    conn.update(worksheet="Sheet1", data=global_db)
                    st.cache_data.clear()
                    st.rerun()
    else:
        st.info("No transactions logged in this range.")

# ==========================================
# --- 7. SINKING FUNDS & GOALS ---
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
