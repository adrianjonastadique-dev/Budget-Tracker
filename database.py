import streamlit as st
import gspread
import pandas as pd
import os

# We explicitly define all 20 columns needed to reconstruct the past!
COLUMNS = [
    "Date", "Income Type", "Salary", "Side Hustle",
    "Housing", "Electricity", "Water", "Internet", "Groceries", "Business Ops",
    "Car Payment", "Credit Cards", "Subscriptions", "Investments", "Transportation", "Leisure",
    "Emergency Spend", "Total Income", "Total Expenses", "Actual Savings"
]

@st.cache_resource
def connect_to_sheets():
    try:
        gc = gspread.service_account(filename='secrets.json')
        sheet = gc.open("Smart Budget Database").sheet1
        
        # Auto-create headers if the sheet is completely empty
        if not sheet.get_all_values():
            sheet.append_row(COLUMNS)
            
        return sheet
    except FileNotFoundError:
        return None
    except Exception as e:
        st.error("🚨 Connection failed.")
        return None

def save_local_fallback(row_data):
    new_entry = pd.DataFrame([row_data], columns=COLUMNS)
    try:
        if not os.path.isfile("offline_budget_history.csv"):
            new_entry.to_csv("offline_budget_history.csv", index=False)
        else:
            # Overwrite if date exists, otherwise append
            df = pd.read_csv("offline_budget_history.csv")
            if row_data[0] in df['Date'].values:
                df.loc[df['Date'] == row_data[0]] = row_data
                df.to_csv("offline_budget_history.csv", index=False)
            else:
                new_entry.to_csv("offline_budget_history.csv", mode='a', header=False, index=False)
        return True
    except Exception as e:
        return False

def save_snapshot(db_sheet, row_data):
    if db_sheet is None:
        return save_local_fallback(row_data)
    try:
        # Check if date already exists to overwrite it, otherwise append
        records = db_sheet.get_all_records()
        if records:
            df = pd.DataFrame(records)
            if row_data[0] in df['Date'].values:
                row_index = df.index[df['Date'] == row_data[0]].tolist()[0] + 2 # +2 because of header and 0-index
                # Update existing row
                for col_idx, val in enumerate(row_data):
                    db_sheet.update_cell(row_index, col_idx + 1, val)
                return True
        
        db_sheet.append_row(row_data)
        return True
    except Exception as e:
        return save_local_fallback(row_data)

def load_history(db_sheet):
    if db_sheet is None:
        return None
    try:
        records = db_sheet.get_all_records()
        return pd.DataFrame(records) if records else None
    except Exception:
        return None

# --- THE TIME MACHINE CORE ---
def get_snapshot_by_date(db_sheet, target_date):
    """Searches the database for a specific date and returns the data."""
    try:
        if db_sheet is not None:
            records = db_sheet.get_all_records()
            if records:
                df = pd.DataFrame(records)
                match = df[df['Date'] == target_date]
                if not match.empty:
                    return match.iloc[0].to_dict()
        
        if os.path.isfile("offline_budget_history.csv"):
            df = pd.read_csv("offline_budget_history.csv")
            match = df[df['Date'] == target_date]
            if not match.empty:
                return match.iloc[0].to_dict()
    except Exception:
        pass
    return None
