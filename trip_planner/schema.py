"""JSON schema for the trip planner agent's structured output.

The schema is passed to the Messages API via ``output_config.format`` so the
model's final response is guaranteed to be valid, parseable JSON that matches
this shape exactly - no prose wrapper, no missing fields. A second, downstream
agent can therefore parse the response with a plain ``json.loads()`` and rely
on every key being present.

Cost handling: every price is represented as a small object with a ``status``
field of ``"available"`` or ``"unavailable"``. Downstream code MUST check
``status`` before trusting ``amount``/``currency`` - when data could not be
found, the model sets ``status: "unavailable"`` and ``amount: 0`` /
``currency: ""`` as placeholders rather than guessing a real-looking price.
"""

from __future__ import annotations

from typing import Any, Dict

# Reused by every "cost" field across flights / accommodation / activities.
_COST_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "description": (
        "Estimated cost. Check 'status' first: if 'unavailable', amount and "
        "currency are placeholders (0 / empty string), not a real estimate."
    ),
    "properties": {
        "status": {
            "type": "string",
            "enum": ["available", "unavailable"],
            "description": "'available' if a real price estimate was found, else 'unavailable'.",
        },
        "amount": {
            "type": "number",
            "description": "Numeric price estimate. Meaningless placeholder (0) when status is 'unavailable'.",
        },
        "currency": {
            "type": "string",
            "description": "ISO 4217 currency code (e.g. 'USD'). Empty string when status is 'unavailable'.",
        },
    },
    "required": ["status", "amount", "currency"],
    "additionalProperties": False,
}

_CATEGORY_NOTES_FIELDS = {
    "data_availability": {
        "type": "string",
        "enum": ["full", "partial", "unavailable"],
        "description": (
            "'full' = all 5 slots filled with real data, 'partial' = some slots "
            "could not be filled or lack cost data, 'unavailable' = no usable "
            "data was found for this category at all."
        ),
    },
    "notes": {
        "type": "string",
        "description": (
            "Short explanation of any gaps, e.g. 'Only 3 flight options found for "
            "these dates' or 'unavailable - no search results returned pricing'."
        ),
    },
}

FLIGHT_ITEM_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "rank": {"type": "integer", "description": "1 = best value, 5 = worst of the returned options."},
        "airline": {"type": "string", "description": "Airline or carrier name, or 'unavailable' if not found."},
        "route": {"type": "string", "description": "e.g. 'JFK -> CDG (nonstop)' or 'JFK -> LHR -> CDG (1 stop)'."},
        "departure_date": {"type": "string", "description": "Outbound date, ISO 8601 (YYYY-MM-DD)."},
        "return_date": {"type": "string", "description": "Return date, ISO 8601 (YYYY-MM-DD), or 'n/a' for one-way."},
        "stops": {"type": "string", "description": "e.g. 'nonstop', '1 stop', 'unavailable'."},
        "estimated_cost": _COST_SCHEMA,
        "value_rationale": {
            "type": "string",
            "description": "Why this option ranks where it does (price vs. convenience, duration, etc.).",
        },
        "source": {"type": "string", "description": "Site/domain the info came from, or 'unavailable'."},
    },
    "required": [
        "rank",
        "airline",
        "route",
        "departure_date",
        "return_date",
        "stops",
        "estimated_cost",
        "value_rationale",
        "source",
    ],
    "additionalProperties": False,
}

ACCOMMODATION_ITEM_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "rank": {"type": "integer", "description": "1 = best value, 5 = worst of the returned options."},
        "name": {"type": "string", "description": "Property name, or 'unavailable' if not found."},
        "property_type": {
            "type": "string",
            "description": "e.g. 'hotel', 'hostel', 'apartment/vacation rental', 'unavailable'.",
        },
        "neighborhood": {"type": "string", "description": "Area/neighborhood, or 'unavailable'."},
        "estimated_cost_per_night": _COST_SCHEMA,
        "estimated_total_cost": {
            **_COST_SCHEMA,
            "description": _COST_SCHEMA["description"] + " Total for the full stay across the given travel dates.",
        },
        "rating": {"type": "string", "description": "e.g. '4.5/5 (1,200 reviews)', or 'unavailable'."},
        "within_budget": {
            "type": "string",
            "enum": ["yes", "no", "unknown"],
            "description": "Whether estimated_total_cost fits the traveler's stated budget alongside the other categories.",
        },
        "value_rationale": {"type": "string", "description": "Why this option ranks where it does."},
        "source": {"type": "string", "description": "Site/domain the info came from, or 'unavailable'."},
    },
    "required": [
        "rank",
        "name",
        "property_type",
        "neighborhood",
        "estimated_cost_per_night",
        "estimated_total_cost",
        "rating",
        "within_budget",
        "value_rationale",
        "source",
    ],
    "additionalProperties": False,
}

ACTIVITY_ITEM_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "rank": {"type": "integer", "description": "1 = best value, 5 = worst of the returned options."},
        "name": {"type": "string", "description": "Activity/attraction name, or 'unavailable' if not found."},
        "category": {
            "type": "string",
            "description": "e.g. 'museum', 'tour', 'outdoor', 'landmark', 'food experience', 'unavailable'.",
        },
        "estimated_cost": _COST_SCHEMA,
        "typical_duration": {"type": "string", "description": "e.g. '2-3 hours', 'half day', 'unavailable'."},
        "rating": {"type": "string", "description": "e.g. '4.7/5 (8,400 reviews)', or 'unavailable'."},
        "value_rationale": {"type": "string", "description": "Why this option ranks where it does."},
        "source": {"type": "string", "description": "Site/domain the info came from, or 'unavailable'."},
    },
    "required": [
        "rank",
        "name",
        "category",
        "estimated_cost",
        "typical_duration",
        "rating",
        "value_rationale",
        "source",
    ],
    "additionalProperties": False,
}


def _category_schema(item_schema: Dict[str, Any], max_items: int = 5) -> Dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            **_CATEGORY_NOTES_FIELDS,
            "items": {
                "type": "array",
                "description": f"Up to {max_items} options, ranked best value first (rank 1 = best).",
                "items": item_schema,
            },
        },
        "required": ["data_availability", "notes", "items"],
        "additionalProperties": False,
    }


TRIP_PLAN_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "trip_request": {
            "type": "object",
            "description": "Echo of the inputs this plan was generated for, for downstream traceability.",
            "properties": {
                "destination": {"type": "string"},
                "start_date": {"type": "string", "description": "ISO 8601 (YYYY-MM-DD)."},
                "end_date": {"type": "string", "description": "ISO 8601 (YYYY-MM-DD)."},
                "budget_amount": {"type": "number"},
                "budget_currency": {"type": "string", "description": "ISO 4217 currency code (e.g. 'USD')."},
            },
            "required": ["destination", "start_date", "end_date", "budget_amount", "budget_currency"],
            "additionalProperties": False,
        },
        "summary": {
            "type": "string",
            "description": (
                "Short (3-6 sentence) natural-language summary of overall trip feasibility given the "
                "budget: whether flights + accommodation + activities plausibly fit, roughly how much "
                "headroom or shortfall there is, and any major data gaps that limit confidence."
            ),
        },
        "flights": _category_schema(FLIGHT_ITEM_SCHEMA),
        "accommodation": _category_schema(ACCOMMODATION_ITEM_SCHEMA),
        "activities": _category_schema(ACTIVITY_ITEM_SCHEMA),
    },
    "required": ["trip_request", "summary", "flights", "accommodation", "activities"],
    "additionalProperties": False,
}
