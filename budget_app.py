import streamlit as st
import pandas as pd
import datetime
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Cash Flow Tracker", layout="centered")

# ==========================================
# --- ISOLATED BUDGET DATABASE CONNECTION ---
# ==========================================
# This ensures it looks for [connections.budget_gsheets] in your Streamlit Secrets
conn = st.connection("budget_gsheets", type=GSheetsConnection)

if "budget_auth" not in st.session_state:
    st.session_state.budget_auth = False

# ==========================================
# --- SECURE LOGIN ---
# ==========================================
if not st.session_state.budget_auth:
    st.title("💼 Enterprise Budget Tracker")
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
                    
                    # Load Monthly Savings Goal
                    st.session_state.savings_goal = float(user_match.iloc[0].get("Monthly_Goal", 0))
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials.")
            except Exception as e:
                st.error("🚨 Database error. Ensure the 'Users' tab is set up correctly in your new Budget_DB.")
    st.stop()

# ==========================================
# --- MAIN DASHBOARD ---
# ==========================================

with st.sidebar:
    st.header(f"👤 {st.session_state.username}")
    st.divider()
    new_goal = st.number_input("Monthly Savings Goal (₱):", min_value=0, value=int(st.session_state.savings_goal), step=1000)
    
    if new_goal != st.session_state.savings_goal:
        st.session_state.savings_goal = new_goal
        users_db = conn.read(worksheet="Users", ttl=0)
        users_db.loc[users_db["Username"] == st.session_state.username, "Monthly_Goal"] = new_goal
        conn.update(worksheet="Users", data=users_db)
        st.success("Goal Updated!")

st.title("💸 Monthly Cash Flow")

# Fetch and filter the main ledger
global_db = conn.read(worksheet="Sheet1", ttl=0).dropna(how="all")
if "Username" not in global_db.columns:
    global_db = pd.DataFrame(columns=["Username", "Date", "Type", "Category", "Description", "Amount"])

global_db["Date"] = pd.to_datetime(global_db["Date"])
user_log = global_db[global_db["Username"] == st.session_state.username]

# Filter by current calendar month
current_month = datetime.date.today().replace(day=1)
this_month_log = user_log[user_log["Date"].dt.date >= current_month]

# ==========================================
# --- DATA ENTRY ---
# ==========================================
st.subheader("🧾 Log Transaction")

INCOME_CATS = ["Salary", "Ice Business Revenue", "REIT / Dividends", "Side Hustle", "Other"]
EXPENSE_CATS = [
    "Groceries & Household", 
    "Utilities (Power/Water/Solar)", 
    "Ice Business Operations", 
    "Navara Maintenance & Mods", 
    "Investments (DragonFi/Stocks)", 
    "Singapore Transfer Fund", 
    "Dining Out", 
    "Misc"
]

with st.form("transaction_form", clear_on_submit=True):
    c1, c2 = st.columns([1, 2])
    with c1: 
        t_date = st.date_input("Date", datetime.date.today())
        t_type = st.radio("Type", ["Expense", "Income"], horizontal=True)
    with c2:
        t_cat = st.selectbox("Category", INCOME_CATS if t_type == "Income" else EXPENSE_CATS)
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
# --- FINANCIAL METRICS ---
# ==========================================
total_income = this_month_log[this_month_log["Type"] == "Income"]["Amount"].sum()
total_expense = this_month_log[this_month_log["Type"] == "Expense"]["Amount"].sum()
net_cash = total_income - total_expense

m1, m2, m3 = st.columns(3)
m1.metric("Total Income", f"₱ {total_income:,.2f}")
m2.metric("Total Expenses", f"₱ {total_expense:,.2f}")
m3.metric("Net Cash Flow", f"₱ {net_cash:,.2f}", delta=float(net_cash))

st.write("**Savings Goal Progress**")
progress = min(max(net_cash / st.session_state.savings_goal, 0.0), 1.0) if st.session_state.savings_goal > 0 else 0
st.progress(progress)

# ==========================================
# --- LEDGER ---
# ==========================================
if not this_month_log.empty:
    st.write("### 📅 This Month's Ledger")
    
    # Sort by date descending so the newest items are at the top
    display_log = this_month_log.sort_values(by="Date", ascending=False)
    
    for original_index, row in display_log.iterrows():
        icon = "🟢" if row["Type"] == "Income" else "🔴"
        col_icon, col_desc, col_amt, col_del = st.columns([1, 4, 2, 1])
        
        with col_icon: st.write(icon)
        with col_desc: st.write(f"**{row['Category']}**\n{row['Description']}")
        with col_amt: st.write(f"₱ {row['Amount']:,.2f}")
        with col_del:
            if st.button("❌", key=f"del_{original_index}"):
                global_db = global_db.drop(original_index)
                conn.update(worksheet="Sheet1", data=global_db)
                st.cache_data.clear()
                st.rerun()
