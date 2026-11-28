import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import re
from datetime import datetime

st.set_page_config(page_title="Autonomous HR Rewards & Extra-Time Agent", page_icon="🤖", layout="wide")

# ==============================================================================
# 1. LOAD & AUTO-NORMALIZE DATASET
# ==============================================================================
@st.cache_data
def load_data():
    try:
        raw_df = pd.read_csv("dataset.csv")
    except Exception:
        return pd.DataFrame()

    if raw_df.empty:
        return raw_df

    # Auto-map flexible column names so any CSV schema works without crashing
    col_map = {}
    for c in raw_df.columns:
        cl = c.strip().lower().replace("_", "").replace(" ", "")
        if cl in ["empid", "employeeid", "id"]:
            col_map[c] = "EmpID"
        elif cl in ["name", "fullname", "employeename"]:
            col_map[c] = "Name"
        elif cl in ["department", "dept"]:
            col_map[c] = "Department"
        elif cl in ["grade", "jobgrade"]:
            col_map[c] = "Grade"
        elif "basesalary" in cl or cl == "salary":
            col_map[c] = "BaseSalary_OMR"
        elif "bonus" in cl:
            col_map[c] = "Bonus_OMR"
        elif "housing" in cl:
            col_map[c] = "HousingAllow_OMR"
        elif "transport" in cl:
            col_map[c] = "TransportAllow_OMR"
        elif "health" in cl:
            col_map[c] = "HealthCover_OMR"
        elif "pension" in cl or "spf" in cl:
            col_map[c] = "PensionContrib_OMR"
        elif "flight" in cl or "ticket" in cl:
            col_map[c] = "FlightTickets_OMR"
        elif "wellness" in cl or "perk" in cl:
            col_map[c] = "WellnessPerks_OMR"
        elif "national" in cl:
            col_map[c] = "Nationality"
        elif cl == "age":
            col_map[c] = "Age"
        elif "service" in cl or "tenure" in cl:
            col_map[c] = "YearsOfService"

    df_clean = raw_df.rename(columns=col_map).copy()

    # Fill defaults for any missing columns
    if "EmpID" not in df_clean.columns:
        df_clean["EmpID"] = [f"EMP{201 + i}" for i in range(len(df_clean))]
    if "Name" not in df_clean.columns:
        df_clean["Name"] = [f"Employee {i + 1}" for i in range(len(df_clean))]
    if "Department" not in df_clean.columns:
        df_clean["Department"] = "Operations"
    if "Grade" not in df_clean.columns:
        df_clean["Grade"] = "G2"
    for num_col, default_val in [
        ("BaseSalary_OMR", 800.0),
        ("Bonus_OMR", 50.0),
        ("HousingAllow_OMR", 150.0),
        ("TransportAllow_OMR", 60.0),
        ("HealthCover_OMR", 35.0),
        ("PensionContrib_OMR", 88.0),
        ("FlightTickets_OMR", 25.0),
        ("WellnessPerks_OMR", 15.0),
    ]:
        if num_col not in df_clean.columns:
            df_clean[num_col] = default_val
        else:
            df_clean[num_col] = pd.to_numeric(df_clean[num_col], errors="coerce").fillna(default_val)

    if "Nationality" not in df_clean.columns:
        df_clean["Nationality"] = df_clean["PensionContrib_OMR"].apply(lambda x: "Omani" if float(x) > 0 else "Expatriate")
    if "Age" not in df_clean.columns:
        np.random.seed(42)
        df_clean["Age"] = np.random.randint(26, 52, size=len(df_clean))
    if "YearsOfService" not in df_clean.columns:
        df_clean["YearsOfService"] = df_clean["Age"].apply(lambda a: max(1, int(a) - 24))

    return df_clean

df = load_data()

if df.empty:
    st.error("⚠️ 'dataset.csv' was not found or is empty. Please ensure 'dataset.csv' is in your GitHub repository.")
    st.stop()

# ==============================================================================
# 2. SHARED CROSS-SESSION AGENT MEMORY
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
        "agent_reasoning_log": [
            "🤖 [System Boot] Autonomous HR Compensation & Extra-Time Agent initialized."
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
    shared_store["agent_reasoning_log"].insert(0, f"🤖 [{timestamp}] {message}")
    save_shared_store()

# ==============================================================================
# 3. CALCULATION ENGINES (12-MONTH PAYROLL & OMANI SPF PENSION)
# ==============================================================================
def generate_annual_payroll_history(emp_record, spf_rate=0.11):
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

    ledger_entry = shared_store["approved_ot_ledger"].get(emp_id, {"day": 0.0, "night": 0.0})
    seed_val = sum(ord(c) for c in emp_id) % 100000
    np.random.seed(seed_val)

    records = []
    for idx, m in enumerate(months):
        if idx == 11:  # December (Active Month)
            day_ot_hrs = float(ledger_entry["day"])
            night_ot_hrs = float(ledger_entry["night"])
            monthly_bonus = float(emp_record["Bonus_OMR"]) * 1.5
        else:
            day_ot_hrs = float(np.random.choice([0, 5, 8, 12], p=[0.25, 0.35, 0.25, 0.15]))
            night_ot_hrs = float(np.random.choice([0, 4, 8], p=[0.65, 0.25, 0.10]))
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

def render_employee_statement_card(emp_id, spf_rate=0.11, unique_key="0"):
    matches = df[df["EmpID"].astype(str).str.upper() == emp_id.upper()]
    if matches.empty:
        st.error(f"Employee ID `{emp_id}` was not found in the workforce registry.")
        return

    emp_record = matches.iloc[0]
    monthly_df = generate_annual_payroll_history(emp_record, spf_rate)

    annual_base = monthly_df["Base_Salary"].sum()
    annual_ot = monthly_df["OT_Pay"].sum()
    annual_bonus = monthly_df["Incentive_Bonus"].sum()
    annual_pension = monthly_df["SPF_Pension"].sum()
    annual_total_rewards = monthly_df["Total_Rewards_Value"].sum()
    multiplier = (annual_total_rewards / annual_base) if annual_base > 0 else 0
    base_share = (annual_base / annual_total_rewards) * 100 if annual_total_rewards > 0 else 0

    st.markdown(f"#### 📊 Total Rewards & Pension Statement: **{emp_record['Name']} ({emp_id})**")
    st.caption(f"Department: **{emp_record['Department']}** | Grade: **{emp_record['Grade']}** | Status: **{emp_record['Nationality']}**")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Annual Base Salary", f"OMR {annual_base:,.2f}")
    c2.metric("Annual Overtime Pay", f"OMR {annual_ot:,.2f}", delta=f"{monthly_df['Day_OT_Hrs'].sum() + monthly_df['Night_OT_Hrs'].sum():.1f} hrs")
    c3.metric("Total Rewards Value", f"OMR {annual_total_rewards:,.2f}")
    c4.metric("Package Multiplier", f"{multiplier:.2f}x Base")

    def highlight_december(row):
        if row["Month"] == "December":
            return ["background-color: #6c757d; color: #ffffff; font-weight: bold;"] * len(row)
        return [""] * len(row)

    st.dataframe(
        monthly_df.style.apply(highlight_december, axis=1),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Base_Salary": st.column_config.NumberColumn("Base", format="OMR %.2f"),
            "Day_OT_Hrs": st.column_config.NumberColumn("Day OT(h)", format="%.1f"),
            "Night_OT_Hrs": st.column_config.NumberColumn("Night OT(h)", format="%.1f"),
            "OT_Pay": st.column_config.NumberColumn("OT Pay", format="OMR %.2f"),
            "Incentive_Bonus": st.column_config.NumberColumn("Bonus", format="OMR %.2f"),
            "Cash_Allowances": st.column_config.NumberColumn("Allowances", format="OMR %.2f"),
            "SPF_Pension": st.column_config.NumberColumn("SPF (11%)", format="OMR %.2f"),
            "Health_Insurance": st.column_config.NumberColumn("Health", format="OMR %.2f"),
            "Perks_Subsidies": st.column_config.NumberColumn("Perks", format="OMR %.2f"),
            "Net_Cash_Pay": st.column_config.NumberColumn("Cash Pay", format="OMR %.2f"),
            "Total_Rewards_Value": st.column_config.NumberColumn("Total Rewards", format="OMR %.2f"),
        }
    )

    st.markdown("##### 🛡️ Oman Social Protection Fund (SPF) & Retirement Forecast")
    age = int(emp_record.get("Age", 32))
    service_years = int(emp_record.get("YearsOfService", 8))
    retire_age = 60
    years_to_retire = max(0, retire_age - age)
    base_sal = float(emp_record["BaseSalary_OMR"])
    is_omani = str(emp_record.get("Nationality", "Omani")).strip().lower() == "omani"

    if is_omani:
        emp_lifetime = base_sal * 0.075 * 12 * service_years
        comp_lifetime = base_sal * spf_rate * 12 * service_years
        total_fund = emp_lifetime + comp_lifetime
        accrual_rate = min(0.80, (service_years + years_to_retire) * 0.02)
        est_pension = base_sal * accrual_rate

        pension_df = pd.DataFrame({
            "Retirement Metric": [
                "Current Age / Official Retirement Age",
                "Completed Service / Remaining Years",
                "Employee Cumulative Contributions (7.5%)",
                f"Company Cumulative Contributions ({spf_rate*100:.1f}%)",
                "Total Accumulated SPF Value to Date",
                "Projected Monthly Pension at Age 60"
            ],
            "Value": [
                f"{age} yrs / {retire_age} yrs",
                f"{service_years} yrs completed / {years_to_retire} yrs remaining",
                f"OMR {emp_lifetime:,.2f}",
                f"OMR {comp_lifetime:,.2f}",
                f"OMR {total_fund:,.2f}",
                f"OMR {est_pension:,.2f} / month ({accrual_rate*100:.0f}% of Base)"
            ]
        })
        st.dataframe(pension_df, use_container_width=True, hide_index=True)
    else:
        st.info("ℹ️ Expatriate Employee: Covered under Oman Labour Law End-of-Service Gratuity (EOSG) instead of SPF Pension.")

    col_c, col_s = st.columns([1.1, 0.9])
    with col_c:
        st.line_chart(monthly_df.set_index("Month")[["Net_Cash_Pay", "Total_Rewards_Value"]])
    with col_s:
        summary_txt = (
            f"TOTAL REWARDS STATEMENT - {emp_record['Name']} ({emp_id})\n"
            f"Department: {emp_record['Department']} | Grade: {emp_record['Grade']}\n"
            f"Annual Base Salary: OMR {annual_base:,.2f} ({base_share:.1f}% of package)\n"
            f"Annual Overtime: OMR {annual_ot:,.2f}\n"
            f"Annual Bonuses: OMR {annual_bonus:,.2f}\n"
            f"Annual Allowances: OMR {monthly_df['Cash_Allowances'].sum():,.2f}\n"
            f"Annual Employer SPF Pension: OMR {annual_pension:,.2f}\n"
            f"Annual Health & Perks: OMR {(monthly_df['Health_Insurance'].sum() + monthly_df['Perks_Subsidies'].sum()):,.2f}\n"
            f"GRAND TOTAL REWARDS INVESTMENT: OMR {annual_total_rewards:,.2f}\n"
        )
        st.success(f"💡 **Agent Insight:** Direct base salary is **{base_share:.1f}%** of total investment; indirect benefits & allowances add **OMR {(annual_total_rewards - annual_base):,.2f}** annually.")
        st.download_button(
            label="📥 Download Statement (.txt)",
            data=summary_txt,
            file_name=f"Statement_{emp_id}.txt",
            mime="text/plain",
            key=f"dl_{emp_id}_{unique_key}"
        )

def render_workforce_audit_card(spf_rate=0.11):
    df_calc = df.copy()
    ot_costs = []
    for _, r in df_calc.iterrows():
        eid = str(r["EmpID"]).upper()
        hr_rate = float(r["BaseSalary_OMR"]) / 240.0
        led = shared_store["approved_ot_ledger"].get(eid, {"day": 0.0, "night": 0.0})
        ot_costs.append((led["day"] * hr_rate * 1.25) + (led["night"] * hr_rate * 1.50))
    df_calc["Agent_OT_Dec_OMR"] = ot_costs

    def calc_ann(r):
        base = float(r["BaseSalary_OMR"])
        is_nat = str(r.get("Nationality", "Omani")).strip().lower() == "omani"
        pen = (base * spf_rate) if is_nat else 0.0
        m_tot = base + float(r["Bonus_OMR"]) + float(r["HousingAllow_OMR"]) + float(r["TransportAllow_OMR"]) + float(r["HealthCover_OMR"]) + pen + float(r["FlightTickets_OMR"]) + float(r["WellnessPerks_OMR"])
        return (m_tot * 12.0) + float(r["Agent_OT_Dec_OMR"])

    df_calc["TotalAnnual_OMR"] = df_calc.apply(calc_ann, axis=1)
    df_calc["TotalMonthly_OMR"] = df_calc["TotalAnnual_OMR"] / 12.0

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Workforce Size", len(df_calc))
    k2.metric("Agent-Verified OT (Dec)", f"OMR {df_calc['Agent_OT_Dec_OMR'].sum():,.2f}")
    k3.metric("Monthly Total Rewards", f"OMR {df_calc['TotalMonthly_OMR'].sum():,.2f}")
    k4.metric("Annual Rewards Budget", f"OMR {df_calc['TotalAnnual_OMR'].sum():,.2f}")

    st.dataframe(
        df_calc[["EmpID", "Name", "Department", "Grade", "Nationality", "BaseSalary_OMR", "Agent_OT_Dec_OMR", "TotalMonthly_OMR", "TotalAnnual_OMR"]],
        use_container_width=True,
        hide_index=True
    )
    st.bar_chart(df_calc.groupby("Department")["TotalMonthly_OMR"].sum())

# ==============================================================================
# 4. FLEXIBLE HYBRID INTENT & ENTITY PARSER (HANDLES TYPOS, ARABIC & ENGLISH)
# ==============================================================================
def parse_agent_command(prompt_text, active_role, active_emp_id):
    text = prompt_text.strip()
    low = text.lower()

    # 1. Extract Employee ID if mentioned
    emp_match = re.search(r'\b(?:emp\s*)?(20\d|21\d|220)\b', low)
    default_emp = str(df.iloc[0]["EmpID"]).upper()
    extracted_emp = f"EMP{emp_match.group(1)}" if emp_match else (active_emp_id if active_role == "Employee" else default_emp)

    # 2. Extract Department
    dept = "All Departments"
    if any(k in low for k in ["operat", "ops", "عمليات", "التشغيل"]):
        dept = "Operations"
    elif any(k in low for k in ["it", "tech", "تقنية", "معلومات"]):
        dept = "IT"
    elif any(k in low for k in ["fin", "money", "account", "مالية", "محاسبة"]):
        dept = "Finance"
    elif any(k in low for k in ["logis", "supply", "لوجست", "امداد"]):
        dept = "Logistics"
    elif re.search(r'\bhr\b', low) and any(k in low for k in ["dept", "department", "قسم", "in hr", "for hr"]):
        dept = "HR"

    # 3. Extract Overtime Type
    ot_type = "Night Overtime (1.50x)" if any(k in low for k in ["night", "evening", "1.5", "ليل", "مسائ"]) else "Day Overtime (1.25x)"

    # 4. Extract Numbers for Headcount and Hours
    headcount = 2
    hours = 4.0
    hc_match = re.search(r'(\d+)\s*(?:worker|workers|wnat|staff|emp|employee|employees|people|guys|person|عمال|عامل|موظف|موظفين|اشخاص)', low)
    if hc_match:
        headcount = max(1, int(hc_match.group(1)))

    hr_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:hour|hours|hrs|hr|h|ov|ot|ساعة|ساعات|ساعه)', low)
    if hr_match:
        hours = max(0.5, float(hr_match.group(1)))
    else:
        nums = re.findall(r'\b\d+(?:\.\d+)?\b', low)
        filtered_nums = [float(n) for n in nums if not (201 <= float(n) <= 220)]
        if len(filtered_nums) >= 2:
            headcount = int(filtered_nums[0])
            hours = float(filtered_nums[1])
        elif len(filtered_nums) == 1:
            hours = float(filtered_nums[0])

    # 5. Classify Intent Broadly
    ot_keywords = ["ot", "ov", "overtime", "over time", "extra", "shift", "worker", "wnat", "want", "need", "dispatch", "ساعات", "اضافي", "إضافي", "اوفر", "عمال", "موظفين", "محتاج", "ابي", "اريد"]
    audit_keywords = ["audit", "budget", "all", "company", "workforce", "department", "summary", "total cost", "highest", "average", "ميزانية", "الشركة", "الاقسام", "تدقيق", "ملخص"]
    statement_keywords = ["statement", "reward", "salary", "pay", "pension", "spf", "retire", "كشف", "راتب", "مكافآت", "تقاعد", "حماية"]

    if any(k in low for k in ot_keywords):
        if active_role == "Employee" and not any(k in low for k in ["worker", "staff", "dispatch", "عمال", "موظفين"]):
            return {
                "intent": "request_ot",
                "emp_id": active_emp_id,
                "department": dept,
                "headcount": 1,
                "hours": hours,
                "ot_type": ot_type,
                "reason": text,
                "reply": f"Understood! I have submitted your extra-time request for **{hours} hrs ({ot_type})** to HR for approval."
            }
        else:
            return {
                "intent": "dispatch_ot",
                "emp_id": extracted_emp,
                "department": dept,
                "headcount": headcount,
                "hours": hours,
                "ot_type": ot_type,
                "reply": f"Action executed! Dispatched an extra-time campaign for **{headcount} worker(s)** for **{hours} hrs ({ot_type})** in **{dept}**."
            }

    if emp_match or any(k in low for k in statement_keywords):
        return {
            "intent": "employee_statement",
            "emp_id": extracted_emp,
            "reply": f"Here is the full 12-month Total Rewards & Omani SPF Pension forecast for **{extracted_emp}**:"
        }

    if any(k in low for k in audit_keywords):
        return {
            "intent": "workforce_audit",
            "reply": "Here is the live organization-wide compensation budget and workforce compliance audit:"
        }

    # Dynamic Data Q&A Fallback
    top_emp = df.loc[df["BaseSalary_OMR"].idxmax()]
    avg_sal = df["BaseSalary_OMR"].mean()
    omani_cnt = (df["Nationality"].astype(str).str.lower() == "omani").sum()
    return {
        "intent": "general_qa",
        "reply": (
            f"I analyzed your query across our **{len(df)}-employee** workforce registry:\n"
            f"- **Average Monthly Base Salary:** OMR {avg_sal:,.2f}\n"
            f"- **Highest Base Earner:** {top_emp['Name']} ({top_emp['EmpID']}, {top_emp['Department']}) at OMR {top_emp['BaseSalary_OMR']:,.2f}/mo\n"
            f"- **Workforce Split:** {omani_cnt} Omani nationals (covered under 11% SPF Pension) and {len(df) - omani_cnt} Expatriates (EOSG).\n\n"
            f"You can also ask me to **dispatch overtime workers**, **generate any employee's rewards/pension statement**, or **audit department budgets**."
        )
    }

# ==============================================================================
# 5. SIDEBAR: AGENT CONTEXT SWITCHER & POLICY KNOWLEDGE BASE
# ==============================================================================
with st.sidebar:
    st.title("🤖 HR AI Agent Control")
    st.caption("MNGT3557 | Topic 8 Autonomous Agent")

    active_role = st.radio(
        "Active User Interacting with Agent:",
        ["🏢 HR Specialist", "👤 Employee"],
        index=0
    )
    role_key = "HR" if "HR" in active_role else "Employee"

    emp_options = [f"{r['EmpID']} - {r['Name']} ({r['Department']})" for _, r in df.iterrows()]
    active_emp_id = str(df.iloc[0]["EmpID"]).strip().upper()
    if role_key == "Employee" and emp_options:
        chosen = st.selectbox("Select Employee Context:", emp_options)
        active_emp_id = chosen.split(" - ")[0].strip().upper()

    if st.button("🔄 Sync Live Agent Memory", use_container_width=True):
        st.rerun()

    st.divider()
    st.subheader("⚖️ Omani Labour & SPF Rules")
    spf_rate = st.slider("Employer SPF Pension Share (%)", 5.0, 20.0, 11.0, 0.5) / 100.0
    st.caption("• Day Overtime: **1.25x** | Night OT: **1.50x**\n• Monthly Divisor: **240 hrs** | Retirement: **Age 60**")

    st.divider()
    st.subheader("📜 Live Agent Reasoning Log")
    for item in shared_store["agent_reasoning_log"][:5]:
        st.caption(item)

# ==============================================================================
# 6. MAIN AGENT WORKSPACE (PROACTIVE ALERTS + CONVERSATIONAL AGENT)
# ==============================================================================
st.title("🤖 Autonomous Total Rewards & Extra-Time AI Agent")
st.caption(f"Active Session Context: **{active_role}** {f'({active_emp_id})' if role_key == 'Employee' else '(Organization Command Mode)'}")

# Proactive Agent Notifications (Human-in-the-Loop Action Cards)
if role_key == "Employee":
    emp_matches = df[df["EmpID"].astype(str).str.upper() == active_emp_id]
    if not emp_matches.empty:
        emp_row = emp_matches.iloc[0]
        emp_dept = str(emp_row["Department"]).strip()
        offers = [
            c for c in shared_store["hr_ot_campaigns"]
            if (c["department"].lower() == emp_dept.lower() or c["department"] == "All Departments")
            and active_emp_id not in c["accepted_by"]
            and active_emp_id not in c["declined_by"]
            and (c["headcount_needed"] - len(c["accepted_by"])) > 0
        ]
        if offers:
            st.warning(f"🔔 **Proactive Agent Alert:** You have **{len(offers)}** extra-time shift invitation(s) from HR!")
            for camp in offers:
                with st.container(border=True):
                    c1, c2 = st.columns([2.5, 1])
                    c1.markdown(f"**Campaign #{camp['id']}** — **{camp['hours']} hrs** ({camp['ot_type']}) | Dept: **{camp['department']}** | Spots left: **{camp['headcount_needed'] - len(camp['accepted_by'])}**")
                    with c2:
                        b1, b2 = st.columns(2)
                        if b1.button("✅ Accept", key=f"acc_{camp['id']}_{active_emp_id}", type="primary"):
                            camp["accepted_by"].append(active_emp_id)
                            shared_store["approved_ot_ledger"].setdefault(active_emp_id, {"day": 0.0, "night": 0.0})
                            if "Day" in camp["ot_type"]:
                                shared_store["approved_ot_ledger"][active_emp_id]["day"] += float(camp["hours"])
                            else:
                                shared_store["approved_ot_ledger"][active_emp_id]["night"] += float(camp["hours"])
                            log_agent_action(f"{active_emp_id} accepted Campaign #{camp['id']} ({camp['hours']}h). Attendance verified & December payroll updated.")
                            st.rerun()
                        if b2.button("❌ Decline", key=f"dec_{camp['id']}_{active_emp_id}"):
                            camp["declined_by"].append(active_emp_id)
                            log_agent_action(f"{active_emp_id} declined Campaign #{camp['id']}.")
                            st.rerun()

elif role_key == "HR":
    pending_reqs = [r for r in shared_store["emp_ot_requests"] if r["status"] == "Pending HR Review"]
    if pending_reqs:
        st.info(f"🔔 **Human-in-the-Loop Queue:** **{len(pending_reqs)}** employee extra-time request(s) awaiting your approval.")
        for req in pending_reqs:
            with st.container(border=True):
                c1, c2 = st.columns([2.5, 1])
                c1.markdown(f"**{req['req_id']}** — **{req['emp_name']} ({req['emp_id']})** requested **{req['hours']} hrs** ({req['ot_type']}) | Reason: *{req['reason']}*")
                with c2:
                    b1, b2 = st.columns(2)
                    if b1.button("✅ Approve", key=f"app_{req['req_id']}", type="primary"):
                        req["status"] = "Approved & Paid"
                        eid = req["emp_id"]
                        shared_store["approved_ot_ledger"].setdefault(eid, {"day": 0.0, "night": 0.0})
                        if "Day" in req["ot_type"]:
                            shared_store["approved_ot_ledger"][eid]["day"] += float(req["hours"])
                        else:
                            shared_store["approved_ot_ledger"][eid]["night"] += float(req["hours"])
                        log_agent_action(f"HR approved {req['req_id']} for {eid} ({req['hours']}h). December payroll & budget updated.")
                        st.rerun()
                    if b2.button("❌ Reject", key=f"rej_{req['req_id']}"):
                        req["status"] = "Rejected"
                        log_agent_action(f"HR rejected {req['req_id']} for {req['emp_id']}.")
                        st.rerun()

# Initialize Chat History
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {
            "role": "assistant",
            "content": "Hello! I am your **Autonomous Total Rewards & Extra-Time AI Agent**. Tell me what you need in natural language (English or Arabic)—for example:\n- *\"I need 4 workers for 3 hours overtime in Operations\"*\n- *\"Show total rewards and SPF pension forecast for EMP201\"*\n- *\"Audit full company compensation budget\"*",
            "action": None
        }
    ]

# Quick One-Click Prompts for Live Demonstration
st.markdown("###### ⚡ Quick Agent Commands:")
q1, q2, q3, q4 = st.columns(4)
quick_prompt = None
if q1.button("📄 EMP201 Rewards & Pension", use_container_width=True):
    quick_prompt = "Generate total rewards and SPF pension statement for EMP201"
if q2.button("📢 Dispatch 4 Workers (3h OT)", use_container_width=True):
    quick_prompt = "I want 4 workers for 3 hours overtime"
if q3.button("🙋‍♂️ Request 4h Night OT", use_container_width=True):
    quick_prompt = "I want to request 4 hours night overtime for urgent month-end closing"
if q4.button("📊 Audit Company Budget", use_container_width=True):
    quick_prompt = "Audit full workforce compensation budget and compliance"

# Render Chat History
for idx, msg in enumerate(st.session_state.chat_history):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        act = msg.get("action")
        if act:
            if act["intent"] == "employee_statement":
                render_employee_statement_card(act["emp_id"], spf_rate=spf_rate, unique_key=str(idx))
            elif act["intent"] == "workforce_audit":
                render_workforce_audit_card(spf_rate=spf_rate)
            elif act["intent"] == "dispatch_ot":
                if shared_store["hr_ot_campaigns"]:
                    latest = shared_store["hr_ot_campaigns"][0]
                    st.success(f"📡 **Active Campaign #{latest['id']}** | Target: **{latest['department']}** | Needed: **{latest['headcount_needed']} staff** | Hours: **{latest['hours']}h ({latest['ot_type']})** | Accepted: **{len(latest['accepted_by'])}/{latest['headcount_needed']}**")

# Chat Input
user_input = st.chat_input("Ask the AI Agent anything (e.g., 'I want 4 workers for 3 hours ov', 'EMP205 statement', 'كم راتب EMP201')...")
final_prompt = quick_prompt or user_input

if final_prompt:
    st.session_state.chat_history.append({"role": "user", "content": final_prompt, "action": None})
    with st.chat_message("user"):
        st.markdown(final_prompt)

    with st.chat_message("assistant"):
        with st.status("🧠 Agent Reasoning & Executing Workflow...", expanded=False) as status:
            st.write("1. Parsing natural language intent & extracting parameters...")
            result = parse_agent_command(final_prompt, role_key, active_emp_id)
            st.write(f"2. Intent identified: `{result['intent']}` — Applying Omani Labour & SPF rules...")

            if result["intent"] == "dispatch_ot":
                new_camp = {
                    "id": f"OT-{len(shared_store['hr_ot_campaigns']) + 501}",
                    "department": result.get("department", "All Departments"),
                    "headcount_needed": int(result.get("headcount", 2)),
                    "hours": float(result.get("hours", 4.0)),
                    "ot_type": result.get("ot_type", "Day Overtime (1.25x)"),
                    "accepted_by": [],
                    "declined_by": []
                }
                shared_store["hr_ot_campaigns"].insert(0, new_camp)
                log_agent_action(f"Dispatched Campaign #{new_camp['id']} ({new_camp['headcount_needed']} staff, {new_camp['hours']}h) to {new_camp['department']}.")
                st.write(f"3. Campaign #{new_camp['id']} dispatched to target employee inboxes.")

            elif result["intent"] == "request_ot":
                emp_row = df[df["EmpID"].astype(str).str.upper() == active_emp_id].iloc[0]
                new_req = {
                    "req_id": f"REQ-{len(shared_store['emp_ot_requests']) + 101}",
                    "emp_id": active_emp_id,
                    "emp_name": emp_row["Name"],
                    "department": emp_row["Department"],
                    "hours": float(result.get("hours", 4.0)),
                    "ot_type": result.get("ot_type", "Day Overtime (1.25x)"),
                    "reason": result.get("reason", final_prompt),
                    "status": "Pending HR Review"
                }
                shared_store["emp_ot_requests"].insert(0, new_req)
                log_agent_action(f"Employee {active_emp_id} submitted {new_req['req_id']} ({new_req['hours']}h) to HR queue.")
                st.write(f"3. Request {new_req['req_id']} queued for HR approval.")

            status.update(label="✅ Agent Execution Complete", state="complete", expanded=False)

        st.markdown(result["reply"])
        if result["intent"] == "employee_statement":
            render_employee_statement_card(result["emp_id"], spf_rate=spf_rate, unique_key=str(len(st.session_state.chat_history)))
        elif result["intent"] == "workforce_audit":
            render_workforce_audit_card(spf_rate=spf_rate)
        elif result["intent"] == "dispatch_ot" and shared_store["hr_ot_campaigns"]:
            latest = shared_store["hr_ot_campaigns"][0]
            st.success(f"📡 **Active Campaign #{latest['id']}** | Target: **{latest['department']}** | Needed: **{latest['headcount_needed']} staff** | Hours: **{latest['hours']}h ({latest['ot_type']})** | Accepted: **{len(latest['accepted_by'])}/{latest['headcount_needed']}**")

    st.session_state.chat_history.append({
        "role": "assistant",
        "content": result["reply"],
        "action": result
    })
