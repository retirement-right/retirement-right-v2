"""
Module 3 — Social Security Engine
Calculates annual SS income for client and spouse for each projection year.
Handles: already collecting, file at future age, spousal benefits,
COLA growth, and survivor benefit after first death.

v2 update: early_filing_reduction() and fra_for_dob() added to correctly
reduce benefits when filing before Full Retirement Age (FRA).
SSA formula: 5/9 of 1% per month for first 36 months early,
             5/12 of 1% per month for each month beyond 36.
"""
from datetime import date
from engine.dates import parse_date, age_at_year_end


def fra_for_dob(dob: date) -> int:
    """
    Returns Full Retirement Age based on birth year per SSA rules.
      1937 or earlier : 65
      1938–1954       : 66
      1955–1959       : 66 (SSA grades these by months but engine uses whole years)
      1960 or later   : 67
    """
    birth_year = dob.year
    if birth_year <= 1937:
        return 65
    elif birth_year <= 1954:
        return 66
    elif birth_year <= 1959:
        return 66
    else:
        return 67  # 1960 and later


def early_filing_reduction(file_age: int, fra: int) -> float:
    """
    Returns the benefit multiplier when filing before FRA.
    Returns 1.0 if filing at or after FRA — no reduction applied.

    SSA formula:
      First 36 months early : 5/9 of 1% reduction per month
      Beyond 36 months early: 5/12 of 1% reduction per month

    Examples:
      File at 65, FRA 67 (24 months early) -> 1 - (24 * 5/9 / 100) = 0.8667  (~13.3% reduction)
      File at 62, FRA 67 (60 months early) -> 1 - (36*5/9 + 24*5/12) / 100  = 0.70  (30% reduction)
      File at 67, FRA 67 (0 months early)  -> 1.0 (no reduction)
    """
    months_early = max(0, (fra - file_age) * 12)
    if months_early == 0:
        return 1.0
    first_36  = min(months_early, 36)
    beyond_36 = max(months_early - 36, 0)
    reduction = (first_36 * (5 / 9) + beyond_36 * (5 / 12)) / 100
    return round(1.0 - reduction, 6)


def ss_annual_for_year(
    year: int,
    status: str,
    monthly_benefit: float,
    cola_pct: float,
    file_age: int | None,
    dob: date,
    analysis_date: date,
    spousal_monthly: float = 0.0,
) -> float:
    """
    Return total SS income for one person in a given year.

    status:
      'collecting'  — already receiving; benefit is current monthly amount,
                      COLA applied from analysis_date year forward
      'file_at_age' — will file at file_age; zero until that year,
                      early-filing reduction applied if file_age < FRA,
                      COLA applied from filing year forward
      'not_started' — returns 0 for all years (no plan set)

    Note: for 'collecting' status the monthly_benefit passed in is assumed
    to already reflect any early-filing reduction the client accepted when
    they originally claimed — no further adjustment is made.
    """
    if status == "not_started" or not monthly_benefit:
        return 0.0

    analysis_year = analysis_date.year
    age_this_year = age_at_year_end(dob, year)

    if status == "collecting":
        # COLA grows from analysis_year
        # Benefit is taken as-is (already reflects actual claimed amount)
        years_of_cola = year - analysis_year
        annual = monthly_benefit * 12 * ((1 + cola_pct) ** years_of_cola)
        return round(annual, 2)

    if status == "file_at_age":
        if age_this_year < file_age:
            return 0.0
        # Apply early-filing reduction if claiming before FRA
        fra       = fra_for_dob(dob)
        reduction = early_filing_reduction(file_age, fra)
        # COLA grows from filing year forward
        filing_year    = dob.year + file_age
        years_of_cola  = year - filing_year
        annual = (monthly_benefit * 12
                  * reduction
                  * ((1 + cola_pct) ** max(years_of_cola, 0)))
        return round(annual, 2)

    return 0.0


def build_ss_table(client_data: dict, phase_table: list[dict]) -> list[dict]:
    """
    For each year in phase_table, calculate SS income for client and spouse.
    Also handles survivor benefit: when one person reaches their planning horizon,
    the survivor collects the higher of the two SS benefits.
    """
    meta        = client_data["meta"]
    client      = client_data["client"]
    spouse      = client_data.get("spouse")
    assumptions = client_data["assumptions"]

    analysis_date = parse_date(meta["analysis_date"])
    client_dob    = parse_date(client["dob"])
    spouse_dob    = parse_date(spouse["dob"]) if spouse else None

    client_horizon = client.get("planning_horizon_age", 90)
    spouse_horizon = spouse.get("planning_horizon_age", 90) if spouse else None

    ss_cfg = client_data.get("income", {}).get("social_security", {})
    c_ss   = ss_cfg.get("client") or {}
    s_ss   = ss_cfg.get("spouse") or {}

    results = []
    for row in phase_table:
        year        = row["year"]
        client_age  = row["client_age"]
        spouse_age  = row.get("spouse_age")

        # Has client reached their planning horizon?
        client_alive = client_age <= client_horizon
        spouse_alive = (spouse_age is not None and
                        spouse_horizon is not None and
                        spouse_age <= spouse_horizon)

        # Raw SS for each person
        c_annual = ss_annual_for_year(
            year            = year,
            status          = c_ss.get("status", "not_started"),
            monthly_benefit = c_ss.get("monthly_benefit") or 0,
            cola_pct        = c_ss.get("cola_pct", 0.015),
            file_age        = c_ss.get("file_age"),
            dob             = client_dob,
            analysis_date   = analysis_date,
            spousal_monthly = c_ss.get("spousal_benefit") or 0,
        ) if client_alive else 0.0

        s_annual = ss_annual_for_year(
            year            = year,
            status          = s_ss.get("status", "not_started"),
            monthly_benefit = s_ss.get("monthly_benefit") or 0,
            cola_pct        = s_ss.get("cola_pct", 0.015),
            file_age        = s_ss.get("file_age"),
            dob             = spouse_dob,
            analysis_date   = analysis_date,
            spousal_monthly = s_ss.get("spousal_benefit") or 0,
        ) if (spouse_dob and spouse_alive) else 0.0

        # Survivor benefit logic:
        # When client dies (past horizon), survivor gets higher benefit
        # When spouse dies, same logic in reverse
        if not client_alive and spouse_alive and spouse_dob:
            s_survivor = ss_annual_for_year(
                year=year, status=c_ss.get("status", "not_started"),
                monthly_benefit=c_ss.get("monthly_benefit") or 0,
                cola_pct=c_ss.get("cola_pct", 0.015),
                file_age=c_ss.get("file_age"), dob=client_dob,
                analysis_date=analysis_date,
            )
            s_annual = max(s_annual, s_survivor)
            c_annual = 0.0

        if not spouse_alive and client_alive and spouse_dob:
            c_survivor = ss_annual_for_year(
                year=year, status=s_ss.get("status", "not_started"),
                monthly_benefit=s_ss.get("monthly_benefit") or 0,
                cola_pct=s_ss.get("cola_pct", 0.015),
                file_age=s_ss.get("file_age"), dob=spouse_dob,
                analysis_date=analysis_date,
            )
            c_annual = max(c_annual, c_survivor)
            s_annual = 0.0

        results.append({
            **row,
            "client_ss":    round(c_annual, 2),
            "spouse_ss":    round(s_annual, 2),
            "total_ss":     round(c_annual + s_annual, 2),
            "client_alive": client_alive,
            "spouse_alive": spouse_alive,
        })

    return results
