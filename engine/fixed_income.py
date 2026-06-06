"""
Module 4 — Fixed Income Engine
Calculates pension, rental, annuity, and other recurring income
for each projection year. All grow by their respective COLA/growth rates.
"""
from engine.dates import parse_date, age_at_year_end


def cola_amount(base: float, cola_pct: float, years: int) -> float:
    """Apply COLA for N years to a base amount."""
    return round(base * ((1 + cola_pct) ** years), 2)


def build_fixed_income_table(client_data: dict, phase_table: list[dict]) -> list[dict]:
    """
    For each year, calculate all fixed income sources:
      pension (client + spouse), rental, annuity, other_income items.

    Returns list of dicts with fixed income fields added.
    """
    meta        = client_data["meta"]
    income      = client_data.get("income", {})
    client      = client_data["client"]
    spouse      = client_data.get("spouse")

    analysis_year = int(meta["analysis_date"][:4])
    client_dob    = parse_date(client["dob"])
    spouse_dob    = parse_date(spouse["dob"]) if spouse else None

    pension_cfg = income.get("pension") or {}
    c_pension   = pension_cfg.get("client") or {}
    s_pension   = pension_cfg.get("spouse") or {}
    rental_cfg  = income.get("rental") or {}
    annuity_cfg = income.get("annuity") or {}
    other_list  = income.get("other_income") or []

    results = []
    for row in phase_table:
        year   = row["year"]
        c_age  = row["client_age"]
        s_age  = row.get("spouse_age", 0) or 0
        years_elapsed = year - analysis_year

        # ── Pension — client ──────────────────────────────────────────────
        c_pension_annual = 0.0
        if c_pension:
            start_age  = c_pension.get("start_age", 0)
            base       = (c_pension.get("monthly_amount", 0) or 0) * 12
            cola       = c_pension.get("cola_pct", 0)
            if c_age >= start_age and base > 0:
                years_on = year - (client_dob.year + start_age)
                c_pension_annual = cola_amount(base, cola, max(years_on, 0))

        # ── Pension — spouse ──────────────────────────────────────────────
        s_pension_annual = 0.0
        if s_pension and spouse_dob:
            start_age  = s_pension.get("start_age", 0)
            base       = (s_pension.get("monthly_amount", 0) or 0) * 12
            cola       = s_pension.get("cola_pct", 0)
            if s_age >= start_age and base > 0:
                years_on = year - (spouse_dob.year + start_age)
                s_pension_annual = cola_amount(base, cola, max(years_on, 0))

        # ── Rental income ─────────────────────────────────────────────────
        rental_annual = 0.0
        if rental_cfg:
            base = rental_cfg.get("annual_amount", 0) or 0
            cola = rental_cfg.get("cola_pct", 0.015)
            rental_annual = cola_amount(base, cola, years_elapsed)

        # ── Annuity income ────────────────────────────────────────────────
        annuity_annual = 0.0
        if annuity_cfg:
            start_age  = annuity_cfg.get("start_age", 0)
            base       = annuity_cfg.get("annual_income", 0) or 0
            cola       = annuity_cfg.get("cola_pct", 0)
            if c_age >= start_age and base > 0:
                years_on = year - (client_dob.year + start_age)
                annuity_annual = cola_amount(base, cola, max(years_on, 0))

        # ── Other income items ────────────────────────────────────────────
        other_annual = 0.0
        other_breakdown = []
        for item in other_list:
            start_age = item.get("start_age", 0)
            end_age   = item.get("end_age")
            base      = item.get("annual_amount", 0) or 0
            cola      = item.get("cola_pct", 0)
            if c_age >= start_age and (end_age is None or c_age <= end_age):
                years_on = year - (client_dob.year + start_age)
                amt = cola_amount(base, cola, max(years_on, 0))
                other_annual += amt
                other_breakdown.append({"label": item.get("label",""), "amount": amt})

        total_fixed = round(
            c_pension_annual + s_pension_annual +
            rental_annual + annuity_annual + other_annual, 2
        )

        results.append({
            **row,
            "client_pension":   round(c_pension_annual, 2),
            "spouse_pension":   round(s_pension_annual, 2),
            "rental":           round(rental_annual, 2),
            "annuity_income":   round(annuity_annual, 2),
            "other_income":     round(other_annual, 2),
            "other_breakdown":  other_breakdown,
            "total_fixed_non_ss": total_fixed,
        })

    return results
