"""Scanner query engine.

Refuses a switched-off metric, a ranking that is not comparable, a missing
value treated as a pass or a fail, and any weight, backtest or deploy key.
"""

from woong.engine.run import run_query
from woong.engine.types import QueryError, QueryResult

__all__ = ["QueryError", "QueryResult", "run_query"]
