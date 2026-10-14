import streamlit as st
import pandas as pd

st.set_page_config(page_title="Oman Pay Compliance Checker", layout="wide")

st.title("⚖️ Omani Labour Law: Pay Compliance Checker Agent")
st.caption("MNGT3557 Assignment | Section 1: AI Compliance Agent")

# Sidebar - Statutory Rule Parameters
st.sidebar.header("Statutory Standards (Omani Labour Law)")
MIN_WAGE_OMANI = st.sidebar.number_input("Minimum Basic Wage (OMR) - Omani", value=325.000)
MAX_REG_HOURS_WEEK = st.sidebar.number_input("Max Standard Hours / Week", value=40)
DAY_OT_RATE = st.sidebar.number_input("Day Overtime Rate", value=1.25)
NIGHT_OT_RATE = st.sidebar.number_input("Night Overtime Rate", value=1.50)
MAX_DEDUCTION_PCT = st.sidebar.slider("Max Deductions Permitted (% of Basic)", 0, 50, 25)

def audit_record(row):
    flags = []
    remediations = []
    
    basic = float(row['BasicSalary_OMR'])
    reg_hours = float(row['RegHours_Wk'])
    day_ot_hrs = float(row['DayOT_Hrs'])
    night_ot_hrs = float(row['NightOT_Hrs'])
    ot_paid = float(row['OT_Paid_OMR'])
    deductions = float(row['Deduction_OMR'])
    nationality = str(row['Nationality']).strip().lower()

    # Rule 1: Minimum Wage Check
    if nationality == 'omani' and basic < MIN_WAGE_OMANI:
        diff = MIN_WAGE_OMANI - basic
        flags.append(f"Basic wage deficit: OMR {basic:.3f} is below statutory threshold (OMR {MIN_WAGE_OMANI:.3f})")
        remediations.append(f"Adjust base pay upward by +OMR {diff:.3f}")

    # Rule 2: Working Hours Cap
    excess_hours = 0
    if reg_hours > MAX_REG_HOURS_WEEK:
        excess_hours = reg_hours - MAX_REG_HOURS_WEEK
        flags.append(f"Excess regular hours: {reg_hours} hrs worked (legal weekly cap is {MAX_REG_HOURS_WEEK} hrs)")
        remediations.append(f"Reclassify {excess_hours} hours as overtime")

    # Rule 3: Overtime Pay Audit (Basic / 240 hrs)
    hourly_rate = basic / 240.0
    statutory_day_ot = (day_ot_hrs + excess_hours) * hourly_rate * DAY_OT_RATE
    statutory_night_ot = night_ot_hrs * hourly_rate * NIGHT_OT_RATE
    total_statutory_ot = statutory_day_ot + statutory_night_ot

    if ot_paid < (total_statutory_ot - 0.005):
        shortfall = total_statutory_ot - ot_paid
        flags.append(f"Overtime underpayment: Paid OMR {ot_paid:.3f}, statutory due is OMR {total_statutory_ot:.3f}")
        remediations.append(f"Pay OT arrears of +OMR {shortfall:.3f}")

    # Rule 4: Maximum Permitted Deductions
    allowed_deduction = basic * (MAX_DEDUCTION_PCT / 100.0)
    if deductions > allowed_deduction:
        excess_deduction = deductions - allowed_deduction
        flags.append(f"Excessive deduction: OMR {deductions:.3f} exceeds {MAX_DEDUCTION_PCT}% limit (OMR {allowed_deduction:.3f})")
        remediations.append(f"Refund excess deduction of OMR {excess_deduction:.3f}")

    status = "COMPLIANT" if not flags else "NON-COMPLIANT"
    return {
        "Status": status,
        "Flags": " | ".join(flags) if flags else "All checks passed.",
        "Remediation": " | ".join(remediations) if remediations else "No action required."
    }

# Option to upload or use default dataset
uploaded_file = st.sidebar.file_uploader("Upload Payroll CSV", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
else:
    try:
        df = pd.read_csv("dataset.csv")
    except Exception:
        df = pd.DataFrame()

st.subheader("1. Payroll Records")
st.dataframe(df, use_container_width=True)

if st.button("🚀 Run Live Compliance Audit", type="primary"):
    audit_results = []
    for _, row in df.iterrows():
        res = audit_record(row)
        audit_results.append({
            "EmpID": row["EmpID"],
            "Name": row["Name"],
            "Nationality": row["Nationality"],
            "Status": res["Status"],
            "Violations Flagged": res["Flags"],
            "Required Remediation": res["Remediation"]
        })
    
    results_df = pd.DataFrame(audit_results)
    
    st.subheader("2. Audit Report & Remediation Plan")
    def color_status(val):
        return 'background-color: #ffcccc' if val == 'NON-COMPLIANT' else 'background-color: #ccffcc'
        
    # Compatible with both old (.applymap) and new (.map) Pandas versions
    try:
        styled_df = results_df.style.map(color_status, subset=['Status'])
    except AttributeError:
        styled_df = results_df.style.applymap(color_status, subset=['Status'])

    st.dataframe(styled_df, use_container_width=True)
    
    non_compliant = (results_df["Status"] == "NON-COMPLIANT").sum()
    col1, col2 = st.columns(2)
    col1.metric("Total Records Audited", len(results_df))
    col2.metric("Violations Found", non_compliant)
