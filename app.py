from __future__ import annotations

import json
import os
import re
import tempfile
import threading
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="PeopleOps Agent Workspace",
    page_icon="✳️",
    layout="wide",
    initial_sidebar_state="expanded",
)

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "dataset.csv"
STATE_FILE = ROOT / "agent_shared_state.json"
MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
REQUIRED_COLUMNS = [
    "EmpID", "Name", "Department", "Grade", "BaseSalary_OMR", "Bonus_OMR",
    "HousingAllow_OMR", "TransportAllow_OMR", "HealthCover_OMR",
    "PensionContrib_OMR", "FlightTickets_OMR", "WellnessPerks_OMR",
    "Nationality", "Age", "YearsOfService",
]
DEPARTMENT_ALIASES = {
    "Operations": ("operations", "العمليات"),
    "IT": ("it", "information technology", "تقنية المعلومات", "تكنولوجيا المعلومات"),
    "Finance": ("finance", "المالية", "الشؤون المالية"),
    "HR": ("hr", "human resources", "الموارد البشرية"),
    "Logistics": ("logistics", "اللوجستيات", "الخدمات اللوجستية"),
}


@st.cache_data
def load_employees() -> pd.DataFrame:
    employees = pd.read_csv(DATA_FILE)
    if list(employees.columns) != REQUIRED_COLUMNS:
        raise ValueError("dataset.csv does not match the required employee schema.")
    if len(employees) != 20 or employees["EmpID"].nunique() != 20:
        raise ValueError("dataset.csv must contain 20 unique employee records.")
    return employees


def new_shared_state() -> dict:
    return {
        "hr_ot_campaigns": [],
        "emp_ot_requests": [],
        "approved_ot_ledger": {},
        "agent_reasoning_log": [],
    }


@st.cache_resource
def get_shared_resources() -> tuple[dict, threading.RLock]:
    state = new_shared_state()
    if STATE_FILE.exists():
        with STATE_FILE.open("r", encoding="utf-8") as state_file:
            loaded = json.load(state_file)
        if not isinstance(loaded, dict):
            raise ValueError("agent_shared_state.json must contain a JSON object.")
        for key, default in new_shared_state().items():
            state[key] = loaded.get(key, default)
        # Migrate the earlier prototype's activity trace without discarding it.
        old_trace = loaded.get("agent_activity_log", [])
        if not state["agent_reasoning_log"] and old_trace:
            state["agent_reasoning_log"] = [
                {"timestamp": "", "action": item, "steps": []}
                for item in old_trace
            ]
    return state, threading.RLock()


employees = load_employees()
shared_state, state_lock = get_shared_resources()


def persist_shared_state() -> None:
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=ROOT,
            prefix=".agent_state_",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            json.dump(shared_state, temp_file, ensure_ascii=False, indent=2)
            temp_path = Path(temp_file.name)
        os.replace(temp_path, STATE_FILE)
    except Exception:
        if temp_path and temp_path.exists():
            temp_path.unlink()
        raise


def log_action(action: str, steps: list[str]) -> None:
    entry = {
        "timestamp": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
        "action": action,
        "steps": steps,
    }
    with state_lock:
        shared_state["agent_reasoning_log"].insert(0, entry)
        del shared_state["agent_reasoning_log"][100:]
        persist_shared_state()


def money(value: float) -> str:
    return f"OMR {value:,.2f}"


def employee_by_id(emp_id: str) -> pd.Series:
    matched = employees.loc[employees["EmpID"] == emp_id]
    if matched.empty:
        raise ValueError(f"Unknown employee ID: {emp_id}")
    return matched.iloc[0]


def parse_hours(text: str, default: float = 4.0) -> float:
    match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h\b|ساعات|ساعة)",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return default
    return min(40.0, max(1.0, float(match.group(1))))


def requested_overtime_type(text: str) -> str:
    if any(word in text.lower() for word in ("night", "ليل", "مساء")):
        return "Night"
    return "Day"


def find_department(text: str) -> str | None:
    lowered = text.casefold()
    for department in employees["Department"].unique():
        aliases = DEPARTMENT_ALIASES.get(str(department), (str(department).casefold(),))
        for alias in aliases:
            if re.search(r"(?<!\w)" + re.escape(alias.casefold()) + r"(?!\w)", lowered):
                return str(department)
    return None


def compute_monthly_history(emp: pd.Series, spf_rate: float) -> pd.DataFrame:
    emp_id = str(emp["EmpID"])
    base = float(emp["BaseSalary_OMR"])
    allowance = float(emp["HousingAllow_OMR"] + emp["TransportAllow_OMR"])
    health = float(emp["HealthCover_OMR"])
    perks = float(emp["FlightTickets_OMR"] + emp["WellnessPerks_OMR"])
    is_omani = emp["Nationality"] == "Omani"
    employer_spf = base * spf_rate if is_omani else 0.0
    ledger = shared_state["approved_ot_ledger"].get(emp_id, {"day": 0.0, "night": 0.0})
    rng = np.random.default_rng(sum(ord(char) for char in emp_id))
    rows = []

    for index, month in enumerate(MONTHS):
        if index == 11:
            day_hours = float(ledger.get("day", 0.0))
            night_hours = float(ledger.get("night", 0.0))
            bonus = float(emp["Bonus_OMR"]) * 1.5
        else:
            day_hours = float(rng.choice([0, 5, 8, 12, 16], p=[0.2, 0.3, 0.25, 0.15, 0.1]))
            night_hours = float(rng.choice([0, 4, 8], p=[0.6, 0.3, 0.1]))
            bonus = float(emp["Bonus_OMR"])
            if month == "June":
                bonus *= 1.5
            elif month in ("July", "August"):
                bonus *= 0.5

        hourly = base / 240.0
        ot_pay = day_hours * hourly * 1.25 + night_hours * hourly * 1.5
        cash_pay = base + bonus + allowance + ot_pay
        rewards = cash_pay + employer_spf + health + perks
        rows.append({
            "Month": month,
            "Base_Salary": base,
            "Day_OT_Hrs": day_hours,
            "Night_OT_Hrs": night_hours,
            "OT_Pay": ot_pay,
            "Incentive_Bonus": bonus,
            "Cash_Allowances": allowance,
            "SPF_Pension": employer_spf,
            "Health_Insurance": health,
            "Perks_Subsidies": perks,
            "Net_Cash_Pay": cash_pay,
            "Total_Rewards_Value": rewards,
        })
    return pd.DataFrame(rows)


def pension_summary(emp: pd.Series, spf_rate: float) -> dict:
    base = float(emp["BaseSalary_OMR"])
    service = int(emp["YearsOfService"])
    age = int(emp["Age"])
    if emp["Nationality"] != "Omani":
        return {
            "nationality": "Expatriate",
            "note": (
                "This employee is not included in the Omani SPF forecast. "
                "End-of-Service Gratuity (EOSG) is shown as the applicable "
                "statutory benefit; confirm the employee's contract and current "
                "law for an individual entitlement calculation."
            ),
        }
    remaining = max(0, 60 - age)
    projected_years = service + remaining
    accrual = min(0.80, projected_years * 0.02)
    employee_paid = base * 0.075 * 12 * service
    employer_paid = base * spf_rate * 12 * service
    return {
        "nationality": "Omani",
        "age": age,
        "service": service,
        "remaining": remaining,
        "employee_paid": employee_paid,
        "employer_paid": employer_paid,
        "accumulated": employee_paid + employer_paid,
        "accrual": accrual,
        "monthly_pension": base * accrual,
        "spf_rate": spf_rate,
    }


def render_rewards(emp: pd.Series, spf_rate: float) -> None:
    history = compute_monthly_history(emp, spf_rate)
    annual_base = float(history["Base_Salary"].sum())
    annual_ot = float(history["OT_Pay"].sum())
    annual_rewards = float(history["Total_Rewards_Value"].sum())
    multiplier = annual_rewards / annual_base if annual_base else 0

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Annual Base", money(annual_base))
    k2.metric("Annual OT", money(annual_ot))
    k3.metric("Total Rewards Value", money(annual_rewards))
    k4.metric("Package Multiplier", f"{multiplier:.2f}×")

    st.markdown("#### 12-month rewards breakdown")
    st.caption("December is the current payroll month; approved agent OT appears in its row.")
    styled = history.style.apply(
        lambda row: [
            "background-color: #6c757d; color: #ffffff; font-weight: bold;"
            if row["Month"] == "December" else ""
            for _ in row
        ],
        axis=1,
    )
    st.dataframe(styled, width="stretch", hide_index=True)

    st.markdown("#### Rewards trend")
    st.line_chart(history.set_index("Month")[["Net_Cash_Pay", "Total_Rewards_Value"]])

    pension = pension_summary(emp, spf_rate)
    st.markdown("#### Pension and retirement forecast")
    if pension["nationality"] == "Omani":
        pension_table = pd.DataFrame([
            ["Employee", f"{emp['Name']} ({emp['EmpID']})"],
            ["Current age / retirement age", f"{pension['age']} / 60 years"],
            ["Completed / remaining service", f"{pension['service']} / {pension['remaining']} years"],
            ["Employee cumulative contributions (7.5%)", money(pension["employee_paid"])],
            [f"Employer cumulative contributions ({pension['spf_rate']:.1%})", money(pension["employer_paid"])],
            ["Illustrative total contributions", money(pension["accumulated"])],
            ["Projected monthly pension", money(pension["monthly_pension"])],
            ["Projected accrual", f"{pension['accrual']:.0%} of current base (80% cap)"],
        ], columns=["Parameter", "Forecast"])
        st.dataframe(pension_table, width="stretch", hide_index=True)
    else:
        st.info(pension["note"])

    base_share = annual_base / annual_rewards * 100 if annual_rewards else 0
    statement = (
        f"TOTAL REWARDS STATEMENT — {emp['Name']} ({emp['EmpID']})\n"
        f"Department: {emp['Department']} | Grade: {emp['Grade']} | "
        f"Nationality: {emp['Nationality']}\n\n"
        f"Annual base salary: {money(annual_base)}\n"
        f"Annual overtime: {money(annual_ot)}\n"
        f"Annual performance bonuses: {money(float(history['Incentive_Bonus'].sum()))}\n"
        f"Housing and transport allowances: {money(float(history['Cash_Allowances'].sum()))}\n"
        f"Employer SPF contributions: {money(float(history['SPF_Pension'].sum()))}\n"
        f"Healthcare coverage: {money(float(history['Health_Insurance'].sum()))}\n"
        f"Perks and flight benefits: {money(float(history['Perks_Subsidies'].sum()))}\n"
        f"Total rewards value: {money(annual_rewards)}\n"
        f"Package multiplier: {multiplier:.2f}x base\n"
        f"Base salary share of total rewards: {base_share:.1f}%\n"
    )
    st.download_button(
        "Download statement (.txt)",
        data=statement,
        file_name=f"Total_Rewards_{emp['EmpID']}.txt",
        mime="text/plain",
        key=f"statement_download_{emp['EmpID']}",
    )


def build_audit(spf_rate: float, department: str | None = None) -> tuple[pd.DataFrame, dict]:
    selected = employees if department is None else employees.loc[employees["Department"] == department]
    records = selected.copy()
    annual_costs = []
    ot_costs = []
    for _, emp in records.iterrows():
        base = float(emp["BaseSalary_OMR"])
        ledger = shared_state["approved_ot_ledger"].get(
            str(emp["EmpID"]), {"day": 0.0, "night": 0.0}
        )
        ot_cost = (
            float(ledger.get("day", 0.0)) * base / 240 * 1.25
            + float(ledger.get("night", 0.0)) * base / 240 * 1.50
        )
        monthly_package = (
            base + float(emp["Bonus_OMR"]) + float(emp["HousingAllow_OMR"])
            + float(emp["TransportAllow_OMR"]) + float(emp["HealthCover_OMR"])
            + float(emp["FlightTickets_OMR"]) + float(emp["WellnessPerks_OMR"])
            + (base * spf_rate if emp["Nationality"] == "Omani" else 0.0)
        )
        annual_costs.append(monthly_package * 12 + ot_cost)
        ot_costs.append(ot_cost)
    records["Agent_Approved_OT_OMR"] = ot_costs
    records["Estimated_Annual_Rewards_OMR"] = annual_costs
    metrics = {
        "headcount": len(records),
        "annual_budget": float(records["Estimated_Annual_Rewards_OMR"].sum()),
        "december_ot": float(records["Agent_Approved_OT_OMR"].sum()),
        "omani_share": (
            float((records["Nationality"] == "Omani").mean() * 100)
            if len(records) else 0.0
        ),
    }
    return records, metrics


def render_audit(spf_rate: float, department: str | None = None) -> None:
    registry, metrics = build_audit(spf_rate, department)
    scope = department or "Entire organization"
    st.markdown(f"#### Workforce budget and compliance snapshot — {scope}")
    a, b, c, d = st.columns(4)
    a.metric("Headcount", metrics["headcount"])
    b.metric("Estimated annual rewards", money(metrics["annual_budget"]))
    c.metric("Approved December OT", money(metrics["december_ot"]))
    d.metric("Omani workforce", f"{metrics['omani_share']:.0f}%")
    st.caption(
        "Planning estimate annualizes the monthly dataset package and adds approved December OT. "
        "SPF and overtime rates follow the adjustable course-project assumptions."
    )
    if registry.empty:
        st.warning("No employees match this department.")
        return
    st.markdown("#### Departmental cost")
    dept_cost = registry.groupby("Department", as_index=False)[
        "Estimated_Annual_Rewards_OMR"
    ].sum()
    st.bar_chart(dept_cost.set_index("Department"))
    st.markdown("#### Workforce registry")
    st.dataframe(registry, width="stretch", hide_index=True)


def create_campaign(text: str, spf_rate: float) -> tuple[str, list[str], dict]:
    hours = parse_hours(text, default=6.0)
    count_match = re.search(
        r"(\d+)\s*(?:staff|employees?|workers?|people|موظفين|عامل)",
        text,
        flags=re.IGNORECASE,
    )
    headcount = max(1, int(count_match.group(1))) if count_match else 1
    department = find_department(text)
    department_label = department or "All Departments"
    eligible = employees if department is None else employees.loc[
        employees["Department"] == department
    ]
    if headcount > len(eligible):
        raise ValueError(
            f"{department_label} has only {len(eligible)} eligible employees in this demo dataset."
        )
    ot_type = requested_overtime_type(text)
    with state_lock:
        campaign_number = max(
            [int(re.sub(r"\D", "", item.get("id", "OT500"))) for item in shared_state["hr_ot_campaigns"]]
            or [500]
        ) + 1
        campaign = {
            "id": f"OT-{campaign_number}",
            "title": f"{department_label} {ot_type.lower()} overtime coverage",
            "department": department_label,
            "headcount_needed": headcount,
            "hours": hours,
            "ot_type": ot_type,
            "notified_emps": eligible["EmpID"].astype(str).tolist(),
            "accepted_by": [],
            "declined_by": [],
            "created_at": datetime.now().astimezone().isoformat(timespec="minutes"),
        }
        shared_state["hr_ot_campaigns"].insert(0, campaign)
        persist_shared_state()
    steps = [
        "Parsed HR dispatch intent, target department, headcount, duration, and shift.",
        f"Queried dataset.csv; identified {len(eligible)} eligible employee inboxes.",
        f"Applied the {1.25 if ot_type == 'Day' else 1.50:.2f}x {ot_type.lower()} overtime assumption and 240-hour divisor.",
        f"Created {campaign['id']} and published the offer to the shared employee inboxes.",
    ]
    log_action(f"Dispatched {campaign['id']} to {department_label}: {headcount} staff × {hours:g}h {ot_type}.", steps)
    response = (
        f"Campaign **{campaign['id']}** is live: {headcount} {department_label} "
        f"employee(s) invited for {hours:g} hours of {ot_type.lower()} overtime. "
        "The offers are now available in the employee inbox below."
    )
    return response, steps, {"type": "campaign", "id": campaign["id"]}


def submit_employee_request(emp_id: str, text: str) -> tuple[str, list[str], dict]:
    emp = employee_by_id(emp_id)
    hours = parse_hours(text)
    ot_type = requested_overtime_type(text)
    request_text = re.sub(
        r"(?i)\b(?:request|submit|need|please|night|day|overtime|extra[\s-]?time|\d+(?:\.\d+)?\s*(?:hours?|hrs?|h))\b",
        "",
        text,
    ).strip(" .,:;-")
    with state_lock:
        request_number = max(
            [int(re.sub(r"\D", "", item.get("req_id", "REQ100"))) for item in shared_state["emp_ot_requests"]]
            or [100]
        ) + 1
        request = {
            "req_id": f"REQ-{request_number}",
            "emp_id": emp_id,
            "emp_name": str(emp["Name"]),
            "department": str(emp["Department"]),
            "hours": hours,
            "ot_type": ot_type,
            "reason": request_text or "Operational task completion",
            "status": "Pending HR Review",
            "timestamp": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M"),
        }
        shared_state["emp_ot_requests"].insert(0, request)
        persist_shared_state()
    steps = [
        f"Recognized an employee overtime request from {emp_id}.",
        f"Queried the employee record and identified {emp['Department']} as the department.",
        f"Applied the {1.25 if ot_type == 'Day' else 1.50:.2f}x {ot_type.lower()} overtime assumption.",
        f"Created {request['req_id']} in the shared HR approval queue; payroll is unchanged until approval.",
    ]
    log_action(f"{emp_id} submitted {hours:g}h {ot_type.lower()} OT request {request['req_id']}.", steps)
    return (
        f"Request **{request['req_id']}** for {hours:g} hours of {ot_type.lower()} overtime "
        "has been sent to HR for review. No payroll entry is made before approval.",
        steps,
        {"type": "request", "id": request["req_id"]},
    )


def process_prompt(text: str, role: str, active_emp_id: str, spf_rate: float) -> tuple[str, list[str], dict | None]:
    lowered = text.casefold()
    emp_match = re.search(r"\bEMP(?:20)?\d{1,3}\b", text, flags=re.IGNORECASE)
    target_emp_id = emp_match.group(0).upper() if emp_match else ""
    if target_emp_id.startswith("EMP") and len(target_emp_id) < 6:
        target_emp_id = "EMP" + target_emp_id[3:].zfill(3)

    is_request = any(token in lowered for token in (
        "request", "submit", "ask for", "extra time", "overtime request",
        "أطلب", "اطلب", "طلب", "ساعات إضافية", "وقت إضافي",
    ))
    is_dispatch = any(token in lowered for token in (
        "dispatch", "recruit", "need ", "staff for", "offer", "campaign",
        "أرسل", "ارسل", "نحتاج", "مطلوب", "دوام إضافي",
    ))
    is_audit = any(token in lowered for token in (
        "audit", "budget", "compliance", "workforce", "department summary",
        "ميزانية", "تدقيق", "امتثال", "ملخص القسم",
    ))
    is_rewards = any(token in lowered for token in (
        "reward", "statement", "pension", "salary", "benefit", "package",
        "مزايا", "مكافآت", "راتب", "معاش", "بيان",
    ))

    if role == "Employee" and is_request:
        response, steps, output = submit_employee_request(active_emp_id, text)
        return response, steps, output
    if role == "HR" and is_dispatch:
        response, steps, output = create_campaign(text, spf_rate)
        return response, steps, output
    if is_audit:
        department = find_department(text)
        steps = [
            "Parsed workforce budget/compliance audit intent and optional department scope.",
            f"Queried {len(employees)} employee records and the approved overtime ledger.",
            f"Applied the {spf_rate:.1%} employer SPF assumption and shift overtime multipliers.",
            "Calculated workforce KPIs and prepared the registry and departmental cost visualization.",
        ]
        log_action(
            f"Generated workforce audit for {department or 'all departments'}.", steps
        )
        return (
            f"Here is the {'department' if department else 'organization-wide'} budget and compliance snapshot.",
            steps,
            {"type": "audit", "department": department},
        )
    if is_rewards or target_emp_id:
        target_emp_id = target_emp_id or active_emp_id
        if not target_emp_id:
            return (
                "Tell me which employee to analyze (for example, **EMP201**) or switch to an employee context.",
                ["Parsed a total rewards or pension request.", "No employee ID was provided, so no employee data was accessed."],
                None,
            )
        try:
            emp = employee_by_id(target_emp_id)
        except ValueError:
            return (
                f"I could not find **{target_emp_id}** in the workforce registry. Use an ID from EMP201–EMP220.",
                ["Parsed an employee-specific rewards request.", "Checked the dataset and found no matching employee record."],
                None,
            )
        steps = [
            f"Parsed the total rewards/pension request for {target_emp_id}.",
            "Queried dataset.csv and the December approved overtime ledger.",
            f"Applied the {spf_rate:.1%} employer SPF assumption, employee 7.5% rate, and the 240-hour overtime divisor.",
            "Generated the 12-month statement, pension/EOSG summary, trend chart, and downloadable text statement.",
        ]
        log_action(f"Generated total rewards and pension statement for {target_emp_id}.", steps)
        return (
            f"Total rewards analysis for **{emp['Name']} ({target_emp_id})** is ready.",
            steps,
            {"type": "rewards", "emp_id": target_emp_id},
        )
    if role == "Employee":
        return (
            "I can prepare your rewards statement or submit an extra-time request. Try “show my rewards” or “request 4 night overtime hours.”",
            ["Parsed the message in employee context.", "No supported rewards or overtime action was detected; shared memory was not changed."],
            None,
        )
    return (
        "I can generate an employee rewards statement, dispatch an overtime campaign, or audit the workforce. Try a suggested prompt below.",
        ["Parsed the HR message.", "No supported agent action was detected; shared memory was not changed."],
        None,
    )


def accept_offer(campaign: dict, emp_id: str) -> None:
    with state_lock:
        slots_left = int(campaign["headcount_needed"]) - len(campaign["accepted_by"])
        if emp_id in campaign["accepted_by"] or emp_id in campaign["declined_by"]:
            return
        if slots_left <= 0 or emp_id not in campaign["notified_emps"]:
            st.warning("This offer is no longer available.")
            return
        # Demo attendance verification is the explicit human-in-the-loop acceptance.
        campaign["accepted_by"].append(emp_id)
        entry = shared_state["approved_ot_ledger"].setdefault(
            emp_id, {"day": 0.0, "night": 0.0}
        )
        entry["day" if campaign["ot_type"] == "Day" else "night"] += float(campaign["hours"])
        persist_shared_state()
    steps = [
        f"Received {emp_id}'s acceptance for campaign {campaign['id']}.",
        "Verified that the employee was invited, the offer was not previously answered, and a slot remained.",
        "Recorded demo attendance confirmation and applied the applicable overtime multiplier.",
        f"Credited {campaign['hours']:g} {campaign['ot_type'].lower()} hours to December payroll and refreshed the HR budget.",
    ]
    log_action(
        f"{emp_id} accepted {campaign['id']}; attendance checked and December OT ledger updated.",
        steps,
    )
    st.rerun()


def respond_to_request(request: dict, approve: bool) -> None:
    with state_lock:
        if request["status"] != "Pending HR Review":
            return
        request["status"] = "Approved & Paid" if approve else "Rejected by HR"
        if approve:
            entry = shared_state["approved_ot_ledger"].setdefault(
                request["emp_id"], {"day": 0.0, "night": 0.0}
            )
            entry["day" if request["ot_type"] == "Day" else "night"] += float(request["hours"])
        persist_shared_state()
    steps = [
        f"Reviewed employee request {request['req_id']} from {request['emp_id']}.",
        "Checked request status to prevent duplicate execution.",
        "Applied the appropriate overtime multiplier and updated December payroll." if approve
        else "Rejected the request; no payroll or overtime ledger entry was created.",
        "Persisted the decision to shared agent memory and refreshed the HR budget.",
    ]
    log_action(
        f"{'Approved' if approve else 'Rejected'} {request['req_id']} for {request['emp_id']}.",
        steps,
    )
    st.rerun()


def render_agent_output(output: dict | None, spf_rate: float) -> None:
    if not output:
        return
    if output["type"] == "rewards":
        render_rewards(employee_by_id(output["emp_id"]), spf_rate)
    elif output["type"] == "audit":
        render_audit(spf_rate, output.get("department"))
    elif output["type"] == "campaign":
        st.caption(f"Campaign reference: {output['id']}")
    elif output["type"] == "request":
        st.caption(f"Request reference: {output['id']}")


st.markdown(
    """
    <style>
    .stApp { background: #f6f8fb; }
    [data-testid="stSidebar"] { background: #eef2f8; }
    .agent-kicker { color: #63718a; font-size: .82rem; letter-spacing: .08em; text-transform: uppercase; }
    .agent-title { font-size: 1.8rem; font-weight: 720; margin: .15rem 0 0; color: #18243a; }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### ✳️ Agent controls")
    role_choice = st.radio(
        "Active workspace context",
        ["🏢 HR Compensation Specialist", "👤 Employee (EMP201 - EMP220)"],
        key="active_context",
    )
    role = "HR" if role_choice.startswith("🏢") else "Employee"
    if role == "Employee":
        employee_options = employees["EmpID"].tolist()
        active_emp_id = st.selectbox(
            "Simulate employee",
            employee_options,
            format_func=lambda emp_id: (
                f"{emp_id} — {employees.loc[employees['EmpID'] == emp_id, 'Name'].iloc[0]}"
            ),
        )
    else:
        active_emp_id = ""

    st.markdown("#### Policy knowledge base")
    spf_rate = st.slider(
        "SPF employer rate (%)",
        min_value=5.0,
        max_value=20.0,
        value=11.0,
        step=0.5,
    ) / 100.0
    st.caption("Course-project policy assumptions")
    st.markdown("- Day overtime: **1.25×**")
    st.markdown("- Night overtime: **1.50×**")
    st.markdown("- Hourly divisor: **240 hrs/month**")

    st.divider()
    st.markdown("#### Live agent memory trace")
    recent_actions = shared_state["agent_reasoning_log"][:5]
    if recent_actions:
        for action in recent_actions:
            timestamp = action.get("timestamp", "")
            st.caption(f"{timestamp} · {action['action']}")
    else:
        st.caption("No agent actions yet. Your executed workflows will appear here.")


st.markdown('<div class="agent-kicker">MNGT3557 · Topic 8 · Total rewards + extra-time workflows</div>', unsafe_allow_html=True)
st.markdown('<div class="agent-title">PeopleOps Agent Workspace</div>', unsafe_allow_html=True)
st.caption("Chat with the HR agent. Every workflow updates shared memory and renders its output in the execution canvas.")

if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

suggestions = [
    "Generate total rewards and pension statement for EMP201",
    "Dispatch 6 hours day overtime for 2 staff in Operations",
    "Audit workforce budget and compliance",
    "Request 4 night overtime hours",
]
st.markdown("#### Suggested agent prompts")
suggestion_cols = st.columns(4)
selected_prompt = None
for index, (column, suggestion) in enumerate(zip(suggestion_cols, suggestions)):
    with column:
        if st.button(suggestion, key=f"suggested_prompt_{index}", width="stretch"):
            selected_prompt = suggestion

typed_prompt = st.chat_input("Message the agent… (English or Arabic)")
prompt = typed_prompt or selected_prompt
if prompt:
    st.session_state["chat_history"].append({"role": "user", "content": prompt})
    try:
        response, reasoning_steps, output = process_prompt(
            prompt, role, active_emp_id, spf_rate
        )
    except (ValueError, OSError, json.JSONDecodeError) as error:
        response = f"I couldn't complete that action: {error}"
        reasoning_steps = [
            "Parsed the request and began the workflow.",
            "A validation or persistence error prevented completion; no success was reported.",
        ]
        output = None
    st.session_state["chat_history"].append({
        "role": "assistant",
        "content": response,
        "steps": reasoning_steps,
        "output": output,
    })

for message_index, message in enumerate(st.session_state["chat_history"]):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            with st.status(
                "🧠 Agent Reasoning & Execution Steps",
                state="complete",
                expanded=False,
            ):
                for step_number, step in enumerate(message.get("steps", []), 1):
                    st.markdown(f"{step_number}. {step}")
            render_agent_output(message.get("output"), spf_rate)


st.divider()
if role == "Employee":
    emp = employee_by_id(active_emp_id)
    st.markdown(f"### 📥 Employee inbox · {emp['Name']} ({active_emp_id})")
    my_campaigns = [
        campaign for campaign in shared_state["hr_ot_campaigns"]
        if active_emp_id in campaign.get("notified_emps", [])
    ]
    pending_count = 0
    if not my_campaigns:
        st.info("No extra-time offers have been dispatched to this employee.")
    for campaign in my_campaigns:
        with st.container(border=True):
            accepted = active_emp_id in campaign["accepted_by"]
            declined = active_emp_id in campaign["declined_by"]
            slots = campaign["headcount_needed"] - len(campaign["accepted_by"])
            st.markdown(
                f"**{campaign['id']} · {campaign['title']}**  \n"
                f"{campaign['department']} · {campaign['hours']:g}h {campaign['ot_type'].lower()} "
                f"· {max(0, slots)} slot(s) remaining"
            )
            if accepted:
                st.success("Accepted — attendance verified and December OT ledger credited.")
            elif declined:
                st.warning("You declined this offer.")
            elif slots <= 0:
                st.caption("This campaign is filled.")
            else:
                pending_count += 1
                accept_col, decline_col = st.columns(2)
                if accept_col.button(
                    "✅ Accept Offer",
                    key=f"accept_{campaign['id']}_{active_emp_id}",
                    type="primary",
                ):
                    accept_offer(campaign, active_emp_id)
                if decline_col.button("❌ Decline", key=f"decline_{campaign['id']}_{active_emp_id}"):
                    with state_lock:
                        campaign["declined_by"].append(active_emp_id)
                        persist_shared_state()
                    steps = [
                        f"Received {active_emp_id}'s response to {campaign['id']}.",
                        "Verified that the employee had not previously responded.",
                        "Recorded the decline and notified the HR campaign queue.",
                    ]
                    log_action(f"{active_emp_id} declined {campaign['id']}.", steps)
                    st.rerun()
    if pending_count:
        st.caption(f"{pending_count} offer(s) awaiting your response.")

    st.markdown("### 📨 Your extra-time requests")
    own_requests = [
        request for request in shared_state["emp_ot_requests"]
        if request["emp_id"] == active_emp_id
    ]
    if own_requests:
        st.dataframe(pd.DataFrame(own_requests), width="stretch", hide_index=True)
    else:
        st.caption("No requests submitted yet. Use the chat prompt to submit one.")
else:
    st.markdown("### 🧭 HR approval queue")
    pending_requests = [
        request for request in shared_state["emp_ot_requests"]
        if request["status"] == "Pending HR Review"
    ]
    if not pending_requests:
        st.info("No employee overtime requests are waiting for approval.")
    for request in pending_requests:
        with st.container(border=True):
            st.markdown(
                f"**{request['req_id']} · {request['emp_name']} ({request['emp_id']})** — "
                f"{request['department']}"
            )
            st.write(
                f"{request['hours']:g}h {request['ot_type'].lower()} · "
                f"{request['timestamp']} · {request['reason']}"
            )
            approve_col, reject_col = st.columns(2)
            if approve_col.button(
                "✅ Approve & Execute",
                key=f"approve_{request['req_id']}",
                type="primary",
            ):
                respond_to_request(request, True)
            if reject_col.button("❌ Reject", key=f"reject_{request['req_id']}"):
                respond_to_request(request, False)

    st.markdown("### 📡 Active extra-time campaigns")
    if shared_state["hr_ot_campaigns"]:
        campaign_rows = []
        for campaign in shared_state["hr_ot_campaigns"]:
            campaign_rows.append({
                "Campaign": campaign["id"],
                "Department": campaign["department"],
                "Shift": campaign["ot_type"],
                "Hours": campaign["hours"],
                "Accepted": len(campaign["accepted_by"]),
                "Needed": campaign["headcount_needed"],
                "Accepted employees": ", ".join(campaign["accepted_by"]) or "Awaiting responses",
            })
        st.dataframe(pd.DataFrame(campaign_rows), width="stretch", hide_index=True)
    else:
        st.caption("No campaigns dispatched yet.")
