import streamlit as st
import pandas as pd

st.set_page_config(page_title="Total Rewards Statement Agent", layout="wide")

st.title("💼 Total Rewards Statement Agent")
st.caption("MNGT3557 Compensation & Performance Management | Section 1 Agent (Topic 8)")

# Load Data
try:
    df = pd.read_csv("dataset.csv")
except Exception:
    st.error("Please place 'dataset.csv' in the same directory.")
    st.stop()

# Employee Selector Dropdown
emp_options = df.apply(
    lambda r: f"{r.get('EmpID', 'N/A')} - {r.get('Name', 'Unknown')} ({r.get('Department', 'General')})", 
    axis=1
).tolist()
selected_label = st.selectbox("Select Employee for Total Rewards Review:", emp_options)
selected_id = selected_label.split(" - ")[0]
emp = df[df["EmpID"] == selected_id].iloc[0]

# Computations
direct_pay = float(emp["BaseSalary_OMR"]) + float(emp["Bonus_OMR"])
allowances = float(emp["HousingAllow_OMR"]) + float(emp["TransportAllow_OMR"])
protections = float(emp["HealthCover_OMR"]) + float(emp["PensionContrib_OMR"])
perks = float(emp["FlightTickets_OMR"]) + float(emp["WellnessPerks_OMR"])

monthly_total = direct_pay + allowances + protections + perks
annual_total = monthly_total * 12.0
annual_base = float(emp["BaseSalary_OMR"]) * 12.0
reward_multiplier = (monthly_total / float(emp["BaseSalary_OMR"]))

# Summary KPI Cards
col1, col2, col3, col4 = st.columns(4)
col1.metric("Base Monthly Salary", f"OMR {emp['BaseSalary_OMR']:.3f}")
col2.metric("Total Monthly Rewards", f"OMR {monthly_total:.3f}")
col3.metric("Annual Total Package", f"OMR {annual_total:,.3f}")
col4.metric("Total Rewards Multiplier", f"{reward_multiplier:.2f}x Base")

st.divider()

# Layout: Visual Breakdown and Details Table
col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("Component Breakdown (Monthly)")
    breakdown_data = pd.DataFrame({
        "Reward Category": ["Direct Cash (Base + Bonus)", "Allowances (Housing + Transport)", "Health & Social Protection", "Perks & Travel Subsidies"],
        "Amount (OMR)": [direct_pay, allowances, protections, perks],
        "Percentage": [
            f"{(direct_pay / monthly_total) * 100:.1f}%",
            f"{(allowances / monthly_total) * 100:.1f}%",
            f"{(protections / monthly_total) * 100:.1f}%",
            f"{(perks / monthly_total) * 100:.1f}%"
        ]
    })
    st.dataframe(breakdown_data, use_container_width=True, hide_index=True)
    st.bar_chart(breakdown_data.set_index("Reward Category")["Amount (OMR)"])

with col_right:
    st.subheader("Personalized Rewards Statement")
    statement_markdown = f"""
    **Employee Profile:** {emp['Name']} ({emp['EmpID']})  
    **Grade / Role:** Grade {emp['Grade']} | {emp['Department']}  

    ---
    ### Financial Summary
    * **Direct Base Pay:** OMR {emp['BaseSalary_OMR']:.3f}
    * **Performance Bonus:** OMR {emp['Bonus_OMR']:.3f}
    * **Company Housing Allowance:** OMR {emp['HousingAllow_OMR']:.3f}
    * **Transportation Allowance:** OMR {emp['TransportAllow_OMR']:.3f}
    * **Employer Health Coverage:** OMR {emp['HealthCover_OMR']:.3f}
    * **Employer Pension / Protection:** OMR {emp['PensionContrib_OMR']:.3f}
    * **Annual Flight Subsidies (Monthly Equiv.):** OMR {emp['FlightTickets_OMR']:.3f}
    * **Wellness & Other Benefits:** OMR {emp['WellnessPerks_OMR']:.3f}
    ---
    **Your Complete Compensation Package:**  
    Your base salary represents only **{(float(emp['BaseSalary_OMR']) / monthly_total) * 100:.1f}%** of what the organization invests in you. The full monetary value of your compensation is **OMR {monthly_total:.3f} per month** (**OMR {annual_total:,.3f} annually**).
    """
    st.info(statement_markdown)

st.divider()
st.subheader("Full Organization Dataset")
st.dataframe(df, use_container_width=True)
