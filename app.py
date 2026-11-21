import streamlit as st
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime

st.set_page_config(page_title="Total Rewards & Autonomous OT Agent", layout="wide")

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

# Ensure required columns exist
if "Nationality" not in df.columns:
    df["Nationality"] = df["PensionContrib_OMR"].apply(lambda x: "Omani" if float(x) > 0 else "Expatriate")
if "Age" not in df.columns:
    np.random.seed(42)
    df["Age"] = np.random.randint(26, 52, size=len(df))
if "YearsOfService" not in df.columns:
    df["YearsOfService"] = df["Age"].apply(lambda a: max(1, a - 24))

# ==============================================================================
# SHARED CROSS-TAB / MULTI-DEVICE AGENT MEMORY (@st.cache_resource + JSON backup)
# ==============================================================================
STATE_FILE = "agent_shared_state.json"

@st.cache_resource
def get_shared_agent_store():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "hr_ot_campaigns": [],
        "emp_ot_requests": [],
        "approved_ot_ledger": {},
        "agent_activity_log": [
            "🤖 [System Boot] Autonomous Total Rewards & Overtime Agent initialized (Multi-Session Sync Active)."
        ]
    }

shared_store = get_shared_agent_store()

def save_shared_store():
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(shared_store, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def log_agent_action(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    shared_store["agent_activity_log"].insert(0, f"🤖 [{timestamp}] {message}")
    save_shared_store()

# 2. Local Session State Initialization (Per Browser Tab Login)
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = None
    st.session_state.emp_id = None
if "spf_rate" not in st.session_state:
    st.session_state.spf_rate = 0.11

# Helper function to generate 12-month dynamic payroll history per employee
def generate_annual_payroll_history(emp_record, custom_ot_day=0.0, custom_ot_night=0.0, custom_bonus=None, spf_rate=0.11):
    months = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    emp_id = str(emp_record["EmpID"]).upper()
    base_sal = float(emp_record["BaseSalary_OMR"])
    allowances = float(emp_record["HousingAllow_OMR"]) + float(emp_record["TransportAllow_OMR"])
    hourly_rate = base_sal / 240.0
    is_national = str(emp_record.get("Nationality", "Omani")).strip().lower() == "omani"
    
    monthly_pension_employer = (base_sal * spf_rate) if is_national else 0.0
    health_cover = float(emp_record["HealthCover_OMR"])
    perks = float(emp_record["FlightTickets_OMR"]) + float(emp_record["WellnessPerks_OMR"])
    
    # Retrieve shared agent-approved OT hours for December
    ledger_entry = shared_store["approved_ot_ledger"].get(emp_id, {"day": 0.0, "night": 0.0})
    
    np.random.seed(int("".join([str(ord(c)) for c in emp_id])) % 100000)
    
    records = []
    for idx, m in enumerate(months):
        if idx == 11:  # Current Month: December
            day_ot_hrs = float(custom_ot_day) + float(ledger_entry["day"])
            night_ot_hrs = float(custom_ot_night) + float(ledger_entry["night"])
            monthly_bonus = float(custom_bonus) if custom_bonus is not None else float(emp_record["Bonus_OMR"]) * 1.5
        else:
            day_ot_hrs = float(np.random.choice([0, 5, 8, 12, 16], p=[0.2, 0.3, 0.25, 0.15, 0.1]))
            night_ot_hrs = float(np.random.choice([0, 4, 8], p=[0.6, 0.3, 0.1]))
            base_bonus = float(emp_record["Bonus_OMR"])
            if m == "June":
                monthly_bonus = base_bonus * 1.5
            elif m in ["July", "August"]:
                monthly_bonus = base_bonus * 0.5
            else:
                monthly_bonus = base_bonus
            
        ot_pay = (day_ot_hrs * hourly_rate * 1.25) + (night_ot_hrs * hourly_rate * 1.50)
        direct_cash = base_sal + ot_pay + monthly_bonus
        social_protections = health_cover + monthly_pension_employer
        total_month_rewards = direct_cash + allowances + social_protections + perks
        
        records.append({
            "Month": m,
            "Base_Salary": base_sal,
            "Day_OT_Hrs": day_ot_hrs,
            "Night_OT_Hrs": night_ot_hrs,
            "OT_Pay": ot_pay,
            "Incentive_Bonus": monthly_bonus,
            "Cash_Allowances": allowances,
            "SPF_Pension": monthly_pension_employer,
            "Health_Insurance": health_cover,
            "Perks_Subsidies": perks,
            "Net_Cash_Pay": direct_cash + allowances,
            "Total_Rewards_Value": total_month_rewards
        })
    return pd.DataFrame(records)

# Function to render employee statement & Pension Analytics
def render_employee_statement(emp_record, custom_ot_day=0.0, custom_ot_night=0.0, custom_bonus=None, spf_rate=0.11):
    monthly_df = generate_annual_payroll_history(emp_record, custom_ot_day, custom_ot_night, custom_bonus, spf_rate)
    
    annual_base = monthly_df["Base_Salary"].sum()
    annual_ot = monthly_df["OT_Pay"].sum()
    annual_bonus = monthly_df["Incentive_Bonus"].sum()
    annual_pension = monthly_df["SPF_Pension"].sum()
    annual_total_rewards = monthly_df["Total_Rewards_Value"].sum()
    
    multiplier = (annual_total_rewards / annual_base) if annual_base > 0 else 0
    base_share = (annual_base / annual_total_rewards) * 100 if annual_total_rewards > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Annual Base Salary", f"OMR {annual_base:,.2f}")
    c2.metric("Annual Overtime Earned", f"OMR {annual_ot:,.2f}", delta=f"{monthly_df['Day_OT_Hrs'].sum() + monthly_df['Night_OT_Hrs'].sum():.1f} total hrs")
    c3.metric("Annual Total Rewards Value", f"OMR {annual_total_rewards:,.2f}")
    c4.metric("Package Multiplier", f"{multiplier:.2f}x Base")

    st.divider()

    # Section 1: Detailed 12-Month Payroll Breakdown Table
    st.markdown("### 📅 12-Month Detailed Payroll & Rewards History")
    st.caption("📌 Note: The current month (**December**) is highlighted in grey and automatically updates whenever the AI Agent verifies extra-time hours.")

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
            "SPF_Pension": st.column_config.NumberColumn("SPF Pension (OMR)", format="OMR %.2f"),
            "Health_Insurance": st.column_config.NumberColumn("Health Ins.", format="OMR %.2f"),
            "Perks_Subsidies": st.column_config.NumberColumn("Perks/Travel", format="OMR %.2f"),
            "Net_Cash_Pay": st.column_config.NumberColumn("Cash Payout", format="OMR %.2f"),
            "Total_Rewards_Value": st.column_config.NumberColumn("Total Rewards", format="OMR %.2f"),
        }
    )

    st.write("")

    # Section 2: Oman Social Protection Fund & Pension Analytics
    st.markdown("### 🛡️ Social Protection & Retirement Pension Forecast")
    age = int(emp_record.get("Age", 32))
    service_years = int(emp_record.get("YearsOfService", 8))
    retire_age = 60
    years_to_retire = max(0, retire_age - age)
    base_sal = float(emp_record["BaseSalary_OMR"])
    is_omani = str(emp_record.get("Nationality", "Omani")).strip().lower() == "omani"

    if is_omani:
        emp_lifetime_contrib = base_sal * 0.075 * 12 * service_years
        company_lifetime_contrib = base_sal * spf_rate * 12 * service_years
        total_accumulated_fund = emp_lifetime_contrib + company_lifetime_contrib
        projected_total_years = service_years + years_to_retire
        pension_accrual_rate = min(0.80, projected_total_years * 0.02)
        projected_monthly_pension = base_sal * pension_accrual_rate

        p_col1, p_col2, p_col3, p_col4 = st.columns(4)
        p_col1.metric("Current Service", f"{service_years} Years")
        p_col2.metric("Years to Retirement", f"{years_to_retire} Years", f"Target Age: {retire_age}")
        p_col3.metric("Company Paid to SPF", f"OMR {company_lifetime_contrib:,.2f}", f"{spf_rate*100:.1f}% Share")
        p_col4.metric("Est. Monthly Pension", f"OMR {projected_monthly_pension:,.2f}", f"{pension_accrual_rate*100:.0f}% of Base")

        pension_table = pd.DataFrame({
            "Retirement Parameter": [
                "Employee Current Age",
                "Official Retirement Age",
                "Completed Years of Service",
                "Remaining Years to Pension",
                "Employee Cumulative Contributions (7.5%)",
                "Employer Cumulative Contributions (11%)",
                "Total Value Accumulated in SPF",
                "Projected Monthly Pension at Age 60"
            ],
            "Details & Figures": [
                f"{age} Years Old",
                f"{retire_age} Years",
                f"{service_years} Years",
                f"{years_to_retire} Years",
                f"OMR {emp_lifetime_contrib:,.2f}",
                f"OMR {company_lifetime_contrib:,.2f}",
                f"OMR {total_accumulated_fund:,.2f}",
                f"OMR {projected_monthly_pension:,.2f} per month"
            ]
        })
        st.dataframe(pension_table, use_container_width=True, hide_index=True)
    else:
        st.info("ℹ️ Expatriate Employee: Covered under statutory End-of-Service Gratuity (EOSG) as per Oman Labour Law.")

    st.write("")

    # Section 3: Visual Trends & Formal Statement
    col_chart, col_summary = st.columns([1.1, 0.9])
    with col_chart:
        st.markdown("#### 📈 Monthly Compensation Trends")
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
        * **Employer Pension Contributions (SPF):** OMR {annual_pension:,.2f}
        * **Employer Healthcare Coverage:** OMR {monthly_df['Health_Insurance'].sum():,.2f}
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
st.title("💼 Autonomous Total Rewards & Extra-Time Agent")
st.caption("MNGT3557 Compensation & Performance Management | Section 1 Agent (Topic 8)")
st.divider()

# ==============================================================================
# LOGIN SCREEN
# ==============================================================================
if not st.session_state.logged_in:
    st.subheader("🔐 Secure Portal Authentication")
    col_a, col_b = st.columns([1, 1])
    with col_a:
        portal_choice = st.radio("Select Portal:", ["👤 Employee Portal", "🏢 HR / Management Portal"])
    with col_b:
        with st.form("login_form"):
            user_id = st.text_input("Enter User ID:", placeholder="e.g., EMP201 for Employee or hr for HR")
            password = st.text_input("Enter Password:", type="password", placeholder="Default: 1234")
            submitted = st.form_submit_button("Sign In", type="primary")
            if submitted:
                cleaned_id = user_id.strip()
                if "Employee" in portal_choice:
                    valid_ids = df["EmpID"].astype(str).str.upper().tolist()
                    if cleaned_id.upper() in valid_ids and password == "1234":
                        st.session_state.logged_in = True
                        st.session_state.user_role = "Employee"
                        st.session_state.emp_id = cleaned_id.upper()
                        st.rerun()
                    else:
                        st.error("❌ Invalid Employee ID or Password! (Hint: Password is 1234)")
                elif "HR" in portal_choice:
                    if cleaned_id.lower() == "hr" and password == "1234":
                        st.session_state.logged_in = True
                        st.session_state.user_role = "HR"
                        st.rerun()
                    else:
                        st.error("❌ Invalid HR credentials! (Use ID: hr and Password: 1234)")

    st.write("")
    with st.expander("⚡ Developer / Demo Fast Bypass"):
        st.caption("Open HR in one browser tab and an Employee in another tab to test real-time cross-tab sync:")
        dev_col1, dev_col2, dev_col3 = st.columns(3)
        with dev_col1:
            if st.button("🚀 Quick Login as HR Specialist"):
                st.session_state.logged_in = True
                st.session_state.user_role = "HR"
                st.rerun()
        with dev_col2:
            emp1 = str(df.iloc[0]["EmpID"]).upper()
            if st.button(f"👤 Quick Login as {emp1} ({df.iloc[0]['Department']})"):
                st.session_state.logged_in = True
                st.session_state.user_role = "Employee"
                st.session_state.emp_id = emp1
                st.rerun()
        with dev_col3:
            if len(df) > 1:
                emp2 = str(df.iloc[1]["EmpID"]).upper()
                if st.button(f"👤 Quick Login as {emp2} ({df.iloc[1]['Department']})"):
                    st.session_state.logged_in = True
                    st.session_state.user_role = "Employee"
                    st.session_state.emp_id = emp2
                    st.rerun()

# ==============================================================================
# AUTHENTICATED PORTALS
# ==============================================================================
else:
    # Top Sync / Refresh Bar for Instant Multi-Tab Sync
    sync_col1, sync_col2 = st.columns([4, 1])
    with sync_col2:
        if st.button("🔄 Sync Live Updates", use_container_width=True):
            st.rerun()

    st.sidebar.write(f"Logged in as: **{st.session_state.user_role}**")
    if st.session_state.user_role == "Employee":
        st.sidebar.write(f"Employee ID: **{st.session_state.emp_id}**")
    if st.sidebar.button("Sign Out"):
        st.session_state.logged_in = False
        st.session_state.user_role = None
        st.session_state.emp_id = None
        st.rerun()

    # Live Agent Activity Feed in Sidebar
    st.sidebar.divider()
    st.sidebar.subheader("🤖 Autonomous Agent Live Log")
    for log_item in shared_store["agent_activity_log"][:6]:
        st.sidebar.caption(log_item)

    # ==========================================================================
    # 1. EMPLOYEE PORTAL
    # ==========================================================================
    if st.session_state.user_role == "Employee":
        emp_record = df[df["EmpID"].astype(str).str.upper() == st.session_state.emp_id].iloc[0]
        emp_id = str(emp_record["EmpID"]).upper()
        emp_dept = str(emp_record["Department"]).strip()
        
        st.subheader(f"👤 Welcome, {emp_record['Name']} ({emp_id}) | {emp_dept} Department")

        # Count unread/pending offers for notification badge
        relevant_campaigns = [
            c for c in shared_store["hr_ot_campaigns"]
            if c["department"].strip().lower() == emp_dept.lower() or c["department"] == "All Departments"
        ]
        pending_offers = [
            c for c in relevant_campaigns
            if emp_id not in c["accepted_by"] and emp_id not in c["declined_by"] and (c["headcount_needed"] - len(c["accepted_by"])) > 0
        ]

        inbox_label = f"📩 Agent Extra-Time Offers ({len(pending_offers)} New)" if pending_offers else "📩 Agent Extra-Time Offers (Inbox)"

        tab_inbox, tab_request, tab_statement = st.tabs([
            inbox_label, 
            "🙋‍♂️ Request Extra Time (Submit to HR)", 
            "📊 My Total Rewards Statement"
        ])

        # TAB 1: Respond to HR-Initiated Extra Time Campaigns
        with tab_inbox:
            st.markdown("### 📩 Incoming Extra-Time Invitations from AI Agent")
            st.caption("When HR dispatches extra-time needs in another tab, click '🔄 Sync Live Updates' at the top right to see incoming invitations immediately.")
            
            if not relevant_campaigns:
                st.info(f"📭 No active extra-time calls from HR for **{emp_dept}** right now.")
            else:
                for camp in relevant_campaigns:
                    with st.container(border=True):
                        c_info, c_action = st.columns([2.2, 1])
                        accepted_count = len(camp["accepted_by"])
                        slots_left = camp["headcount_needed"] - accepted_count
                        
                        with c_info:
                            st.markdown(f"**Campaign #{camp['id']} — {camp['title']}**")
                            st.write(f"• **Hours Offered:** {camp['hours']} hrs ({camp['ot_type']}) | **Target Dept:** {camp['department']}")
                            st.write(f"• **Spots Remaining:** {slots_left} of {camp['headcount_needed']} needed")
                        
                        with c_action:
                            if emp_id in camp["accepted_by"]:
                                st.success("✅ Accepted & Verified by Attendance System")
                            elif emp_id in camp["declined_by"]:
                                st.warning("❌ Declined")
                            elif slots_left <= 0:
                                st.error("🔒 Quota Filled")
                            else:
                                if st.button("✅ Accept Offer", key=f"acc_{camp['id']}_{emp_id}", type="primary"):
                                    camp["accepted_by"].append(emp_id)
                                    if emp_id not in shared_store["approved_ot_ledger"]:
                                        shared_store["approved_ot_ledger"][emp_id] = {"day": 0.0, "night": 0.0}
                                    if "Day" in camp["ot_type"]:
                                        shared_store["approved_ot_ledger"][emp_id]["day"] += float(camp["hours"])
                                    else:
                                        shared_store["approved_ot_ledger"][emp_id]["night"] += float(camp["hours"])
                                    
                                    log_agent_action(f"{emp_id} accepted Campaign #{camp['id']} ({camp['hours']}h). Attendance verified, payroll & budget updated, HR notified.")
                                    st.rerun()
                                    
                                if st.button("❌ Decline", key=f"dec_{camp['id']}_{emp_id}"):
                                    camp["declined_by"].append(emp_id)
                                    log_agent_action(f"{emp_id} declined Campaign #{camp['id']}. HR notified.")
                                    st.rerun()

        # TAB 2: Employee-Initiated Extra Time Request
        with tab_request:
            st.markdown("### 🙋‍♂️ Submit Extra-Time Request to HR")
            with st.form("emp_ot_form"):
                req_col1, req_col2 = st.columns(2)
                with req_col1:
                    req_hours = st.number_input("Requested Extra Hours:", min_value=1.0, max_value=40.0, value=4.0, step=1.0)
                    req_type = st.selectbox("Overtime Type:", ["Day Overtime (1.25x)", "Night Overtime (1.50x)"])
                with req_col2:
                    req_reason = st.text_area("Justification / Task Description:", placeholder="e.g., Year-end inventory audit and urgent client reporting")
                
                submit_req = st.form_submit_button("📤 Send Request to AI Agent", type="primary")
                if submit_req:
                    new_req = {
                        "req_id": f"REQ-{len(shared_store['emp_ot_requests']) + 101}",
                        "emp_id": emp_id,
                        "emp_name": emp_record["Name"],
                        "department": emp_dept,
                        "hours": req_hours,
                        "ot_type": req_type,
                        "reason": req_reason if req_reason.strip() else "Operational task completion",
                        "status": "Pending HR Review",
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                    }
                    shared_store["emp_ot_requests"].insert(0, new_req)
                    log_agent_action(f"New OT request {new_req['req_id']} from {emp_id} ({req_hours}h) routed to HR.")
                    st.success("✅ Request submitted! Switch to the HR tab and click '🔄 Sync Live Updates' to approve it.")

            st.markdown("#### 📋 My Submitted Extra-Time Requests")
            my_reqs = [r for r in shared_store["emp_ot_requests"] if r["emp_id"] == emp_id]
            if my_reqs:
                st.dataframe(pd.DataFrame(my_reqs), use_container_width=True, hide_index=True)
            else:
                st.caption("No personal requests submitted yet.")

        # TAB 3: Full Total Rewards Statement
        with tab_statement:
            render_employee_statement(emp_record, spf_rate=st.session_state.spf_rate)

    # ==========================================================================
    # 2. HR / MANAGEMENT PORTAL
    # ==========================================================================
    elif st.session_state.user_role == "HR":
        st.subheader("🏢 HR Compensation & Autonomous Extra-Time Command Center")

        st.sidebar.divider()
        st.sidebar.subheader("⚙️ Oman Pension / SPF Policy")
        st.session_state.spf_rate = st.sidebar.slider(
            "Employer SPF Pension Share (%)",
            min_value=5.0, max_value=20.0, value=11.0, step=0.5
        ) / 100.0

        # Calculate live organization budget including Agent-Approved Extra Time
        df_calc = df.copy()
        extra_ot_costs = []
        for _, r in df_calc.iterrows():
            eid = str(r["EmpID"]).upper()
            base = float(r["BaseSalary_OMR"])
            hr_rate = base / 240.0
            ledger = shared_store["approved_ot_ledger"].get(eid, {"day": 0.0, "night": 0.0})
            ot_cost = (ledger["day"] * hr_rate * 1.25) + (ledger["night"] * hr_rate * 1.50)
            extra_ot_costs.append(ot_cost)
        
        df_calc["Agent_Approved_OT_OMR"] = extra_ot_costs

        def calc_emp_annual_total(r):
            base = float(r["BaseSalary_OMR"])
            is_nat = str(r.get("Nationality", "Omani")).strip().lower() == "omani"
            pension_m = (base * st.session_state.spf_rate) if is_nat else 0.0
            direct_m = base + float(r["Bonus_OMR"])
            allow_m = float(r["HousingAllow_OMR"]) + float(r["TransportAllow_OMR"])
            prot_m = float(r["HealthCover_OMR"]) + pension_m
            perks_m = float(r["FlightTickets_OMR"]) + float(r["WellnessPerks_OMR"])
            return ((direct_m + allow_m + prot_m + perks_m) * 12.0) + float(r["Agent_Approved_OT_OMR"])

        df_calc["TotalAnnual"] = df_calc.apply(calc_emp_annual_total, axis=1)
        df_calc["TotalMonthly"] = df_calc["TotalAnnual"] / 12.0

        total_agent_ot_spend = df_calc["Agent_Approved_OT_OMR"].sum()
        h1, h2, h3, h4 = st.columns(4)
        h1.metric("Total Headcount", len(df_calc))
        h2.metric("Agent-Verified OT Spend (Dec)", f"OMR {total_agent_ot_spend:,.2f}", delta="Auto-Balanced")
        h3.metric("Total Monthly Rewards", f"OMR {df_calc['TotalMonthly'].sum():,.2f}")
        h4.metric("Rebalanced Annual Budget", f"OMR {df_calc['TotalAnnual'].sum():,.2f}")

        st.divider()

        pending_emp_reqs = [r for r in shared_store["emp_ot_requests"] if r["status"] == "Pending HR Review"]
        req_tab_label = f"📥 Workflow 2: Review Employee OT Requests ({len(pending_emp_reqs)} Pending)" if pending_emp_reqs else "📥 Workflow 2: Review Employee OT Requests"

        hr_tab1, hr_tab2, hr_tab3 = st.tabs([
            "📢 Workflow 1: Dispatch Extra-Time Need (HR → Employees)",
            req_tab_label,
            "🔍 Individual Audit & Workforce Registry"
        ])

        # HR TAB 1: HR Initiates Extra Time Campaign
        with hr_tab1:
            st.markdown("### 📢 Dispatch Autonomous Extra-Time Call to Target Employees")
            with st.form("hr_dispatch_form"):
                d_col1, d_col2, d_col3, d_col4 = st.columns(4)
                with d_col1:
                    all_depts = ["All Departments"] + sorted(df["Department"].dropna().unique().tolist())
                    target_dept = st.selectbox("Target Department:", all_depts)
                with d_col2:
                    needed_staff = st.number_input("Employees Needed:", min_value=1, max_value=20, value=2, step=1)
                with d_col3:
                    hours_per_emp = st.number_input("Hours per Employee:", min_value=1.0, max_value=40.0, value=6.0, step=1.0)
                with d_col4:
                    camp_ot_type = st.selectbox("Overtime Rate:", ["Day Overtime (1.25x)", "Night Overtime (1.50x)"])
                
                camp_title = st.text_input("Task / Shift Description:", value="End-of-Year Operational Surge & Inventory Audit")
                dispatch_btn = st.form_submit_button("🤖 Launch AI Agent Dispatch", type="primary")
                
                if dispatch_btn:
                    if target_dept == "All Departments":
                        target_emps = df["EmpID"].astype(str).str.upper().tolist()
                    else:
                        target_emps = df[df["Department"] == target_dept]["EmpID"].astype(str).str.upper().tolist()
                    
                    new_camp = {
                        "id": f"OT-{len(shared_store['hr_ot_campaigns']) + 501}",
                        "title": camp_title,
                        "department": target_dept,
                        "headcount_needed": int(needed_staff),
                        "hours": float(hours_per_emp),
                        "ot_type": camp_ot_type,
                        "notified_emps": target_emps,
                        "accepted_by": [],
                        "declined_by": []
                    }
                    shared_store["hr_ot_campaigns"].insert(0, new_camp)
                    log_agent_action(f"Campaign #{new_camp['id']} launched for {target_dept}. Notified {len(target_emps)} employees.")
                    st.success(f"🤖 Agent Dispatched! Messages sent to **{len(target_emps)} employees** in **{target_dept}**. Switch to the Employee tab and click '🔄 Sync Live Updates'.")

            st.markdown("#### 📊 Live Campaign Tracking & Responses")
            if not shared_store["hr_ot_campaigns"]:
                st.info("No extra-time campaigns dispatched yet. Create one above to see the Agent in action.")
            else:
                for c in shared_store["hr_ot_campaigns"]:
                    with st.container(border=True):
                        st.markdown(f"**Campaign #{c['id']}: {c['title']}** ({c['department']} | {c['hours']} hrs | {c['ot_type']})")
                        st.write(f"• **Progress:** {len(c['accepted_by'])} / {c['headcount_needed']} positions filled")
                        st.write(f"• **Accepted & Verified (Payroll Updated):** {', '.join(c['accepted_by']) if c['accepted_by'] else 'Awaiting responses...'}")
                        if c["declined_by"]:
                            st.write(f"• **Declined:** {', '.join(c['declined_by'])}")

        # HR TAB 2: Review Employee-Submitted OT Requests
        with hr_tab2:
            st.markdown("### 📥 Employee Extra-Time Requests Queue")
            if not shared_store["emp_ot_requests"]:
                st.info("📭 No employee extra-time requests in queue.")
            else:
                for req in shared_store["emp_ot_requests"]:
                    with st.container(border=True):
                        r_col1, r_col2 = st.columns([2.2, 1])
                        with r_col1:
                            st.markdown(f"**{req['req_id']} — {req['emp_name']} ({req['emp_id']})** | Dept: {req['department']}")
                            st.write(f"• **Requested:** {req['hours']} hrs ({req['ot_type']}) | **Submitted:** {req['timestamp']}")
                            st.write(f"• **Reason:** {req['reason']}")
                        with r_col2:
                            if req["status"] == "Pending HR Review":
                                if st.button("✅ Approve & Execute", key=f"hr_app_{req['req_id']}", type="primary"):
                                    req["status"] = "Approved & Paid"
                                    eid = req["emp_id"]
                                    if eid not in shared_store["approved_ot_ledger"]:
                                        shared_store["approved_ot_ledger"][eid] = {"day": 0.0, "night": 0.0}
                                    if "Day" in req["ot_type"]:
                                        shared_store["approved_ot_ledger"][eid]["day"] += float(req["hours"])
                                    else:
                                        shared_store["approved_ot_ledger"][eid]["night"] += float(req["hours"])
                                    
                                    log_agent_action(f"HR approved {req['req_id']} for {eid} ({req['hours']}h). Attendance verified, December pay & budget updated.")
                                    st.rerun()
                                if st.button("❌ Reject", key=f"hr_rej_{req['req_id']}"):
                                    req["status"] = "Rejected by HR"
                                    log_agent_action(f"HR rejected {req['req_id']} for {req['emp_id']}.")
                                    st.rerun()
                            elif req["status"] == "Approved & Paid":
                                st.success("✅ Approved & Credited to Payroll")
                            else:
                                st.error("❌ Rejected")

        # HR TAB 3: Individual Audit & Workforce Registry
        with hr_tab3:
            st.markdown("### 🔍 Individual Employee Audit & Manual Override")
            emp_options = df_calc.apply(
                lambda r: f"{r.get('EmpID', 'N/A')} - {r.get('Name', 'Unknown')} ({r.get('Department', 'General')})", 
                axis=1
            ).tolist()
            
            selected_label = st.selectbox("Select Employee to audit:", emp_options)
            selected_id = selected_label.split(" - ")[0]
            selected_emp = df_calc[df_calc["EmpID"] == selected_id].iloc[0]

            with st.expander("⚙️ Manual Variable Adjustment (Optional Override)", expanded=False):
                col_in1, col_in2, col_in3 = st.columns(3)
                with col_in1:
                    hr_day_ot = st.number_input("Extra Day OT Hours", min_value=0.0, max_value=80.0, value=0.0, step=1.0, key=f"hr_day_ot_{selected_id}")
                with col_in2:
                    hr_night_ot = st.number_input("Extra Night OT Hours", min_value=0.0, max_value=80.0, value=0.0, step=1.0, key=f"hr_night_ot_{selected_id}")
                with col_in3:
                    hr_bonus = st.number_input("December Bonus (OMR)", min_value=0.0, max_value=3000.0, value=float(selected_emp["Bonus_OMR"]) * 1.5, step=25.0, key=f"hr_bonus_{selected_id}")

            render_employee_statement(
                selected_emp, 
                custom_ot_day=hr_day_ot, 
                custom_ot_night=hr_night_ot, 
                custom_bonus=hr_bonus,
                spf_rate=st.session_state.spf_rate
            )

            st.divider()
            st.markdown("### 📋 Workforce Budget & Registry")
            display_cols = ["EmpID", "Name", "Department", "Grade", "BaseSalary_OMR", "Agent_Approved_OT_OMR", "TotalMonthly", "TotalAnnual"]
            st.dataframe(
                df_calc[display_cols], 
                use_container_width=True,
                column_config={
                    "EmpID": st.column_config.TextColumn("ID", width="small"),
                    "Name": st.column_config.TextColumn("Full Name", width="medium"),
                    "Department": st.column_config.TextColumn("Department", width="medium"),
                    "Grade": st.column_config.TextColumn("Grade", width="small"),
                    "BaseSalary_OMR": st.column_config.NumberColumn("Base Salary", format="OMR %.3f"),
                    "Agent_Approved_OT_OMR": st.column_config.NumberColumn("Agent OT (Dec)", format="OMR %.3f"),
                    "TotalMonthly": st.column_config.NumberColumn("Total Monthly", format="OMR %.3f"),
                    "TotalAnnual": st.column_config.NumberColumn("Total Annual", format="OMR %.3f"),
                }
            )
