"""Core research-agent logic: prompts, the Claude API call, and result parsing."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional

import anthropic

from .schema import TRIP_PLAN_SCHEMA

DEFAULT_MODEL = "claude-opus-5"

# Server-side tool with dynamic filtering (Claude Opus 5 / Sonnet 5 / Fable 5 /
# Opus 4.6+ / Sonnet 4.6). Runs entirely on Anthropic's infrastructure - no
# client-side tool execution loop is needed for it.
WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search", "max_uses": 40}

# A server-side search loop pauses (stop_reason: "pause_turn") after roughly
# 10 internal search iterations; we resume automatically up to this many times
# before giving up, so a research task needing many searches can still finish.
MAX_PAUSE_RESUMES = 6

SYSTEM_PROMPT = """\
You are a meticulous travel-research agent. Given a destination, a date range, \
and a total trip budget, you research real options using web search and return \
a single structured trip plan.

For EACH of three categories - flights, accommodation, activities - find and \
rank the top 5 options by overall value (not just lowest price: weigh price \
against convenience, quality, location, and reviews). Rank 1 is the best value.

Rules you must follow:
- Use the web_search tool to find real, current information. Do not rely on \
prior knowledge of prices, which goes stale quickly - search for it.
- Prefer reputable sources (airline sites, major OTAs like Google Flights/ \
Kayak/Expedia/Booking.com, official tourism/attraction sites, TripAdvisor).
- If you cannot find fewer than 5 solid options for a category, return as many \
as you actually found rather than inventing more - do not pad the list with \
speculative entries.
- If you cannot find cost data (or any other field) for an option, mark it as \
unavailable in that field rather than guessing or estimating from general \
knowledge. Never fabricate a specific price, rating, or name.
- Estimate accommodation's total cost using the full length of the stay implied \
by the given date range.
- In the summary, explicitly reason about feasibility: sum a reasonable \
low-to-mid estimate across the three categories and compare it to the stated \
budget, and call out if key data was missing in a way that limits confidence.
- Your final answer must be produced via the structured output format you were \
given - do not add any prose outside of it.
"""


@dataclass
class TripPlanRequest:
    destination: str
    start_date: str
    end_date: str
    budget_amount: float
    budget_currency: str = "USD"

    def user_prompt(self) -> str:
        return (
            f"Plan a trip to {self.destination} from {self.start_date} to "
            f"{self.end_date}, with a total budget of "
            f"{self.budget_amount:g} {self.budget_currency}.\n\n"
            "Research flights, accommodation, and activities for these exact "
            "dates and this destination, then return the ranked top 5 for each "
            "category plus a feasibility summary, per your instructions."
        )


def _resume_messages(user_prompt: str, response: "anthropic.types.Message") -> list:
    """Rebuild the message list to resume a paused server-side tool loop.

    Per Anthropic's guidance for `stop_reason == "pause_turn"`: re-send the
    original user turn plus the paused assistant turn verbatim (no synthetic
    "continue" message) and the server resumes the search loop automatically.
    """
    return [
        {"role": "user", "content": user_prompt},
        {"role": "assistant", "content": response.content},
    ]


def _call_claude(
    client: anthropic.Anthropic,
    model: str,
    user_prompt: str,
    max_tokens: int,
    effort: str,
) -> "anthropic.types.Message":
    messages = [{"role": "user", "content": user_prompt}]

    request_kwargs: Dict[str, Any] = dict(
        model=model,
        max_tokens=max_tokens,
        system=SYSTEM_PROMPT,
        tools=[WEB_SEARCH_TOOL],
        thinking={"type": "adaptive"},
        output_config={
            "effort": effort,
            "format": {"type": "json_schema", "schema": TRIP_PLAN_SCHEMA},
        },
        messages=messages,
    )

    with client.messages.stream(**request_kwargs) as stream:
        response = stream.get_final_message()

    resumes = 0
    while response.stop_reason == "pause_turn" and resumes < MAX_PAUSE_RESUMES:
        resumes += 1
        messages = _resume_messages(user_prompt, response)
        request_kwargs["messages"] = messages
        with client.messages.stream(**request_kwargs) as stream:
            response = stream.get_final_message()

    return response


def _extract_json(response: "anthropic.types.Message") -> Dict[str, Any]:
    if response.stop_reason == "refusal":
        raise RuntimeError(
            "Claude declined to produce a trip plan for this request "
            f"(stop_reason=refusal, details={getattr(response, 'stop_details', None)!r})."
        )
    if response.stop_reason == "max_tokens":
        raise RuntimeError(
            "Response was truncated at max_tokens before the structured output "
            "finished - increase max_tokens and retry."
        )
    if response.stop_reason == "pause_turn":
        raise RuntimeError(
            "Server-side search loop was still paused after the maximum number "
            "of resumes - the research task needed more search iterations than "
            "this run allowed. Try a narrower request or raise MAX_PAUSE_RESUMES."
        )

    text_blocks = [b.text for b in response.content if b.type == "text"]
    if not text_blocks:
        raise RuntimeError(
            f"No text content in Claude's response (stop_reason={response.stop_reason!r})."
        )

    # output_config.format guarantees the final text block is valid JSON
    # matching TRIP_PLAN_SCHEMA - but parse defensively rather than assume.
    try:
        return json.loads(text_blocks[-1])
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Structured output was not valid JSON: {exc}") from exc


def plan_trip(
    request: TripPlanRequest,
    client: Optional[anthropic.Anthropic] = None,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 16000,
    effort: str = "high",
) -> Dict[str, Any]:
    """Run the research agent and return the trip plan as a plain dict.

    The returned dict matches ``trip_planner.schema.TRIP_PLAN_SCHEMA`` exactly,
    so it can be handed directly to a downstream agent/parser.
    """
    client = client or anthropic.Anthropic()
    user_prompt = request.user_prompt()
    try:
        response = _call_claude(client, model, user_prompt, max_tokens, effort)
    except anthropic.RateLimitError as exc:
        retry_after = exc.response.headers.get("retry-after", "unknown") if exc.response else "unknown"
        raise RuntimeError(f"Rate limited by the Claude API; retry after {retry_after}s.") from exc
    except anthropic.AuthenticationError as exc:
        raise RuntimeError("Invalid or missing ANTHROPIC_API_KEY.") from exc
    except anthropic.APIConnectionError as exc:
        raise RuntimeError(f"Network error calling the Claude API: {exc}") from exc
    except anthropic.APIStatusError as exc:
        raise RuntimeError(f"Claude API error ({exc.status_code}): {exc.message}") from exc

    return _extract_json(response)
