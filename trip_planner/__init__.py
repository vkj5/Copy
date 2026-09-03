"""Trip planning research agent.

Given a destination, a set of travel dates, and a budget, this package uses
Claude with the web search tool to find flight, accommodation, and activity
options and return them as a single structured JSON document.
"""

from .agent import TripPlanRequest, plan_trip

__all__ = ["TripPlanRequest", "plan_trip"]
