# Retirement-Right API v2

Clean-build retirement income projection engine + PDF generator.

## Structure

```
retirement-right-v2/
├── api/
│   └── main.py              # FastAPI app — POST /generate
├── engine/
│   ├── orchestrator.py      # Wires all 8 modules, entry point
│   ├── dates.py             # Phase detection, proration months
│   ├── proration.py         # Salary, 401k, employer match
│   ├── social_security.py   # SS income, COLA, survivor benefit
│   ├── fixed_income.py      # Pension, rental, annuity, other
│   ├── rmd.py               # IRS RMD table, inherited IRA 10-yr rule
│   ├── taxes.py             # Federal brackets, state flat rate
│   ├── waterfall.py         # Income gap, funding source priority
│   └── portfolio.py         # Account balance tracking
├── pdf/
│   └── generator.py         # ReportLab 4-page PDF output
├── fixtures/
│   ├── abel.json            # Working couple, two retirement dates
│   ├── eberhardt.json       # Fully retired, inherited IRA, annuity
│   ├── thompson.json        # 401k+match, Roth, pension, Scenario C
│   └── thompson_single.json # Single filer variant
├── schema_v2.json           # Full JSON schema with all fields
├── requirements.txt
└── render.yaml
```

## Local development

```bash
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000
```

Test with Abel fixture:
```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d @fixtures/abel.json \
  --output abel_report.pdf
```

Get projection data as JSON (no PDF):
```bash
curl -X POST http://localhost:8000/projection \
  -H "Content-Type: application/json" \
  -d @fixtures/abel.json
```

Validate a client file:
```bash
curl -X POST http://localhost:8000/validate \
  -H "Content-Type: application/json" \
  -d @fixtures/thompson.json
```

Run engine directly (CLI):
```bash
python engine/orchestrator.py fixtures/abel.json
python engine/orchestrator.py fixtures/eberhardt.json
python engine/orchestrator.py fixtures/thompson.json
```

## Deploy to Render

1. Push this repo to GitHub as `retirement-right-v2`
2. Go to render.com → New → Web Service
3. Connect your GitHub repo
4. Render auto-detects `render.yaml` — click Deploy
5. Your API will be live at `https://retirement-right-v2.onrender.com`

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | API info |
| GET | `/health` | Health check |
| POST | `/generate` | Client JSON → PDF binary |
| POST | `/projection` | Client JSON → projection JSON |
| POST | `/validate` | Client JSON → schema validation |

## Schema v2 — key fields

See `schema_v2.json` for complete documentation. Key new fields vs v1:

- `meta.analysis_date` — drives first-year salary proration
- `client.retirement.date` + `date_known` — exact or estimated retirement
- `spouse.retirement.date` + `date_known` — independent from client
- `client.employment.contrib_401k_pct` — 401k contribution %
- `client.employment.employer_match_pct` + `employer_match_cap_pct`
- `income.social_security.client.status` — collecting / file_at_age / not_started
- `assets.ira_inherited` — balance + 10-year rule fields

## Test fixtures coverage

| Scenario | Abel | Eberhardt | Thompson |
|----------|------|-----------|----------|
| Both working | ✓ | — | — |
| Client only working (Scenario C) | — | — | ✓ |
| Both retired | — | ✓ | — |
| SS file at future age | ✓ | — | — |
| SS already collecting | — | ✓ | ✓ |
| SS not started (govt employee) | — | — | ✓ |
| 401k + employer match + Roth | — | — | ✓ |
| Pension with COLA | — | — | ✓ |
| Inherited IRA 10-year rule | — | ✓ | ✓ |
| Annuity income + asset value | — | ✓ | ✓ |
| Real estate equity | — | ✓ | ✓ |
| Single filer | — | — | ✓ (variant) |
| No state income tax | — | — | ✓ (TX) |
