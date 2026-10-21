import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Total Rewards Statement Agent", layout="wide")

# 1. Load Dataset
@st.cache_data
def load_data():
    try:
        return pd.read_csv("dataset.csv")
    except Exception:
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.error("⚠️ 'dataset.csv' was not found. Please ensure it is uploaded in the repository.")
    st.stop()

# Helper function to generate 12-month dynamic payroll history per employee
def generate_annual_payroll_history(emp_record, custom_ot_day=0.0, custom_ot_night=0.0, custom_bonus=None):
    months = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    base_sal = float(emp_record["BaseSalary_OMR"])
    hourly_rate = base_sal / 240.0
    
    np.random.seed(int("".join([str(ord(c)) for c in str(emp_record["EmpID"])])) % 100000)
    
    records = []
    for idx, m in enumerate(months):
        # Allow custom override for the latest month (December) if provided by HR
        if idx == 11 and (custom_ot_day > 0 or custom_ot_night > 0 or custom_bonus is not None):
            day_ot_hrs = float(custom_ot_day)
            night_ot_hrs = float(custom_ot_night)
            monthly_bonus = float(custom_bonus) if custom_bonus is not None else float(emp_record["Bonus_OMR"])
        else:
            day_ot_hrs = float(np.random.choice([0, 5, 8, 12, 16], p=[0.2, 0.3, 0.25, 0.15, 0.1]))
            night_ot_hrs = float(np.random.choice([0, 4, 8], p=[0.6, 0.3, 0.1]))
            base_bonus = float(emp_record["Bonus_OMR"])
            if m in ["June", "December"]:
                monthly_bonus = base_bonus * 1.5
            elif m in ["July", "August"]:
                monthly_bonus = base_bonus * 0.5
            else:
                monthly_bonus = base_bonus
            
        ot_pay = (day_ot_hrs * hourly_rate * 1.25) + (night_ot_hrs * hourly_rate * 1.50)
        direct_cash = base_sal + ot_pay + monthly_bonus
        
        allowances = float(emp_record["HousingAllow_OMR"]) + float(emp_record["TransportAllow_OMR"])
        protections = float(emp_record["HealthCover_OMR"]) + float(emp_record["PensionContrib_OMR"])
        perks = float(emp_record["FlightTickets_OMR"]) + float(emp_record["WellnessPerks_OMR"])
        
        total_month_rewards = direct_cash + allowances + protections + perks
        
        records.append({
            "Month": m,
            "Base_Salary": base_sal,
            "Day_OT_Hrs": day_ot_hrs,
            "Night_OT_Hrs": night_ot_hrs,
            "OT_Pay": ot_pay,
            "Incentive_Bonus": monthly_bonus,
            "Cash_Allowances": allowances,
            "Social_Protections": protections,
            "Perks_Subsidies": perks,
            "Net_Cash_Pay": direct_cash + allowances,
            "Total_Rewards_Value": total_month_rewards
        })
    return pd.DataFrame(records)

# 2. Session State Initialization
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = None
    st.session_state.emp_id = None

# Function to render employee statement
def render_employee_statement(emp_record, custom_ot_day=0.0, custom_ot_night=0.0, custom_bonus=None):
    monthly_df = generate_annual_payroll_history(emp_record, custom_ot_day, custom_ot_night, custom_bonus)
    
    annual_base = monthly_df["Base_Salary"].sum()
    annual_ot = monthly_df["OT_Pay"].sum()
    annual_bonus = monthly_df["Incentive_Bonus"].sum()
    annual_total_rewards = monthly_df["Total_Rewards_Value"].sum()
    
    multiplier = (annual_total_rewards / annual_base) if annual_base > 0 else 0
    base_share = (annual_base / annual_total_rewards) * 100 if annual_total_rewards > 0 else 0

    # Macro Metric Cards
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Annual Base Salary", f"OMR {annual_base:,.2f}")
    c2.metric("Annual Overtime Earned", f"OMR {annual_ot:,.2f}", delta=f"{monthly_df['Day_OT_Hrs'].sum() + monthly_df['Night_OT_Hrs'].sum():.0f} total hrs")
    c3.metric("Annual Total Rewards Value", f"OMR {annual_total_rewards:,.2f}")
    c4.metric("Annual Multiplier", f"{multiplier:.2f}x Base")

    st.divider()

    # Section 1: Detailed 12-Month Payroll Breakdown Table
    st.markdown("### 📅 12-Month Detailed Payroll & Rewards History")
    st.caption("Month-by-month record showing base wage, overtime, bonus variations, and indirect organizational investments.")
    
    st.dataframe(
        monthly_df, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "Month": st.column_config.TextColumn("Month", width="small"),
            "Base_Salary": st.column_config.NumberColumn("Base Pay", format="OMR %.2f"),
            "Day_OT_Hrs": st.column_config.NumberColumn("Day OT (h)", format="%.1f"),
            "Night_OT_Hrs": st.column_config.NumberColumn("Night OT (h)", format="%.1f"),
            "OT_Pay": st.column_config.NumberColumn("OT Amount", format="OMR %.2f"),
            "Incentive_Bonus": st.column_config.NumberColumn("Bonus/Incentive", format="OMR %.2f"),
            "Cash_Allowances": st.column_config.NumberColumn("Allowances", format="OMR %.2f"),
            "Social_Protections": st.column_config.NumberColumn("Health & Pension", format="OMR %.2f"),
            "Perks_Subsidies": st.column_config.NumberColumn("Perks/Travel", format="OMR %.2f"),
            "Net_Cash_Pay": st.column_config.NumberColumn("Cash Payout", format="OMR %.2f"),
            "Total_Rewards_Value": st.column_config.NumberColumn("Total Rewards", format="OMR %.2f"),
        }
    )

    st.write("")

    # Section 2: Visual Trends Over the 12 Months
    col_chart, col_summary = st.columns([1.1, 0.9])
    
    with col_chart:
        st.markdown("#### 📈 Monthly Compensation Trends (Fluctuations)")
        trend_chart_data = monthly_df.set_index("Month")[["Net_Cash_Pay", "Total_Rewards_Value"]]
        st.line_chart(trend_chart_data)

    with col_summary:
        st.markdown("#### 📜 Annual Total Rewards Summary Statement")
        statement_text = f"""
        **Employee Name:** {emp_record['Name']} ({emp_record['EmpID']})  
        **Grade & Department:** Grade {emp_record['Grade']} | {emp_record['Department']} Department  

        ---
        ### 12-Month Cumulative Totals
        * **Total Base Wage Paid:** OMR {annual_base:,.2f}
        * **Total Overtime Payouts:** OMR {annual_ot:,.2f}
        * **Total Performance Bonuses:** OMR {annual_bonus:,.2f}
        * **Total Housing & Transport Allowances:** OMR {monthly_df['Cash_Allowances'].sum():,.2f}
        * **Total Healthcare & Pension Coverage:** OMR {monthly_df['Social_Protections'].sum():,.2f}
        * **Total Perks & Flight Subsidies:** OMR {monthly_df['Perks_Subsidies'].sum():,.2f}
        ---
        **Grand Total Annual Rewards Investment:** **OMR {annual_total_rewards:,.2f}**  
        
        💡 **Executive Message:**  
        Your direct basic salary accounts for only **{base_share:.1f}%** of the total investment made by the organization throughout the entire year.
        """
        st.info(statement_text)

        st.download_button(
            label="📥 Download Annual Statement (.txt)",
            data=statement_text,
            file_name=f"Annual_Total_Rewards_{emp_record['EmpID']}.txt",
            mime="text/plain"
        )

# Header
st.title("💼 Total Rewards Statement Agent")
st.caption("MNGT3557 Compensation & Performance Management | Section 1 Agent (Topic 8)")
st.divider()

# ==============================================================================
# LOGIN SCREEN
# ==============================================================================
if not st.session_state.logged_in:
    st.subheader("🔐 Secure Portal Authentication")
    
    col_a, col_b = st.columns([1, 1])
    
    with col_a:
        portal_choice = st.radio(
            "Select Portal:",
            ["👤 Employee Portal", "🏢 HR / Management Portal"]
        )

    with col_b:
        with st.form("login_form"):
            user_id = st.text_input("Enter User ID:", placeholder="e.g., EMP201 for Employee or hr for HR")
            password = st.text_input("Enter Password:", type="password", placeholder="Default: 1234")
            submitted = st.form_submit_button("Sign In", type="primary")

            if submitted:
                cleaned_id = user_id.strip()
                
                # Employee Authentication
                if "Employee" in portal_choice:
                    valid_ids = df["EmpID"].astype(str).str.upper().tolist()
                    if cleaned_id.upper() in valid_ids and password == "1234":
                        st.session_state.logged_in = True
                        st.session_state.user_role = "Employee"
                        st.session_state.emp_id = cleaned_id.upper()
                        st.rerun()
                    else:
                        st.error("❌ Invalid Employee ID or Password! (Hint: Password is 1234)")
                
                # HR Authentication
                elif "HR" in portal_choice:
                    if cleaned_id.lower() == "hr" and password == "1234":
                        st.session_state.logged_in = True
                        st.session_state.user_role = "HR"
                        st.rerun()
                    else:
                        st.error("❌ Invalid HR credentials! (Use ID: hr and Password: 1234)")

# ==============================================================================
# AUTHENTICATED PORTALS
# ==============================================================================
else:
    st.sidebar.write(f"Logged in as: **{st.session_state.user_role}**")
    if st.sidebar.button("Sign Out"):
        st.session_state.logged_in = False
        st.session_state.user_role = None
        st.session_state.emp_id = None
        st.rerun()

    # 1. Employee Authenticated View
    if st.session_state.user_role == "Employee":
        emp_record = df[df["EmpID"].astype(str).str.upper() == st.session_state.emp_id].iloc[0]
        st.subheader(f"👤 Welcome, {emp_record['Name']} ({emp_record['EmpID']})")
        render_employee_statement(emp_record)

    # 2. HR Authenticated View
    elif st.session_state.user_role == "HR":
        st.subheader("🏢 HR Compensation & Benefits Analytics Center")

        df_calc = df.copy()
        df_calc["DirectPay"] = df_calc["BaseSalary_OMR"] + df_calc["Bonus_OMR"]
        df_calc["Allowances"] = df_calc["HousingAllow_OMR"] + df_calc["TransportAllow_OMR"]
        df_calc["Protections"] = df_calc["HealthCover_OMR"] + df_calc["PensionContrib_OMR"]
        df_calc["Perks"] = df_calc["FlightTickets_OMR"] + df_calc["WellnessPerks_OMR"]
        df_calc["TotalMonthly"] = df_calc["DirectPay"] + df_calc["Allowances"] + df_calc["Protections"] + df_calc["Perks"]
        df_calc["TotalAnnual"] = df_calc["TotalMonthly"] * 12.0

        h1, h2, h3, h4 = st.columns(4)
        h1.metric("Total Headcount", len(df_calc))
        h2.metric("Monthly Base Payroll", f"OMR {df_calc['BaseSalary_OMR'].sum():,.2f}")
        h3.metric("Total Monthly Rewards", f"OMR {df_calc['TotalMonthly'].sum():,.2f}")
        h4.metric("Annual Rewards Budget", f"OMR {df_calc['TotalAnnual'].sum():,.2f}")

        st.divider()

        # Individual Employee Audit & Variable Inputs Section
        st.markdown("### 🔍 Individual Employee Audit & Variable Pay Adjustment")
        st.caption("Select an employee, then adjust current variable parameters (Overtime, Bonus) to simulate changes in real-time.")
        
        emp_options = df_calc.apply(
            lambda r: f"{r.get('EmpID', 'N/A')} - {r.get('Name', 'Unknown')} ({r.get('Department', 'General')})", 
            axis=1
        ).tolist()
        
        selected_label = st.selectbox("Select Employee to audit & adjust:", emp_options)
        selected_id = selected_label.split(" - ")[0]
        selected_emp = df_calc[df_calc["EmpID"] == selected_id].iloc[0]

        # HR Input Controls for Overtime & Bonuses
        with st.expander("⚙️ Adjust Variable Pay & Overtime Inputs for this Employee", expanded=True):
            col_in1, col_in2, col_in3 = st.columns(3)
            with col_in1:
                hr_day_ot = st.number_input(
                    "Day Overtime Hours (1.25x)", 
                    min_value=0.0, max_value=80.0, value=10.0, step=1.0, 
                    key=f"hr_day_ot_{selected_id}"
                )
            with col_in2:
                hr_night_ot = st.number_input(
                    "Night Overtime Hours (1.50x)", 
                    min_value=0.0, max_value=80.0, value=4.0, step=1.0, 
                    key=f"hr_night_ot_{selected_id}"
                )
            with col_in3:
                hr_bonus = st.number_input(
                    "Performance Bonus / Incentive (OMR)", 
                    min_value=0.0, max_value=3000.0, value=float(selected_emp["Bonus_OMR"]), step=25.0, 
                    key=f"hr_bonus_{selected_id}"
                )

        # Render Statement with HR's Variable Inputs
        render_employee_statement(
            selected_emp, 
            custom_ot_day=hr_day_ot, 
            custom_ot_night=hr_night_ot, 
            custom_bonus=hr_bonus
        )

        st.divider()

        # Organization Workforce Table
        st.markdown("### 📋 Baseline Workforce Summary Registry")
        display_cols = ["EmpID", "Name", "Department", "Grade", "BaseSalary_OMR", "TotalMonthly", "TotalAnnual"]
        st.dataframe(
            df_calc[display_cols], 
            use_container_width=True,
            column_config={
                "EmpID": st.column_config.TextColumn("ID", width="small"),
                "Name": st.column_config.TextColumn("Full Name", width="medium"),
                "Department": st.column_config.TextColumn("Department", width="medium"),
                "Grade": st.column_config.TextColumn("Grade", width="small"),
                "BaseSalary_OMR": st.column_config.NumberColumn("Base Salary", format="OMR %.3f"),
                "TotalMonthly": st.column_config.NumberColumn("Total Monthly", format="OMR %.3f"),
                "TotalAnnual": st.column_config.NumberColumn("Total Annual", format="OMR %.3f"),
            }
        )

        st.markdown("### 🏢 Baseline Monthly Expenditure by Department")
        dept_costs = df_calc.groupby("Department")["TotalMonthly"].sum().reset_index()
        st.bar_chart(dept_costs.set_index("Department"))
