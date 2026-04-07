import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import database

st.set_page_config(page_title="Smart Budget", layout="wide")
st.title("💸 Smart Finance Tracker")

db_sheet = database.connect_to_sheets()

col_date, _ = st.columns([1, 3])
with col_date:
    entry_date = st.date_input("📅 Select Date to Log or Edit", datetime.date.today())

# --- THE TIME MACHINE TRIGGER ---
if 'last_date' not in st.session_state or st.session_state.last_date != entry_date:
    st.session_state.last_date = entry_date
    past_data = database.get_snapshot_by_date(db_sheet, entry_date.strftime("%Y-%m-%d"))
    
    if past_data:
        st.session_state.fd = past_data 
        st.toast(f"🕰️ Time Machine: Loaded data from {entry_date.strftime('%b %d, %Y')}")
    else:
        st.session_state.fd = {} 

fd = st.session_state.fd

# -> NEW: We create a unique string based on the date to force widgets to reset!
dk = entry_date.strftime("%Y%m%d")

# 2. Sidebar: The Net Income Engine
with st.sidebar:
    st.header("💰 Income Engine")
    salary_type = st.radio("Pay Frequency:", ["Weekly", "Bi-Monthly", "Once a Month"], 
                           index=["Weekly", "Bi-Monthly", "Once a Month"].index(fd.get("Income Type", "Weekly")),
                           key=f"freq_{dk}")
    
    if salary_type == "Weekly":
        with st.expander("📝 Enter Weekly Pay", expanded=True):
            weekly_pay = st.number_input("Average Weekly Net (PHP)", min_value=0.0, value=float(fd.get("Salary", 0))/4 if fd.get("Salary") else None, step=500.0, key=f"wp_{dk}")
            salary = (weekly_pay or 0) * 4 
    elif salary_type == "Bi-Monthly":
        with st.expander("📝 Enter Bi-Monthly Paychecks", expanded=True):
            pay1 = st.number_input("1st Paycheck", min_value=0.0, value=float(fd.get("Salary", 0))/2 if fd.get("Salary") else None, step=1000.0, key=f"p1_{dk}")
            pay2 = st.number_input("2nd Paycheck", min_value=0.0, value=float(fd.get("Salary", 0))/2 if fd.get("Salary") else None, step=1000.0, key=f"p2_{dk}")
            salary = (pay1 or 0) + (pay2 or 0)
    else:
        with st.expander("📝 Enter Monthly Salary", expanded=True):
            salary_input = st.number_input("Total Monthly Net (PHP)", min_value=0.0, value=float(fd.get("Salary")) if fd.get("Salary") else None, step=1000.0, key=f"si_{dk}")
            salary = salary_input or 0

    side_hustle = st.number_input("Business / Side Hustle", min_value=0.0, value=float(fd.get("Side Hustle")) if fd.get("Side Hustle") else None, step=1000.0, key=f"sh_{dk}")
    total_income = salary + (side_hustle or 0)
    st.success(f"**Total Baseline Income: ₱{total_income:,.2f}**")

# 3. Main Interface: The Expense Categorizer
st.subheader("📋 Expense Allocation")
col1, col2 = st.columns(2)

with col1:
    st.write("**🏡 Core Living**")
    housing = st.number_input("🏠 Rent / Mortgage", value=float(fd.get("Housing")) if fd.get("Housing") else None, step=500.0, key=f"hou_{dk}")
    electricity = st.number_input("⚡ Electricity", value=float(fd.get("Electricity")) if fd.get("Electricity") else None, step=500.0, key=f"ele_{dk}")
    water = st.number_input("💧 Water", value=float(fd.get("Water")) if fd.get("Water") else None, step=100.0, key=f"wat_{dk}")
    internet = st.number_input("🌐 Internet", value=float(fd.get("Internet")) if fd.get("Internet") else None, step=100.0, key=f"int_{dk}")
    groceries = st.number_input("🛒 Groceries", value=float(fd.get("Groceries")) if fd.get("Groceries") else None, step=500.0, key=f"gro_{dk}")
    business_ops = st.number_input("⚙️ Business Ops", value=float(fd.get("Business Ops")) if fd.get("Business Ops") else None, step=500.0, key=f"bus_{dk}")

with col2:
    st.write("**💳 Debt, Subs & Lifestyle**")
    car_payment = st.number_input("🚘 Car Payment", value=float(fd.get("Car Payment")) if fd.get("Car Payment") else None, step=1000.0, key=f"car_{dk}")
    credit_card = st.number_input("💳 Credit Cards", value=float(fd.get("Credit Cards")) if fd.get("Credit Cards") else None, step=500.0, key=f"cre_{dk}")
    subscriptions = st.number_input("📺 Subscriptions", value=float(fd.get("Subscriptions")) if fd.get("Subscriptions") else None, step=100.0, key=f"sub_{dk}")
    investments = st.number_input("📈 Investments", value=float(fd.get("Investments")) if fd.get("Investments") else None, step=500.0, key=f"inv_{dk}")
    transpo = st.number_input("🚗 Gas & Auto", value=float(fd.get("Transportation")) if fd.get("Transportation") else None, step=500.0, key=f"tra_{dk}")
    leisure = st.number_input("🍔 Dining Out", value=float(fd.get("Leisure")) if fd.get("Leisure") else None, step=500.0, key=f"lei_{dk}")

total_expenses = sum([
    housing or 0, electricity or 0, water or 0, internet or 0, groceries or 0, business_ops or 0,
    car_payment or 0, credit_card or 0, subscriptions or 0, investments or 0, transpo or 0, leisure or 0
])
planned_remaining = total_income - total_expenses

st.divider()
st.write("### 🚨 Unplanned / Emergency Expenses")
emergency_spend = st.number_input("Total Emergency Spend this cycle", min_value=0.0, value=float(fd.get("Emergency Spend")) if fd.get("Emergency Spend") else None, step=500.0, key=f"emg_{dk}")
safe_emergency = emergency_spend or 0
actual_remaining = planned_remaining - safe_emergency

# --- THE BIG SAVE (Overwrites past data or saves new data) ---
can_save = total_income > 0
if st.button("💾 Save Snapshot", disabled=not can_save):
    with st.spinner("Saving data..."):
        row_data = [
            entry_date.strftime("%Y-%m-%d"), salary_type, salary, (side_hustle or 0),
            (housing or 0), (electricity or 0), (water or 0), (internet or 0), (groceries or 0), (business_ops or 0),
            (car_payment or 0), (credit_card or 0), (subscriptions or 0), (investments or 0), (transpo or 0), (leisure or 0),
            safe_emergency, total_income, total_expenses, actual_remaining
        ]
        success = database.save_snapshot(db_sheet, row_data)
        if success:
            st.toast("✅ Data Saved Successfully!", icon="🚀")

st.divider()

# 4. Analytics
st.subheader("📊 Cash Flow Analysis")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Income", f"₱{total_income:,.2f}")
m2.metric("Baseline Expenses", f"₱{total_expenses:,.2f}")
m3.metric("Emergency Drain", f"₱{safe_emergency:,.2f}", delta=-float(safe_emergency), delta_color="inverse")
m4.metric("Actual Savings", f"₱{actual_remaining:,.2f}", delta=float(actual_remaining))

chart_col, hist_col = st.columns(2)
with chart_col:
    st.write("**Baseline Expense Breakdown**")
    if total_expenses > 0:
        expense_data = pd.DataFrame({
            "Category": ["Housing", "Electricity", "Water", "Internet", "Groceries", "Business Ops", "Car Payment", "Credit Cards", "Subscriptions", "Investments", "Transportation", "Leisure"],
            "Amount": [housing or 0, electricity or 0, water or 0, internet or 0, groceries or 0, business_ops or 0, car_payment or 0, credit_card or 0, subscriptions or 0, investments or 0, transpo or 0, leisure or 0]
        })
        expense_data = expense_data[expense_data["Amount"] > 0]
        fig = px.pie(expense_data, names="Category", values="Amount", hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig, use_container_width=True)
    else:
        empty_data = pd.DataFrame({"Category": ["Awaiting Data"], "Amount": [1]})
        fig = px.pie(empty_data, names="Category", values="Amount", hole=0.4, color_discrete_sequence=["#e0e0e0"])
        fig.update_traces(textinfo='none', hoverinfo='skip')
        st.plotly_chart(fig, use_container_width=True)

with hist_col:
    st.write("**☁️ Database History**")
    if db_sheet is not None:
        cloud_history = database.load_history(db_sheet)
        if cloud_history is not None:
            display_history = cloud_history[["Date", "Total Income", "Total Expenses", "Actual Savings"]].sort_values(by="Date", ascending=False)
            st.dataframe(display_history, hide_index=True, use_container_width=True)
        else:
            st.info("No data found in cloud.")
            
# 5. Sinking Funds
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
                g_name = st.text_input(f"Goal {i+1} Name", value="", key=f"name_{i}_{dk}")
                g_pct = st.slider(f"{g_name or f'Goal {i+1}'} (%)", 0, 100, 0, key=f"pct_{i}_{dk}")
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
