# MPG Calculator

## Overview
This project is a simple Python-based tool that calculates fuel efficiency in miles per gallon (MPG).  
It takes user input for distance traveled and fuel used, then computes the MPG.

---

## Features
- Calculates MPG using distance and fuel input
- Input validation:
  - Rejects zero fuel
  - Rejects negative values
  - Ensures numeric input
- Includes automated tests using pytest

---

## Project Structure

CItest trigger

---

# Trip Planning Research Agent

A Python research agent that plans a trip given a **destination**, **travel
dates**, and a **budget**. It uses Claude with the server-side web search
tool to find real flight, accommodation, and activity options, ranks the
top 5 in each category by overall value, and returns everything as a single
structured JSON document designed to be consumed by another agent.

## Setup

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
```

## Usage

CLI:

```bash
python -m trip_planner.cli \
  --destination "Lisbon, Portugal" \
  --start-date 2026-10-10 \
  --end-date 2026-10-17 \
  --budget 2200 \
  --currency USD
```

Programmatically:

```python
from trip_planner import TripPlanRequest, plan_trip

plan = plan_trip(TripPlanRequest(
    destination="Lisbon, Portugal",
    start_date="2026-10-10",
    end_date="2026-10-17",
    budget_amount=2200,
    budget_currency="USD",
))
```

## Output shape

The result always has this top-level shape (see `trip_planner/schema.py` for
the full JSON Schema, which is enforced via the Messages API's structured
outputs so the response is guaranteed to match):

```jsonc
{
  "trip_request": { "destination": "...", "start_date": "...", "end_date": "...", "budget_amount": 2200, "budget_currency": "USD" },
  "summary": "Natural-language feasibility summary...",
  "flights": { "data_availability": "full|partial|unavailable", "notes": "...", "items": [ /* up to 5, ranked */ ] },
  "accommodation": { "data_availability": "...", "notes": "...", "items": [ /* up to 5, ranked */ ] },
  "activities": { "data_availability": "...", "notes": "...", "items": [ /* up to 5, ranked */ ] }
}
```

Every price is an object like `{"status": "available", "amount": 450, "currency": "USD"}`.
When data can't be found, `status` is `"unavailable"` and `amount`/`currency`
are placeholders (`0`/`""`) rather than a guess - a downstream parser should
always check `status` before trusting the number.

## Tests

```bash
pytest test_trip_planner.py -v
```

Tests run against a fake Claude client (no network access or API key
required) and cover schema shape, prompt construction, JSON parsing, and the
`pause_turn` resume loop for long-running searches.