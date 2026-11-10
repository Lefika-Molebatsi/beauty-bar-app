import os
import json
import streamlit as st
import gspread
from datetime import datetime

# -----------------------------------------------------------------------------
# Google Sheets Connection Helper
# -----------------------------------------------------------------------------
@st.cache_resource
def get_gspread_client():
    """Connects to Google Sheets using Streamlit Secrets or local service_account.json"""
    if "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
        gc = gspread.service_account_from_dict(creds_dict)
    elif os.path.exists("service_account.json"):
        gc = gspread.service_account(filename="service_account.json")
    else:
        st.error("Google Sheets service account credentials not found! Please configure secrets.toml or service_account.json.")
        st.stop()
    return gc

def get_db_connection(sheet_name="Beauty Bar"):
    """Opens the target Google Sheet workbook"""
    gc = get_gspread_client()
    return gc.open(sheet_name)

# -----------------------------------------------------------------------------
# Cached Data Access Functions (Prevents API Quota Limits)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=30)
def load_services():
    """Loads active services starting from Row 4 headers (Cached for 30s)"""
    sh = get_db_connection()
    worksheet = sh.worksheet("Services")
    records = worksheet.get_all_records(head=4)
    return [r for r in records if str(r.get("active", "")).upper() == "TRUE"]

@st.cache_data(ttl=30)
def load_staff():
    """Loads staff accounts starting from Row 4 headers (Cached for 30s)"""
    sh = get_db_connection()
    worksheet = sh.worksheet("Staff")
    return worksheet.get_all_records(head=4)

@st.cache_data(ttl=60)
def load_business_info():
    """Loads business info settings starting from Row 4 headers (Cached for 60s)"""
    sh = get_db_connection()
    worksheet = sh.worksheet("Business_Info")
    records = worksheet.get_all_records(head=4)
    return {r["setting_key"]: r["setting_value"] for r in records if "setting_key" in r}

@st.cache_data(ttl=15)
def load_appointments():
    """Loads all appointments starting from Row 4 headers (Cached for 15s)"""
    sh = get_db_connection()
    worksheet = sh.worksheet("Appointments")
    return worksheet.get_all_records(head=4)

@st.cache_data(ttl=15)
def load_expenses():
    """Loads all business expenses starting from Row 4 headers (Cached for 15s)"""
    sh = get_db_connection()
    worksheet = sh.worksheet("Expenses")
    return worksheet.get_all_records(head=4)

# -----------------------------------------------------------------------------
# Data Insertion / Update Functions
# -----------------------------------------------------------------------------
def add_appointment(booking_data):
    """Appends a new appointment row and clears cache"""
    sh = get_db_connection()
    worksheet = sh.worksheet("Appointments")
    
    row_values = [
        booking_data.get("booking_id"),
        booking_data.get("created_at"),
        booking_data.get("customer_name"),
        booking_data.get("customer_phone"),
        booking_data.get("service_ids"),
        booking_data.get("total_price_bwp"),
        booking_data.get("booking_source"),
        booking_data.get("booking_date"),
        booking_data.get("start_time"),
        booking_data.get("assigned_staff_id"),
        booking_data.get("status"),
        booking_data.get("payment_method"),
        booking_data.get("payment_status"),
        booking_data.get("notes")
    ]
    worksheet.append_row(row_values)
    # Clear cache so new bookings show up immediately
    st.cache_data.clear()

def add_expense(expense_data):
    """Appends a new expense record and clears cache"""
    sh = get_db_connection()
    worksheet = sh.worksheet("Expenses")
    row_values = [
        expense_data.get("expense_id"),
        expense_data.get("date"),
        expense_data.get("category"),
        expense_data.get("description"),
        expense_data.get("amount_bwp"),
        expense_data.get("logged_by")
    ]
    worksheet.append_row(row_values)
    # Clear cache so new expenses show up immediately
    st.cache_data.clear()
