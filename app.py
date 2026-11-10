import streamlit as st
import pandas as pd
from datetime import datetime
import db

# Page Configuration
st.set_page_config(
    page_title="Beauty Bar Management System",
    page_icon="💅",
    layout="wide"
)

# Initialize Session State for Authentication
if "logged_in_user" not in st.session_state:
    st.session_state.logged_in_user = None
if "user_role" not in st.session_state:
    st.session_state.user_role = None

def main():
    st.sidebar.title("💅 Beauty Bar Portal")
    
    # Load Business Info & Services
    try:
        biz_info = db.load_business_info()
        services = db.load_services()
    except Exception as e:
        st.error(f"Error connecting to Google Sheets. Please check your credentials and sheet sharing permissions.\n\nDetails: {e}")
        return

    # Sidebar Navigation Mode
    nav_mode = st.sidebar.radio("Navigation", ["🌐 Customer Booking Portal", "🔐 Staff & Owner Login"])

    # -----------------------------------------------------------------------------
    # MODE 1: CUSTOMER BOOKING PORTAL
    # -----------------------------------------------------------------------------
    if nav_mode == "🌐 Customer Booking Portal":
        st.title(f"✨ {biz_info.get('business_name', 'Beauty Bar')} - Online Booking")
        st.markdown(f"📍 **Address:** {biz_info.get('address', 'Plot 3421 Matima Crescent, Extension 12')}")
        st.markdown(f"🕒 **Hours:** {biz_info.get('operating_days', 'Monday to Sunday')} | {biz_info.get('operating_hours', '09:00 to 18:00')}")
        st.markdown("---")

        st.subheader("1. Select Your Services")
        if not services:
            st.warning("No services currently available.")
            return

        # Organize services by category
        df_services = pd.DataFrame(services)
        categories = df_services["category"].unique()
        
        selected_services = []
        total_price = 0

        for cat in categories:
    st.markdown(f"### {cat}")
    cat_services = df_services[df_services["category"] == cat]
    
    for _, s in cat_services.iterrows():
        # Clean up price string from sheet (e.g., "P50.00" -> "50.00" or handle floats)
        raw_price = str(s['price_bwp']).replace('P', '').replace('p', '').strip()
        price_val = float(raw_price) if raw_price else 0.0
        
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            is_selected = st.checkbox(f"{s['service_name']} (P{price_val:.2f}) - {s['duration_mins']} mins", key=s['service_id'])
        with col2:
            st.text(f"P{price_val:.2f}")
        with col3:
            if is_selected:
                selected_services.append(s)
                total_price += price_val

        st.markdown("---")
        st.subheader("2. Appointment Details")
        
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            cust_name = st.text_input("Full Name *")
            cust_phone = st.text_input("Contact Number *", value="76468676")
        with col_c2:
            booking_date = st.date_input("Appointment Date")
            start_time = st.time_input("Preferred Time", value=datetime.strptime("10:00", "%H:%M").time())

        notes = st.text_area("Special Requests / Add-ons (e.g., Art per nail x 2)")

        # Display Payment Instructions
        st.markdown("---")
        st.subheader("3. Payment Information")
        st.info(f"""
        **Accepted Local Payment Methods (Send to Number: `{biz_info.get('contact_phone', '76468676')}`):**
        * **Orange Money:** `{biz_info.get('orange_money_number', '76468676')}`
        * **Pay2Cell:** `{biz_info.get('pay2cell_number', '76468676')}`
        * **E-Wallet:** `{biz_info.get('ewallet_number', '76468676')}`
        """)

        payment_method = st.selectbox("Select Payment Method", ["Orange Money", "Pay2Cell", "Ewallet", "Cash at Salon"])

        if st.button("Confirm and Book Appointment", type="primary"):
            if not cust_name or not cust_phone:
                st.error("Please enter your full name and contact number.")
            elif not selected_services:
                st.error("Please select at least one service.")
            else:
                # Generate booking ID and format date as DD-MM-YYYY
                booking_id = f"BK-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                created_at = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                formatted_date = booking_date.strftime("%d-%m-%Y")
                
                service_ids_str = ", ".join([str(s['service_id']) for s in selected_services])
                
                # Assign default staff or keep unassigned
                staff_list = db.load_staff()
                assigned_staff = "BB01" # Default first staff member for auto-confirmation
                
                booking_payload = {
                    "booking_id": booking_id,
                    "created_at": created_at,
                    "customer_name": cust_name,
                    "customer_phone": cust_phone,
                    "service_ids": service_ids_str,
                    "total_price_bwp": total_price,
                    "booking_source": "Online",
                    "booking_date": formatted_date,
                    "start_time": start_time.strftime("%H:%M"),
                    "assigned_staff_id": assigned_staff,
                    "status": "Confirmed",
                    "payment_method": payment_method,
                    "payment_status": "Paid" if payment_method != "Cash at Salon" else "Pending",
                    "notes": notes
                }
                
                try:
                    db.add_appointment(booking_payload)
                    st.success(f"🎉 Booking Confirmed successfully! Your Booking ID is **{booking_id}**. We look forward to seeing you at Beauty Bar!")
                except Exception as ex:
                    st.error(f"Failed to save booking to Google Sheets: {ex}")

    # -----------------------------------------------------------------------------
    # MODE 2: STAFF & OWNER LOGIN PORTAL
    # -----------------------------------------------------------------------------
    elif nav_mode == "🔐 Staff & Owner Login":
        st.title("🔐 Employee & Owner Portal")
        
        if not st.session_state.logged_in_user:
            st.markdown("Enter your credentials (e.g., `BB01` to `BB07`, or `BBowner`).")
            login_id = st.text_input("Staff ID / Username").strip()
            pin_input = st.text_input("PIN / Password", type="password")
            
            if st.button("Login"):
                staff_records = db.load_staff()
                matched_user = next((s for s in staff_records if str(s.get("staff_id")).lower() == login_id.lower()), None)
                
                if matched_user:
                    st.session_state.logged_in_user = matched_user["staff_id"]
                    st.session_state.user_role = matched_user["role"]
                    st.session_state.staff_name = matched_user["staff_name"]
                    st.rerun()
                else:
                    st.error("Invalid Staff ID or Password.")
        else:
            # Logged In View
            st.success(f"Welcome back, **{st.session_state.staff_name}** ({st.session_state.logged_in_user}) - Role: **{st.session_state.user_role}**")
            
            if st.button("Log Out"):
                st.session_state.logged_in_user = None
                st.session_state.user_role = None
                st.rerun()
                
            st.markdown("---")
            
            # Owner vs Staff Dashboards
            if st.session_state.user_role == "Owner":
                st.subheader("📊 Owner Administration Dashboard")
                
                appts = db.load_appointments()
                expenses = db.load_expenses()
                
                df_appts = pd.DataFrame(appts) if appts else pd.DataFrame()
                df_expenses = pd.DataFrame(expenses) if expenses else pd.DataFrame()
                
                col_m1, col_m2, col_m3 = st.columns(3)
                total_sales = df_appts["total_price_bwp"].sum() if not df_appts.empty and "total_price_bwp" in df_appts else 0
                total_exp = df_expenses["amount_bwp"].sum() if not df_expenses.empty and "amount_bwp" in df_expenses else 0
                
                col_m1.metric("Total Gross Sales", f"P{total_sales:,.2f}")
                col_m2.metric("Total Expenses", f"P{total_exp:,.2f}")
                col_m3.metric("Net Profit", f"P{total_sales - total_exp:,.2f}")
                
                st.markdown("### All Salon Appointments")
                if not df_appts.empty:
                    st.dataframe(df_appts, use_container_width=True)
                else:
                    st.info("No appointments recorded yet.")
                    
                st.markdown("### Log New Business Expense")
                with st.form("expense_form"):
                    exp_date = st.date_input("Expense Date").strftime("%d-%m-%Y")
                    exp_cat = st.selectbox("Category", ["Supplies", "Utilities", "Rent", "Other"])
                    exp_desc = st.text_input("Description")
                    exp_amt = st.number_input("Amount (BWP)", min_value=0.0, step=10.0)
                    submit_exp = st.form_submit_button("Record Expense")
                    
                    if submit_exp:
                        exp_id = f"EXP-{datetime.now().strftime('%Y%m-%H%M%S')}"
                        exp_payload = {
                            "expense_id": exp_id,
                            "date": exp_date,
                            "category": exp_cat,
                            "description": exp_desc,
                            "amount_bwp": exp_amt,
                            "logged_by": st.session_state.logged_in_user
                        }
                        db.add_expense(exp_payload)
                        st.success("Expense recorded successfully!")
                        st.rerun()
            
            else:
                st.subheader(f"📅 Schedule for Staff ID: {st.session_state.logged_in_user}")
                appts = db.load_appointments()
                if appts:
                    df_appts = pd.DataFrame(appts)
                    # Filter appointments assigned to this staff member
                    my_appts = df_appts[df_appts["assigned_staff_id"] == st.session_state.logged_in_user]
                    if not my_appts.empty:
                        st.dataframe(my_appts, use_container_width=True)
                    else:
                        st.info("No appointments currently assigned to your account.")
                else:
                    st.info("No appointments found in the database.")

if __name__ == "__main__":
    main()
