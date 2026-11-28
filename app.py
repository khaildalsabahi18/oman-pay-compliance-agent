import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import re
from datetime import datetime

st.set_page_config(page_title="Autonomous HR Rewards & Extra-Time Agent", page_icon="🤖", layout="wide")

# ==============================================================================
# 1. LOAD DATASET
# ==============================================================================
@st.cache_data
def load_data():
    try:
        return pd.read_csv("dataset.csv")
    except Exception:
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.error("⚠️ 'dataset.csv' was not found in the repository. Please upload 'dataset.csv'.")
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
    np.random.seed(int("".join([str(ord(c)) for c in emp_id])) % 100000)

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

    # 12-Month Table with Grey December
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

    # Pension Forecast Section
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
# 4. FLEXIBLE HYBRID INTENT & ENTITY PARSER (NO RIGID LIMITS)
# ==============================================================================
def parse_agent_command(prompt_text, active_role, active_emp_id, api_key=""):
    text = prompt_text.strip()
    low = text.lower()

    # Optional Mode A: Real Gemini LLM Reasoning if API Key provided
    if api_key.strip():
        try:
            from google import genai
            client = genai.Client(api_key=api_key.strip())
            sys_prompt = (
                f"You are an autonomous HR Total Rewards & Extra-Time AI Agent. Active user role: {active_role} (ID: {active_emp_id}). "
                f"Dataset has employees EMP201..EMP220 across Operations, IT, Finance, HR, Logistics. "
                f"Extract JSON with keys: intent (one of: 'dispatch_ot', 'request_ot', 'employee_statement', 'workforce_audit', 'general_qa'), "
                f"emp_id (e.g. 'EMP201' or ''), department (e.g. 'Operations' or 'All Departments'), headcount (int, default 2), "
                f"hours (float, default 4.0), ot_type ('Day Overtime (1.25x)' or 'Night Overtime (1.50x)'), reply (helpful short response)."
            )
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"{sys_prompt}\nUser message: {text}",
                config={"response_mime_type": "application/json"}
            )
            parsed = json.loads(resp.text)
            return parsed
        except Exception:
            pass  # Gracefully fall back to ultra-flexible local fuzzy parser

    # Mode B: Ultra-Flexible Fuzzy & Regex Parser (Handles typos, abbreviations, Arabic & English)
    # 1. Extract Employee ID if mentioned (e.g., EMP201, emp 205, 201)
    emp_match = re.search(r'\b(?:emp\s*)?(20\d|21\d|220)\b', low)
    extracted_emp = f"EMP{emp_match.group(1)}" if emp_match else (active_emp_id if active_role == "Employee" else "EMP201")

    # 2. Extract Department (with fuzzy matching)
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

    # Dynamic Data Q&A Fallback (Never gives a dead-end "I don't understand" error)
    top_emp = df.loc[df["BaseSalary_OMR"].idxmax()]
    avg_sal = df["BaseSalary_OMR"].mean()
    omani_cnt = (df["Nationality"].str.lower() == "omani").sum()
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

    active_emp_id = "EMP201"
    if role_key == "Employee":
        emp_list = df.apply(lambda r: f"{r['EmpID']} - {r['Name']} ({r['Department']})", axis=1).tolist()
        chosen = st.selectbox("Select Employee Context:", emp_list)
        active_emp_id = chosen.split(" - ")[0].strip().upper()

    if st.button("🔄 Sync Live Agent Memory", use_container_width=True):
        st.rerun()
