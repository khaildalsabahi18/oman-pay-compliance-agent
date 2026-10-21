import streamlit as st
import pandas as pd

st.set_page_config(page_title="Total Rewards Statement Agent", layout="wide")

# Load dataset
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

# Header
st.title("💼 Total Rewards Statement Agent")
st.caption("MNGT3557 Compensation & Performance Management | Section 1 Agent (Topic 8)")

st.divider()

# Sidebar: Role Selection
st.sidebar.header("🔐 User Portal Access")
user_role = st.sidebar.radio(
    "Select your viewpoint:",
    ["👤 Employee View", "🏢 HR / Management View"]
)

# ==============================================================================
# 1. EMPLOYEE VIEW
# ==============================================================================
if user_role == "👤 Employee View":
    st.subheader("👤 Personal Total Rewards Statement")
    st.write("Welcome! This interactive statement demonstrates the complete, holistic value of your total rewards package, including direct pay, cash allowances, social protections, and indirect benefits sponsored by the company.")

    # Dropdown to select employee
    emp_options = df.apply(
        lambda r: f"{r.get('EmpID', 'N/A')} - {r.get('Name', 'Unknown')} ({r.get('Department', 'General')})", 
        axis=1
    ).tolist()
    
    selected_label = st.selectbox("Select Employee Profile:", emp_options)
    selected_id = selected_label.split(" - ")[0]
    emp = df[df["EmpID"] == selected_id].iloc[0]

    # Calculations
    direct_pay = float(emp["BaseSalary_OMR"]) + float(emp["Bonus_OMR"])
    allowances = float(emp["HousingAllow_OMR"]) + float(emp["TransportAllow_OMR"])
    protections = float(emp["HealthCover_OMR"]) + float(emp["PensionContrib_OMR"])
    perks = float(emp["FlightTickets_OMR"]) + float(emp["WellnessPerks_OMR"])

    monthly_total = direct_pay + allowances + protections + perks
    annual_total = monthly_total * 12.0
    base_salary = float(emp["BaseSalary_OMR"])
    reward_multiplier = (monthly_total / base_salary) if base_salary > 0 else 0

    # Summary KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Base Monthly Salary", f"OMR {base_salary:.3f}")
    col2.metric("Total Monthly Value", f"OMR {monthly_total:.3f}")
    col3.metric("Annual Total Package", f"OMR {annual_total:,.3f}")
    col4.metric("Rewards Multiplier", f"{reward_multiplier:.2f}x Base Pay")

    st.write("")

    # Detailed Columns
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
        
        # Display table with expanded text columns to prevent truncated text
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
        base_percentage = (base_salary / monthly_total) * 100 if monthly_total > 0 else 0
        statement_text = f"""
        **Employee Name:** {emp['Name']} ({emp['EmpID']})  
        **Grade & Department:** Grade {emp['Grade']} | {emp['Department']} Department  

        ---
        ### Package Breakdown
        * **Monthly Base Salary:** OMR {base_salary:.3f}
        * **Performance Incentive / Bonus (Monthly Avg):** OMR {float(emp['Bonus_OMR']):.3f}
        * **Company Housing Allowance:** OMR {float(emp['HousingAllow_OMR']):.3f}
        * **Transportation Allowance:** OMR {float(emp['TransportAllow_OMR']):.3f}
        * **Sponsored Health Coverage:** OMR {float(emp['HealthCover_OMR']):.3f}
        * **Social Protection / Pension Contribution:** OMR {float(emp['PensionContrib_OMR']):.3f}
        * **Annual Flight Subsidies (Monthly Equiv.):** OMR {float(emp['FlightTickets_OMR']):.3f}
        * **Wellness & Other Organizational Perks:** OMR {float(emp['WellnessPerks_OMR']):.3f}
        ---
        💡 **Executive Message:**  
        Your direct basic wage represents only **{base_percentage:.1f}%** of the total investment the company makes toward your career and financial security. The true realized value of your compensation is **OMR {monthly_total:.3f} per month**, amounting to **OMR {annual_total:,.3f} annually**.
        """
        st.info(statement_text)

# ==============================================================================
# 2. HR / MANAGEMENT VIEW
# ==============================================================================
else:
    st.subheader("🏢 HR Compensation & Benefits Analytics Center")
    st.write("This dashboard provides compensation specialists and executive management with workforce-wide analytics, department cost allocations, and individual package visibility.")

    # Option to upload dataset
    uploaded_file = st.sidebar.file_uploader("Upload Updated Dataset (CSV)", type=["csv"])
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        st.sidebar.success("New dataset loaded successfully!")

    # Calculate workforce aggregates
    df_calc = df.copy()
    df_calc["DirectPay"] = df_calc["BaseSalary_OMR"] + df_calc["Bonus_OMR"]
    df_calc["Allowances"] = df_calc["HousingAllow_OMR"] + df_calc["TransportAllow_OMR"]
    df_calc["Protections"] = df_calc["HealthCover_OMR"] + df_calc["PensionContrib_OMR"]
    df_calc["Perks"] = df_calc["FlightTickets_OMR"] + df_calc["WellnessPerks_OMR"]
    df_calc["TotalMonthly"] = df_calc["DirectPay"] + df_calc["Allowances"] + df_calc["Protections"] + df_calc["Perks"]
    df_calc["TotalAnnual"] = df_calc["TotalMonthly"] * 12.0

    # Macro Metric Cards
    hr1, hr2, hr3, hr4 = st.columns(4)
    hr1.metric("Total Headcount", len(df_calc))
    hr2.metric("Monthly Base Payroll", f"OMR {df_calc['BaseSalary_OMR'].sum():,.2f}")
    hr3.metric("Total Monthly Rewards", f"OMR {df_calc['TotalMonthly'].sum():,.2f}")
    hr4.metric("Annual Rewards Budget", f"OMR {df_calc['TotalAnnual'].sum():,.2f}")

    st.divider()

    # Department Filter
    all_depts = ["All Departments"] + sorted(df_calc["Department"].dropna().unique().tolist())
    selected_dept = st.selectbox("Filter Workforce by Department:", all_depts)

    if selected_dept != "All Departments":
        filtered_df = df_calc[df_calc["Department"] == selected_dept]
    else:
        filtered_df = df_calc

    st.markdown("#### 📋 Comprehensive Employee Rewards Registry")
    display_cols = ["EmpID", "Name", "Department", "Grade", "BaseSalary_OMR", "TotalMonthly", "TotalAnnual"]
    
    st.dataframe(
        filtered_df[display_cols], 
        use_container_width=True,
        column_config={
            "EmpID": st.column_config.TextColumn("ID", width="small"),
            "Name": st.column_config.TextColumn("Full Name", width="medium"),
            "Department": st.column_config.TextColumn("Department", width="medium"),
            "Grade": st.column_config.TextColumn("Grade", width="small"),
            "BaseSalary_OMR": st.column_config.NumberColumn("Base Salary (OMR)", format="OMR %.3f"),
            "TotalMonthly": st.column_config.NumberColumn("Total Monthly (OMR)", format="OMR %.3f"),
            "TotalAnnual": st.column_config.NumberColumn("Total Annual (OMR)", format="OMR %.3f"),
        }
    )

    # Department Cost Comparison
    st.markdown("#### 🏢 Monthly Rewards Expenditure by Department")
    dept_costs = df_calc.groupby("Department")["TotalMonthly"].sum().reset_index()
    st.bar_chart(dept_costs.set_index("Department"))
