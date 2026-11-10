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
if "staff_name" not in st.session_state:
    st.session_state.staff_name = None

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
        selected_service_labels = []
        total_price = 0.0

        for cat in categories:
            st.markdown(f"### {cat}")
            cat_services = df_services[df_services["category"] == cat]
            
            for _, s in cat_services.iterrows():
                service_name = str(s['service_name'])
                service_id = str(s['service_id'])
                
                # Clean up price string from sheet (e.g., "P50.00" -> 50.00)
                raw_price = str(s['price_bwp']).replace('P', '').replace('p', '').strip()
                unit_price = float(raw_price) if raw_price else 0.0
                duration = s.get('duration_mins', 0)
                
                # Check if this is a per-unit service (e.g., Art per nail)
                is_per_unit = "per nail" in service_name.lower() or "per piece" in service_name.lower()
                
                col1, col2, col3 = st.columns([3, 1, 1])
                
                if is_per_unit:
                    with col1:
                        is_selected = st.checkbox(f"{service_name} (P{unit_price:.2f} each) - {duration} mins/unit", key=f"chk_{service_id}")
                    with col2:
                        qty = 1
                        if is_selected:
                            qty = st.number_input("Qty", min_value=1, max_value=20, value=1, step=1, key=f"qty_{service_id}", label_visibility="collapsed")
                    with col3:
                        if is_selected:
                            item_total = unit_price * qty
                            st.text(f"P{item_total:.2f}")
                            selected_services.append(s)
                            selected_service_labels.append(f"{service_name} (x{qty})")
                            total_price += item_total
                        else:
                            st.text(f"P{unit_price:.2f}")
                else:
                    with col1:
                        is_selected = st.checkbox(f"{service_name} (P{unit_price:.2f}) - {duration} mins", key=f"chk_{service_id}")
                    with col2:
                        st.text(f"P{unit_price:.2f}")
                    with col3:
                        if is_selected:
                            selected_services.append(s)
                            selected_service_labels.append(service_name)
                            total_price += unit_price

        # Live Running Total
        st.markdown("---")
        st.markdown(f"### 💳 **Live Total: P{total_price:.2f}**")

        st.markdown("---")
        st.subheader("2. Appointment Details")
        
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            cust_name = st.text_input("Full Name *")
            cust_phone = st.text_input("Contact Number *", value="76468676")
        with col_c2:
            booking_date = st.date_input("Appointment Date")
            start_time = st.time_input("Preferred Time", value=datetime.strptime("10:00", "%H:%M").time())

        notes = st.text_area("Special Requests / Add-ons")

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
                booking_id = f"BK-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                created_at = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                formatted_date = booking_date.strftime("%d-%m-%Y")
                
                service_ids_str = ", ".join(selected_service_labels)
                
                # Auto-assign staff using round-robin rotation
                staff_list = db.load_staff()
                staff_df = pd.DataFrame(staff_list) if staff_list else pd.DataFrame()
                
                active_staff = []
                if not staff_df.empty and "staff_id" in staff_df.columns:
                    # Filter active staff excluding Owner
                    active_staff = staff_df[
                        (staff_df["active"].astype(str).str.upper() == "TRUE") & 
                        (staff_df["role"].astype(str).str.lower() != "owner")
                    ]["staff_id"].tolist()

                if active_staff:
                    existing_appts = db.load_appointments()
                    assigned_staff = active_staff[len(existing_appts) % len(active_staff)]
                else:
                    assigned_staff = "BB01"
                
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

                    assigned_staff_name = assigned_staff
                    assigned_staff_phone = "N/A"

                    if not staff_df.empty and "staff_id" in staff_df.columns:
                        staff_match = staff_df[staff_df["staff_id"] == assigned_staff]
                        if not staff_match.empty:
                            assigned_staff_name = staff_match.iloc[0].get("staff_name", assigned_staff)
                            assigned_staff_phone = staff_match.iloc[0].get("phone", "N/A")

                    st.success(f"🎉 Booking Confirmed successfully! Your Booking ID is **{booking_id}**.")
                    st.markdown(f"""
                    - **Date & Time:** {formatted_date} at {start_time.strftime('%H:%M')}
                    - **Assigned Specialist:** **{assigned_staff_name}**
                    - **Specialist Contact:** `{assigned_staff_phone}`
                    """)
                    st.info("Please keep a note of your specialist's contact details in case you need to reschedule or run a few minutes late. We look forward to seeing you at Beauty Bar!")

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
                    st.session_state.user_role = matched_user.get("role", "Staff")
                    st.session_state.staff_name = matched_user.get("staff_name", matched_user["staff_id"])
                    st.rerun()
                elif login_id.lower() == "bbowner":
                    st.session_state.logged_in_user = "BBowner"
                    st.session_state.user_role = "Owner"
                    st.session_state.staff_name = "Owner"
                    st.rerun()
                else:
                    st.error("Invalid Staff ID or Password.")
        else:
            # Logged In View Header
            st.success(f"Welcome back, **{st.session_state.staff_name}** ({st.session_state.logged_in_user}) - Role: **{st.session_state.user_role}**")
            
            if st.button("Log Out"):
                st.session_state.logged_in_user = None
                st.session_state.user_role = None
                st.session_state.staff_name = None
                st.rerun()
                
            st.markdown("---")
            
            # Owner vs Staff Dashboards
            if str(st.session_state.user_role).lower() == "owner" or str(st.session_state.logged_in_user).lower() == "bbowner":
                st.subheader("📊 Owner Administration Dashboard")
                
                appts = db.load_appointments()
                expenses = db.load_expenses()
                
                df_appts = pd.DataFrame(appts) if appts else pd.DataFrame()
                df_expenses = pd.DataFrame(expenses) if expenses else pd.DataFrame()
                
                # Clean and convert total_price_bwp to numeric safely
                if not df_appts.empty and "total_price_bwp" in df_appts.columns:
                    df_appts["total_price_bwp"] = (
                        df_appts["total_price_bwp"]
                        .astype(str)
                        .str.replace("P", "", case=False)
                        .str.replace("p", "", case=False)
                        .str.strip()
                    )
                    df_appts["total_price_bwp"] = pd.to_numeric(df_appts["total_price_bwp"], errors="coerce").fillna(0)
                    total_sales = df_appts["total_price_bwp"].sum()
                else:
                    total_sales = 0.0

                # Clean and convert amount_bwp to numeric safely
                if not df_expenses.empty and "amount_bwp" in df_expenses.columns:
                    df_expenses["amount_bwp"] = (
                        df_expenses["amount_bwp"]
                        .astype(str)
                        .str.replace("P", "", case=False)
                        .str.replace("p", "", case=False)
                        .str.strip()
                    )
                    df_expenses["amount_bwp"] = pd.to_numeric(df_expenses["amount_bwp"], errors="coerce").fillna(0)
                    total_exp = df_expenses["amount_bwp"].sum()
                else:
                    total_exp = 0.0
                
                col_m1, col_m2, col_m3 = st.columns(3)
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
                        exp_id = f"EXP-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
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
                # -----------------------------------------------------------------------------
                # 👤 STAFF PORTAL (Card View for Bookings)
                # -----------------------------------------------------------------------------
                st.subheader(f"👤 Staff Portal — Welcome, {st.session_state.staff_name}")

                all_appts = db.load_appointments()
                df_appts = pd.DataFrame(all_appts) if all_appts else pd.DataFrame()

                if not df_appts.empty and "assigned_staff_id" in df_appts.columns:
                    my_appts = df_appts[
                        df_appts["assigned_staff_id"].astype(str).str.strip().str.lower() == str(st.session_state.logged_in_user).lower()
                    ]
                    
                    if my_appts.empty:
                        st.info("You currently have no bookings assigned to you.")
                    else:
                        st.markdown(f"### 📅 You have **{len(my_appts)}** active booking(s):")
                        st.markdown("---")
                        
                        for _, appt in my_appts.iterrows():
                            with st.container():
                                st.markdown(f"### 🔔 Booking ID: `{appt.get('booking_id', 'N/A')}`")
                                
                                col_a, col_b = st.columns(2)
                                with col_a:
                                    st.markdown(f"**👤 Customer Name:** {appt.get('customer_name', 'N/A')}")
                                    st.markdown(f"**📞 Customer Phone:** `{appt.get('customer_phone', 'N/A')}`")
                                with col_b:
                                    st.markdown(f"**📅 Booking Date:** {appt.get('booking_date', 'N/A')}")
                                    st.markdown(f"**⏰ Start Time:** {appt.get('start_time', 'N/A')}")
                                
                                st.markdown(f"**🛠️ Services Booked:** {appt.get('service_ids', 'N/A')}")
                                
                                raw_p = str(appt.get('total_price_bwp', '0.00')).replace('P', '').replace('p', '').strip()
                                p_val = float(raw_p) if raw_p else 0.0
                                st.markdown(f"**💰 Total Price:** `P{p_val:.2f}`")
                                
                                st.markdown(f"**📝 Notes:** {appt.get('notes', 'None')}")
                                st.markdown("---")
                else:
                    st.info("No appointment records found in the system.")

if __name__ == "__main__":
    main()
