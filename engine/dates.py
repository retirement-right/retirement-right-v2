"""
Module 1 — Date Engine
Parses analysis date + retirement dates, calculates months remaining per person
per year, detects working/transition/retired phases, returns phase boundaries.

All functions are pure — no side effects, no global state.
"""
from datetime import date, datetime
from typing import Optional
import math


# ── Helpers ──────────────────────────────────────────────────────────────────

def parse_date(d: str) -> date:
    """Parse ISO date string to date object."""
    return datetime.strptime(d, "%Y-%m-%d").date()


def age_at_year_end(dob: date, year: int) -> int:
    """Age the person will be at Dec 31 of the given year."""
    return year - dob.year if dob.month == 1 and dob.day == 1 else year - dob.year


def age_at(dob: date, as_of: date) -> int:
    """Exact age on a given date."""
    years = as_of.year - dob.year
    if (as_of.month, as_of.day) < (dob.month, dob.day):
        years -= 1
    return years


def months_remaining_in_year(d: date) -> int:
    """
    Number of full months remaining in the calendar year from date d inclusive.
    July 12 → months Jul, Aug, Sep, Oct, Nov, Dec = 6 months.
    """
    return 12 - d.month + 1


def months_worked_in_year(retirement_date: date, year: int) -> int:
    """
    Months a person works in a given calendar year given their retirement date.
    Retirement date = first day NOT working.
    Jan 1 retirement → 0 months worked that year.
    Jul 1 retirement → 6 months worked (Jan–Jun).
    """
    if retirement_date.year > year:
        return 12  # fully working this year
    if retirement_date.year < year:
        return 0   # already retired
    # Retirement happens this year
    return retirement_date.month - 1  # months before retirement month


def estimate_retirement_date(dob: date, retirement_age: int) -> date:
    """
    Fallback when exact date unknown.
    Assumes retirement on birthday month of the retirement-age year.
    """
    ret_year = dob.year + retirement_age
    return date(ret_year, dob.month, 1)


# ── Phase detection ───────────────────────────────────────────────────────────

def get_retirement_date(person: dict, dob: date) -> date:
    """
    Resolve retirement date from person dict.
    Uses exact date if date_known, else estimates from retirement_age + DOB.
    """
    ret = person.get("retirement", {})
    if ret.get("status") == "retired":
        # Already retired at analysis date — use analysis date as effective retirement
        # (they stopped working before the projection starts)
        return date(1900, 1, 1)  # sentinel: retired before any projection year

    if ret.get("date_known") and ret.get("date"):
        return parse_date(ret["date"])

    if ret.get("retirement_age"):
        return estimate_retirement_date(dob, ret["retirement_age"])

    # No retirement info — assume they work through projection
    return date(2099, 12, 31)


def detect_scenario(client_ret: date, spouse_ret: date) -> str:
    """
    A = same year retirement
    B = client retires first (or only client)
    C = spouse retires first
    """
    if spouse_ret.year == date(2099, 12, 31).year:
        return "B"  # no spouse
    if abs((client_ret - spouse_ret).days) < 32:
        return "A"
    if client_ret <= spouse_ret:
        return "B"
    return "C"


# ── Per-year phase info ───────────────────────────────────────────────────────

def year_phase(
    year: int,
    analysis_date: date,
    client_dob: date,
    client_ret: date,
    spouse_dob: Optional[date],
    spouse_ret: Optional[date],
) -> dict:
    """
    For a given projection year, return:
      - client_months_working: int 0-12
      - spouse_months_working: int 0-12
      - client_age:  age at Dec 31
      - spouse_age:  age at Dec 31 (or None)
      - phase_label: "both_working" | "client_only" | "spouse_only" | "both_retired"
      - is_first_year: bool (analysis date falls in this year)
    """
    is_first_year = (year == analysis_date.year)

    # Client months
    if is_first_year and client_ret.year > year:
        # First year and not retiring this year — prorate from analysis date
        c_months = months_remaining_in_year(analysis_date)
    elif client_ret.year == date(1900, 1, 1).year:
        c_months = 0  # already retired
    else:
        c_months = months_worked_in_year(client_ret, year)

    # Spouse months
    if spouse_dob is None or spouse_ret is None:
        s_months = 0
    elif is_first_year and spouse_ret.year > year:
        s_months = months_remaining_in_year(analysis_date)
    elif spouse_ret.year == date(1900, 1, 1).year:
        s_months = 0
    else:
        s_months = months_worked_in_year(spouse_ret, year)

    # Ages at Dec 31
    c_age = age_at_year_end(client_dob, year)
    s_age = age_at_year_end(spouse_dob, year) if spouse_dob else None

    # Phase label
    c_working = c_months > 0
    s_working = s_months > 0
    if c_working and s_working:
        phase = "both_working"
    elif c_working:
        phase = "client_only"
    elif s_working:
        phase = "spouse_only"
    else:
        phase = "both_retired"

    return {
        "year":                  year,
        "client_age":            c_age,
        "spouse_age":            s_age,
        "client_months_working": c_months,
        "spouse_months_working": s_months,
        "phase":                 phase,
        "is_first_year":         is_first_year,
    }


# ── Projection year range ─────────────────────────────────────────────────────

def projection_years(
    analysis_date: date,
    client_dob: date,
    client_horizon_age: int,
    spouse_dob: Optional[date] = None,
    spouse_horizon_age: Optional[int] = None,
    override_end_age: Optional[int] = None,
) -> list[int]:
    """
    Return list of calendar years to project.
    Starts at analysis year.
    Ends at the later of client or spouse planning horizon.
    """
    start_year = analysis_date.year

    client_end = client_dob.year + (override_end_age or client_horizon_age)

    if spouse_dob and spouse_horizon_age:
        spouse_end = spouse_dob.year + (override_end_age or spouse_horizon_age)
        end_year = max(client_end, spouse_end)
    else:
        end_year = client_end

    return list(range(start_year, end_year))


# ── Build full phase table ────────────────────────────────────────────────────

def build_phase_table(client_data: dict) -> list[dict]:
    """
    Entry point: takes full client JSON, returns list of year-phase dicts
    for every projection year.
    """
    meta         = client_data["meta"]
    client       = client_data["client"]
    spouse       = client_data.get("spouse")
    assumptions  = client_data["assumptions"]

    analysis_date = parse_date(meta["analysis_date"])
    client_dob    = parse_date(client["dob"])
    client_ret    = get_retirement_date(client, client_dob)

    spouse_dob  = parse_date(spouse["dob"]) if spouse else None
    spouse_ret  = get_retirement_date(spouse, spouse_dob) if spouse else None

    client_horizon = client.get("planning_horizon_age", 90)
    spouse_horizon = spouse.get("planning_horizon_age", 90) if spouse else None
    override_end   = assumptions.get("projection_end_age")

    years = projection_years(
        analysis_date, client_dob, client_horizon,
        spouse_dob, spouse_horizon, override_end
    )

    table = []
    for yr in years:
        row = year_phase(
            yr, analysis_date,
            client_dob, client_ret,
            spouse_dob, spouse_ret,
        )
        table.append(row)

    return table
