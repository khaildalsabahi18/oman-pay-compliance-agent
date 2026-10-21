import streamlit as st
import pandas as pd

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

# 2. Session State Initialization
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = None
    st.session_state.emp_id = None

# Function to render employee statement
def render_employee_statement(emp_record):
    base_sal = float(emp_record["BaseSalary_OMR"])
    direct_pay = base_sal + float(emp_record["Bonus_OMR"])
    allowances = float(emp_record["HousingAllow_OMR"]) + float(emp_record["TransportAllow_OMR"])
    protections = float(emp_record["HealthCover_OMR"]) + float(emp_record["PensionContrib_OMR"])
    perks = float(emp_record["FlightTickets_OMR"]) + float(emp_record["WellnessPerks_OMR"])

    monthly_total = direct_pay + allowances + protections + perks
    annual_total = monthly_total * 12.0
    multiplier = (monthly_total / base_sal) if base_sal > 0 else 0
    base_share = (base_sal / monthly_total) * 100 if monthly_total > 0 else 0

    # Metric Cards
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Base Monthly Salary", f"OMR {base_sal:.3f}")
    c2.metric("Total Monthly Value", f"OMR {monthly_total:.3f}")
    c3.metric("Annual Total Package", f"OMR {annual_total:,.3f}")
    c4.metric("Package Multiplier", f"{multiplier:.2f}x Base")

    st.write("")
    col_left, col_right = st.columns([1.1, 0.9])

    with col_left:
        st.markdown("#### 📊 Monthly Compensation Breakdown")
        breakdown_data = pd.DataFrame({
            "Component Category": [
                "1. Direct Base & Performance Bonus",
                "2. Cash Allowances (Housing + Transport)",
                "3. Social Protection & Healthcare",
                "4. Indirect Perks (Tickets + Wellness)"
            ],
            "Amount (OMR)": [direct_pay, allowances, protections, perks],
            "Share of Total (%)": [
                f"{(direct_pay / monthly_total) * 100:.1f}%",
                f"{(allowances / monthly_total) * 100:.1f}%",
                f"{(protections / monthly_total) * 100:.1f}%",
                f"{(perks / monthly_total) * 100:.1f}%"
            ]
        })
        st.dataframe(
            breakdown_data, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Component Category": st.column_config.TextColumn("Reward Category", width="large"),
                "Amount (OMR)": st.column_config.NumberColumn("Amount (OMR)", format="OMR %.3f"),
                "Share of Total (%)": st.column_config.TextColumn("Share (%)", width="medium"),
            }
        )
        st.bar_chart(breakdown_data.set_index("Component Category")["Amount (OMR)"])

    with col_right:
        st.markdown("#### 📜 Formal Total Rewards Statement")
        statement_text = f"""
        **Employee Name:** {emp_record['Name']} ({emp_record['EmpID']})  
        **Grade & Department:** Grade {emp_record['Grade']} | {emp_record['Department']} Department  

        ---
        ### Detailed Component Breakdown
        * **Monthly Base Salary:** OMR {base_sal:.3f}
        * **Performance Incentive / Bonus (Monthly Avg):** OMR {float(emp_record['Bonus_OMR']):.3f}
        * **Company Housing Allowance:** OMR {float(emp_record['HousingAllow_OMR']):.3f}
        * **Transportation Allowance:** OMR {float(emp_record['TransportAllow_OMR']):.3f}
        * **Sponsored Health Coverage:** OMR {float(emp_record['HealthCover_OMR']):.3f}
        * **Social Protection / Pension Contribution:** OMR {float(emp_record['PensionContrib_OMR']):.3f}
        * **Annual Flight Subsidies (Monthly Equiv.):** OMR {float(emp_record['FlightTickets_OMR']):.3f}
        * **Wellness & Other Organizational Perks:** OMR {float(emp_record['WellnessPerks_OMR']):.3f}
        ---
        💡 **Executive Statement:**  
        Your direct base salary accounts for only **{base_share:.1f}%** of the total investment made by the organization in your overall career and welfare. The comprehensive financial value of your package is **OMR {monthly_total:.3f} per month**, totaling **OMR {annual_total:,.3f} annually**.
        """
        st.info(statement_text)

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
    # Sidebar Session Info
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

        # Organization Aggregates
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

        # Individual Employee Audit Feature
        st.markdown("### 🔍 Individual Employee Audit")
        emp_options = df_calc.apply(
            lambda r: f"{r.get('EmpID', 'N/A')} - {r.get('Name', 'Unknown')} ({r.get('Department', 'General')})", 
            axis=1
        ).tolist()
        
        selected_label = st.selectbox("Select Employee to audit rewards statement:", emp_options)
        selected_id = selected_label.split(" - ")[0]
        selected_emp = df_calc[df_calc["EmpID"] == selected_id].iloc[0]
        
        with st.expander("📄 Click to View Employee's Detailed Rewards Statement", expanded=True):
            render_employee_statement(selected_emp)

        st.divider()

        # Organization Workforce Table
        st.markdown("### 📋 Workforce Summary Registry")
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

        st.markdown("### 🏢 Monthly Expenditure by Department")
        dept_costs = df_calc.groupby("Department")["TotalMonthly"].sum().reset_index()
        st.bar_chart(dept_costs.set_index("Department"))
