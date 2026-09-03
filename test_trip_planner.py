import json

import pytest

from trip_planner.agent import TripPlanRequest, plan_trip
from trip_planner.schema import (
    ACCOMMODATION_ITEM_SCHEMA,
    ACTIVITY_ITEM_SCHEMA,
    FLIGHT_ITEM_SCHEMA,
    TRIP_PLAN_SCHEMA,
)

VALID_COST = {"status": "available", "amount": 500, "currency": "USD"}
UNAVAILABLE_COST = {"status": "unavailable", "amount": 0, "currency": ""}


# --- schema shape -----------------------------------------------------------

def test_top_level_schema_has_required_sections():
    props = TRIP_PLAN_SCHEMA["properties"]
    assert set(TRIP_PLAN_SCHEMA["required"]) == {
        "trip_request",
        "summary",
        "flights",
        "accommodation",
        "activities",
    }
    for section in ("flights", "accommodation", "activities"):
        assert props[section]["additionalProperties"] is False
        assert "items" in props[section]["properties"]
        assert "data_availability" in props[section]["properties"]


@pytest.mark.parametrize(
    "item_schema",
    [FLIGHT_ITEM_SCHEMA, ACCOMMODATION_ITEM_SCHEMA, ACTIVITY_ITEM_SCHEMA],
)
def test_item_schemas_disallow_additional_properties(item_schema):
    assert item_schema["additionalProperties"] is False
    assert item_schema["type"] == "object"
    # every field listed in properties must be required, so downstream
    # parsers never have to guess whether a key is present
    assert set(item_schema["properties"]) == set(item_schema["required"])


def test_cost_fields_use_status_flag_not_null():
    # a downstream parser should never need to special-case null - it checks
    # "status" and only trusts amount/currency when status == "available"
    cost_schema = FLIGHT_ITEM_SCHEMA["properties"]["estimated_cost"]
    assert cost_schema["properties"]["status"]["enum"] == ["available", "unavailable"]
    assert "null" not in json.dumps(cost_schema)


# --- prompt building ---------------------------------------------------------

def test_user_prompt_includes_all_inputs():
    request = TripPlanRequest(
        destination="Lisbon, Portugal",
        start_date="2026-10-10",
        end_date="2026-10-17",
        budget_amount=2200,
        budget_currency="USD",
    )
    prompt = request.user_prompt()
    assert "Lisbon, Portugal" in prompt
    assert "2026-10-10" in prompt
    assert "2026-10-17" in prompt
    assert "2200" in prompt
    assert "USD" in prompt


# --- plan_trip against a fake client (no network / API key needed) ---------

class _FakeBlock:
    def __init__(self, type_, text=None):
        self.type = type_
        self.text = text


class _FakeMessage:
    def __init__(self, content, stop_reason):
        self.content = content
        self.stop_reason = stop_reason


class _FakeStreamCM:
    def __init__(self, message):
        self._message = message

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def get_final_message(self):
        return self._message


class _FakeMessages:
    def __init__(self, message):
        self._message = message
        self.calls = []

    def stream(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeStreamCM(self._message)


class _FakeClient:
    def __init__(self, message):
        self.messages = _FakeMessages(message)


def _sample_plan_json():
    def category(item):
        return {"data_availability": "full", "notes": "", "items": [item] * 5}

    flight_item = {
        "rank": 1,
        "airline": "Air Example",
        "route": "JFK -> LIS (nonstop)",
        "departure_date": "2026-10-10",
        "return_date": "2026-10-17",
        "stops": "nonstop",
        "estimated_cost": VALID_COST,
        "value_rationale": "cheapest nonstop",
        "source": "example.com",
    }
    hotel_item = {
        "rank": 1,
        "name": "Hotel Example",
        "property_type": "hotel",
        "neighborhood": "Baixa",
        "estimated_cost_per_night": VALID_COST,
        "estimated_total_cost": VALID_COST,
        "rating": "4.5/5",
        "within_budget": "yes",
        "value_rationale": "central and well reviewed",
        "source": "example.com",
    }
    activity_item = {
        "rank": 1,
        "name": "Walking Tour",
        "category": "tour",
        "estimated_cost": UNAVAILABLE_COST,
        "typical_duration": "3 hours",
        "rating": "unavailable",
        "value_rationale": "top-rated free tour",
        "source": "unavailable",
    }

    return {
        "trip_request": {
            "destination": "Lisbon, Portugal",
            "start_date": "2026-10-10",
            "end_date": "2026-10-17",
            "budget_amount": 2200,
            "budget_currency": "USD",
        },
        "summary": "This trip fits comfortably within budget.",
        "flights": category(flight_item),
        "accommodation": category(hotel_item),
        "activities": category(activity_item),
    }


def test_plan_trip_parses_final_json_from_fake_client():
    plan_dict = _sample_plan_json()
    message = _FakeMessage(
        content=[_FakeBlock("text", json.dumps(plan_dict))],
        stop_reason="end_turn",
    )
    client = _FakeClient(message)
    request = TripPlanRequest("Lisbon, Portugal", "2026-10-10", "2026-10-17", 2200, "USD")

    result = plan_trip(request, client=client)

    assert result == plan_dict
    assert client.messages.calls[0]["model"]
    assert client.messages.calls[0]["tools"][0]["name"] == "web_search"


def test_plan_trip_resumes_on_pause_turn_then_succeeds():
    plan_dict = _sample_plan_json()
    paused = _FakeMessage(
        content=[_FakeBlock("server_tool_use")],
        stop_reason="pause_turn",
    )
    done = _FakeMessage(
        content=[_FakeBlock("text", json.dumps(plan_dict))],
        stop_reason="end_turn",
    )

    class _ResumingMessages(_FakeMessages):
        def __init__(self):
            self._message = paused
            self.calls = []
            self._n = 0

        def stream(self, **kwargs):
            self.calls.append(kwargs)
            self._n += 1
            return _FakeStreamCM(paused if self._n == 1 else done)

    client = _FakeClient(paused)
    client.messages = _ResumingMessages()
    request = TripPlanRequest("Lisbon, Portugal", "2026-10-10", "2026-10-17", 2200, "USD")

    result = plan_trip(request, client=client)

    assert result == plan_dict
    assert len(client.messages.calls) == 2


def test_plan_trip_raises_on_refusal():
    message = _FakeMessage(content=[], stop_reason="refusal")
    client = _FakeClient(message)
    request = TripPlanRequest("Lisbon, Portugal", "2026-10-10", "2026-10-17", 2200, "USD")

    with pytest.raises(RuntimeError, match="declined"):
        plan_trip(request, client=client)
