"""
Module 2 — Income Proration Engine
Calculates prorated salary, 401k contributions, and employer match
for each person for each projection year, applying:
  - Partial-year proration (first year from analysis date, final year to retirement)
  - Annual raises (applied each Jan 1 on full-year salary)
  - IRS contribution limits (employee + catch-up)
  - Employer match with cap
  - Final-year 401k total flagged for IRA opening balance rollup
"""
from datetime import date
from typing import Optional

# ── IRS limits by tax year ────────────────────────────────────────────────────
# Format: {year: {"employee": limit, "catchup": additional_catchup, "total": combined_limit}}
IRS_LIMITS = {
    2023: {"employee": 22500,  "catchup": 7500,  "total": 66000},
    2024: {"employee": 23000,  "catchup": 7500,  "total": 69000},
    2025: {"employee": 23500,  "catchup": 7500,  "total": 70000},
    2026: {"employee": 23500,  "catchup": 7500,  "total": 71000},
}
IRS_CATCHUP_AGE = 50
IRS_RMD_START_AGE = 73

def get_irs_limits(tax_year: int) -> dict:
    """Return IRS limits for year, using most recent known year if future."""
    years = sorted(IRS_LIMITS.keys())
    yr = tax_year if tax_year in IRS_LIMITS else years[-1]
    return IRS_LIMITS[yr]


# ── Per-person per-year employment income ─────────────────────────────────────

def calc_employment_year(
    year: int,
    months_working: int,
    annual_salary_base: float,
    years_since_base: int,
    raise_pct: float,
    contrib_401k_pct: float,
    contrib_roth_pct: float,
    employer_match_pct: float,
    employer_match_cap_pct: float,
    apply_catchup: bool,
    age_this_year: int,
    tax_year: int,
) -> dict:
    """
    Calculate all employment-related figures for one person for one year.

    Returns dict with:
      prorated_salary, annual_salary (full-year),
      contrib_traditional, contrib_roth, employer_match,
      total_401k_to_ira (contrib + match),
      is_final_working_year (True if months_working < 12 and > 0 and year > base_year)
    """
    if months_working == 0:
        return {
            "prorated_salary":       0.0,
            "annual_salary":         0.0,
            "contrib_traditional":   0.0,
            "contrib_roth":          0.0,
            "employer_match":        0.0,
            "total_401k_to_ira":     0.0,
            "is_final_working_year": False,
            "is_partial_year":       False,
        }

    # Apply raises: salary grows each full Jan 1
    annual_salary = annual_salary_base * ((1 + raise_pct) ** years_since_base)

    # Prorated salary for this year
    prorated_salary = annual_salary / 12 * months_working

    # IRS limits
    limits = get_irs_limits(tax_year)
    emp_limit = limits["employee"]
    if apply_catchup and age_this_year >= IRS_CATCHUP_AGE:
        emp_limit += limits["catchup"]

    # Employee contributions (traditional + Roth share the same IRS limit)
    raw_trad  = prorated_salary * contrib_401k_pct
    raw_roth  = prorated_salary * contrib_roth_pct
    raw_total = raw_trad + raw_roth

    # Cap at IRS limit
    if raw_total > emp_limit:
        scale        = emp_limit / raw_total
        raw_trad    *= scale
        raw_roth    *= scale
        raw_total    = emp_limit

    contrib_trad = round(raw_trad,  2)
    contrib_roth = round(raw_roth,  2)

    # Employer match: match_pct on contributions up to (salary * match_cap_pct)
    matchable_salary = prorated_salary * employer_match_cap_pct
    matchable_contrib = min(raw_total, matchable_salary)
    employer_match = round(matchable_contrib * employer_match_pct, 2)

    # Total going into IRA/401k this year (for IRA opening balance rollup)
    total_to_ira = contrib_trad + employer_match  # Roth tracked separately

    is_partial = (months_working < 12)

    return {
        "prorated_salary":       round(prorated_salary, 2),
        "annual_salary":         round(annual_salary, 2),
        "contrib_traditional":   contrib_trad,
        "contrib_roth":          contrib_roth,
        "employer_match":        employer_match,
        "total_401k_to_ira":     round(total_to_ira, 2),
        "is_partial_year":       is_partial,
    }


# ── Build full employment table for both people ───────────────────────────────

def build_employment_table(client_data: dict, phase_table: list[dict]) -> list[dict]:
    """
    For each year in phase_table, compute employment income for client and spouse.
    Returns list of dicts, one per year, merged with phase info.
    """
    meta        = client_data["meta"]
    client      = client_data["client"]
    spouse      = client_data.get("spouse")
    assumptions = client_data["assumptions"]
    tax_year    = assumptions.get("tax_year", 2024)

    analysis_year = int(meta["analysis_date"][:4])

    def get_emp(person):
        """Extract employment config or return zeroed defaults."""
        emp = person.get("employment") or {}
        return {
            "annual_salary":          emp.get("annual_salary", 0),
            "annual_raise_pct":       emp.get("annual_raise_pct", 0),
            "contrib_401k_pct":       emp.get("contrib_401k_pct", 0),
            "contrib_roth_401k_pct":  emp.get("contrib_roth_401k_pct", 0),
            "employer_match_pct":     emp.get("employer_match_pct", 0),
            "employer_match_cap_pct": emp.get("employer_match_cap_pct", 0),
            "apply_catchup":          emp.get("apply_catchup", True),
        }

    c_emp = get_emp(client)
    s_emp = get_emp(spouse) if spouse else get_emp({})

    results = []
    for row in phase_table:
        year = row["year"]
        yrs_since = year - analysis_year

        # Client
        c_result = calc_employment_year(
            year                 = year,
            months_working       = row["client_months_working"],
            annual_salary_base   = c_emp["annual_salary"],
            years_since_base     = yrs_since,
            raise_pct            = c_emp["annual_raise_pct"],
            contrib_401k_pct     = c_emp["contrib_401k_pct"],
            contrib_roth_pct     = c_emp["contrib_roth_401k_pct"],
            employer_match_pct   = c_emp["employer_match_pct"],
            employer_match_cap_pct = c_emp["employer_match_cap_pct"],
            apply_catchup        = c_emp["apply_catchup"],
            age_this_year        = row["client_age"],
            tax_year             = tax_year,
        )

        # Spouse
        s_result = calc_employment_year(
            year                 = year,
            months_working       = row["spouse_months_working"],
            annual_salary_base   = s_emp["annual_salary"],
            years_since_base     = yrs_since,
            raise_pct            = s_emp["annual_raise_pct"],
            contrib_401k_pct     = s_emp["contrib_401k_pct"],
            contrib_roth_pct     = s_emp["contrib_roth_401k_pct"],
            employer_match_pct   = s_emp["employer_match_pct"],
            employer_match_cap_pct = s_emp["employer_match_cap_pct"],
            apply_catchup        = s_emp["apply_catchup"],
            age_this_year        = row["spouse_age"] or 0,
            tax_year             = tax_year,
        )

        results.append({
            **row,
            "client_salary":            c_result["prorated_salary"],
            "client_contrib_trad":      c_result["contrib_traditional"],
            "client_contrib_roth":      c_result["contrib_roth"],
            "client_match":             c_result["employer_match"],
            "client_401k_to_ira":       c_result["total_401k_to_ira"],
            "spouse_salary":            s_result["prorated_salary"],
            "spouse_contrib_trad":      s_result["contrib_traditional"],
            "spouse_contrib_roth":      s_result["contrib_roth"],
            "spouse_match":             s_result["employer_match"],
            "spouse_401k_to_ira":       s_result["total_401k_to_ira"],
            "total_employment_income":  round(c_result["prorated_salary"] + s_result["prorated_salary"], 2),
            "total_401k_contributions": round(
                c_result["contrib_traditional"] + c_result["contrib_roth"] +
                s_result["contrib_traditional"] + s_result["contrib_roth"], 2
            ),
        })

    return results
