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
        # Allow custom override for current month (December)
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

    # Section 1: Detailed 12-Month Payroll Breakdown Table with Grey Highlight on December
    st.markdown("### 📅 12-Month Detailed Payroll & Rewards History")
    st.caption("📌 Note: The current month (**December**) and all its active components are highlighted in grey for immediate identification.")

    def highlight_current_month(row):
        if row["Month"] == "December":
            return ["background-color: #6c757d; color: #ffffff; font-weight: bold; border-top: 2px solid #343a40; border-bottom: 2px solid #343a40;"] * len(row)
        return [""] * len(row)

    styled_monthly_df = monthly_df.style.apply(highlight_current_month, axis=1)

    st.dataframe(
        styled_monthly_df, 
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
            "Total_Rewards_Value": st.column_config.NumberColumn("Total Rewards", formatimport streamlit as st
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
        # Allow custom override for current month (December)
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

    # Section 1: Detailed 12-Month Payroll Breakdown Table with Grey Highlight on December
    st.markdown("### 📅 12-Month Detailed Payroll & Rewards History")
    st.caption("📌 Note: The current month (**December**) and all its active components are highlighted in grey for immediate identification.")

    def highlight_current_month(row):
        if row["Month"] == "December":
            return ["background-color: #6c757d; color: #ffffff; font-weight: bold; border-top: 2px solid #343a40; border-bottom: 2px solid #343a40;"] * len(row)
        return [""] * len(row)

    styled_monthly_df = monthly_df.style.apply(highlight_current_month, axis=1)

    st.dataframe(
        styled_monthly_df, 
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
            "Total_Rewards_Value": st.column_config.NumberColumn("Total Rewards", format
