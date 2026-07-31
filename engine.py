"""Backwards compatible re-export; the implementation lives in :mod:`ti.engine`."""

from ti.engine import ActionResult, Engine, RuleError

__all__ = ["Engine", "ActionResult", "RuleError"]
