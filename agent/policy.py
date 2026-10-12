"""BƯỚC 3b — PEP (Policy Enforcement Point) tại tool call (15').

Cổng chặn TRƯỚC KHI tool thật sự execute. Đọc CHECKPOINTS.md (§3b).

Interface bắt buộc (tests/test_policy.py và agent/runner.py gọi trực tiếp):

    check(context: PolicyContext) -> tuple[bool, str]
        Trả về (allow, reason).
        `reason` KHÔNG BAO GIỜ được để trống — cả khi allow=True và
        allow=False. Đây là evidence audit ở Bước 4 (rubric: "Audit
        completeness = 100%" — điều kiện trượt nếu có dòng thiếu reason).

PolicyContext — 5 input gốc và các input OBO cho lớp L3:

    data_classification: str   "public" | "internal" | "restricted"
    request_purpose: str       tự do, ví dụ "reconciliation", "support-reply"
    agent_owner: str            định danh agent/run gọi tool này
    delegation_depth: int       0 = gọi trực tiếp bởi user, >0 = agent gọi agent
    egress_enabled: bool        run hiện tại có được phép gọi network không
    principal_id: str           ID người ra lệnh từ data/principals.json
    requested_tool: str         tool sắp gọi
    agent_scopes: tuple[str]    quyền tối đa của agent
    parent_scopes: tuple[str]   quyền của agent cha khi delegation_depth > 0
    expires_at: str             ISO-8601 UTC; hết hạn phải deny

Rule TỐI THIỂU bắt buộc (không được viết yếu hơn rule này):

    classification == "restricted" and egress_enabled is True  ->  DENY

Checkpoint OBO: quyền hiệu lực = principal.allowed_tools ∩ agent_scopes,
và nếu depth > 0 thì còn giao với parent_scopes. Unknown principal, scope
thiếu, run hết hạn đều deny kèm reason. Principal là fixture mô phỏng,
không phải xác thực người dùng production.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("agent.policy")

PRINCIPALS_PATH = Path(__file__).resolve().parent.parent / "data" / "principals.json"
_PRINCIPALS_CACHE: dict | None = None


@dataclass(frozen=True)
class PolicyContext:
    data_classification: str
    request_purpose: str
    agent_owner: str
    delegation_depth: int
    egress_enabled: bool
    principal_id: str = ""
    requested_tool: str = ""
    agent_scopes: tuple[str, ...] = ()
    parent_scopes: tuple[str, ...] = ()
    expires_at: str = ""


def _load_principals() -> dict:
    """Load data/principals.json once (global cache). Fail-secure: {} on error."""
    global _PRINCIPALS_CACHE
    if _PRINCIPALS_CACHE is None:
        try:
            with open(PRINCIPALS_PATH, encoding="utf-8") as fh:
                data = json.load(fh)
            _PRINCIPALS_CACHE = data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}  # do not cache failures; retry next call, deny meanwhile
    return _PRINCIPALS_CACHE


def _parse_expiry(value) -> datetime | None:
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _decide(ctx: PolicyContext) -> tuple[bool, str]:
    classification = (ctx.data_classification or "").strip().lower()

    # Minimum mandatory rule: restricted data must never coexist with egress.
    if classification == "restricted" and ctx.egress_enabled is True:
        return False, ("restricted data with egress enabled is forbidden "
                       f"(tool '{ctx.requested_tool}', purpose '{ctx.request_purpose}')")

    if not ctx.principal_id:
        return False, "missing principal_id"
    if not ctx.requested_tool:
        return False, "missing requested_tool"
    if not (ctx.request_purpose or "").strip():
        return False, "missing request_purpose"
    if not ctx.agent_scopes:
        return False, "missing agent_scopes (no scope granted to agent)"
    if not ctx.expires_at:
        return False, "missing expires_at (no TTL on this run)"

    expiry = _parse_expiry(ctx.expires_at)
    if expiry is None:
        return False, f"invalid expires_at '{ctx.expires_at}' (not ISO-8601)"
    now = datetime.now(timezone.utc)
    if expiry < now:
        return False, f"TTL expired (expires_at {ctx.expires_at} < now {now.isoformat()})"

    principal = _load_principals().get(ctx.principal_id)
    if not isinstance(principal, dict):
        return False, f"principal '{ctx.principal_id}' not found in authorization database"

    tool = ctx.requested_tool
    allowed_tools = set(principal.get("allowed_tools", []))
    if tool not in allowed_tools:
        return False, f"{ctx.principal_id} not authorized for tool '{tool}'"
    if tool not in set(ctx.agent_scopes):
        return False, f"tool '{tool}' not in agent_scopes for agent '{ctx.agent_owner}'"

    if ctx.delegation_depth > 0 and tool not in set(ctx.parent_scopes):
        return False, f"tool '{tool}' not in parent_scopes for delegation_depth={ctx.delegation_depth}"

    purposes = principal.get("purposes")
    if purposes is not None and ctx.request_purpose not in set(purposes):
        return False, f"purpose '{ctx.request_purpose}' not permitted for principal '{ctx.principal_id}'"

    return True, (f"ALLOW: principal {ctx.principal_id} can use {tool} "
                  f"with purpose {ctx.request_purpose}")


def check(context: PolicyContext) -> tuple[bool, str]:
    """Return (allow, reason). Fail-secure; reason is never empty."""
    try:
        allow, reason = _decide(context)
    except Exception as exc:  # any unexpected error -> deny
        allow, reason = False, f"policy error, default deny: {type(exc).__name__}: {exc}"
    if not reason:
        allow, reason = False, "default deny: no reason produced"
    logger.info("policy %s principal=%s tool=%s: %s", "ALLOW" if allow else "DENY",
                getattr(context, "principal_id", ""), getattr(context, "requested_tool", ""), reason)
    return allow, reason
