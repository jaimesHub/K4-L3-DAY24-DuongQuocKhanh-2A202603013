"""BƯỚC 3c — trifecta split + egress allowlist (13'). ĐÂY LÀ PHẦN KHÓ NHẤT.

Đọc CHECKPOINTS.md (§3c) trước khi viết code. Tóm tắt yêu cầu:

Tách 1 yêu cầu người dùng thành ít nhất 2 run riêng biệt — KHÔNG run nào
được cầm cả 3 chân của trifecta cùng lúc:

    Run A: gọi search_docs (untrusted content).
           KHÔNG gọi read_customer. KHÔNG gọi http_post.
    Run B: gọi read_customer (private data).
           CHỈ nhận input là TYPED, ĐÃ SANITIZE từ Run A — ví dụ
           list[int] ticket id trích từ TÊN FILE (vd "ticket-007.md" -> 7),
           KHÔNG BAO GIỜ nhận nguyên văn text của document. free text của
           attacker không được đi xa hơn Run A.

Mọi lần gọi tool (allow HAY deny) phải:
  1. Đi qua `agent.policy.check()` TRƯỚC KHI tool thật sự chạy.
  2. Được ghi vào ledger qua `agent.ledger.append()` — cả khi deny.
Nếu policy deny, KHÔNG được gọi tool đó.

--- Gợi ý kiến trúc (không bắt buộc theo đúng, nhưng đủ để làm trong 13') ---

data/customers.json có field `related_tickets: list[int]` cho mỗi khách
hàng — đây là NGUỒN TIN CẬY để map ticket_id -> customer_id, KHÔNG map qua
customer_id mà attacker nhúng trong nội dung document. Cụ thể:

    Run A: search_docs(message) -> lấy list[int] ticket_id từ TÊN FILE của
           các doc khớp (vd "ticket-999.md" -> 999). Cũng chạy
           llm.find_injection() trên text để log lại (KHÔNG dùng
           customer_id mà nó trả về).
    Run B: với mỗi ticket_id nhận từ Run A, tìm customer nào trong
           customers.json có ticket_id trong related_tickets, rồi
           read_customer(customer_id) đó — không phải customer_id lấy từ
           text tự do.

Vì sao cách này chống được một chỉ thị viết không dấu / lookalike: filter
chuỗi thô sẽ luôn có thể bị né bằng cách viết lại chỉ thị, nhưng nếu Run B
không bao giờ ĐỌC free text để quyết định gọi ai, thì việc né filter chuỗi
trở nên vô nghĩa — đây là containment (kiến trúc), khác với mitigation
(bộ lọc). Sinh viên NÊN thử filter chuỗi trước, rồi tự phá nó bằng
một bản viết lại không dấu của lure, trước khi chuyển sang cách này.

Interface bắt buộc (agent/loop.py import và gọi hàm này nếu tồn tại):

    handle(message: str, llm, log_dir: pathlib.Path | None = None,
           principal_id: str = "support_l1") -> str
        `llm` cung cấp:
            llm.find_injection(text: str) -> InjectedInstruction | None
            llm.summarize(docs: list[dict]) -> str
        `log_dir` là thư mục chứa ledger.jsonl (mặc định: reports/).
        Mỗi tool call truyền principal_id, requested_tool, agent_scopes,
        parent_scopes và expires_at vào PolicyContext; ledger ghi
        on_behalf_of = principal_id, agent_id, run_id, expires_at.
        Principal chỉ được tra trong data/principals.json. Run B không
        được đọc customer cho support_l1; dpo vẫn đọc được khách hợp lệ.
        Trả về câu trả lời cuối cùng hiển thị cho người dùng — hành vi
        quan sát được từ ngoài (CLI) không đổi so với trước khi contain,
        chỉ có sink log và ledger là khác.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from agent import ledger, tools
from agent.policy import PolicyContext, check

logger = logging.getLogger("agent.runner")

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
DEFAULT_LEDGER_PATH = REPORTS_DIR / "ledger.jsonl"
CUSTOMERS_FILE = Path(__file__).resolve().parent.parent / "data" / "customers.json"

RUN_TTL = timedelta(minutes=5)
# Only digits from a bare corpus filename are ever accepted from Run A.
_TICKET_FILENAME_RE = re.compile(r"^ticket-(\d{1,9})\.md$")

# Run A holds the untrusted-content leg only; Run B holds the private-data leg
# only. Neither run has egress, and no run ever has http_post in scope.
RUN_A_SCOPES = ("search_docs",)
RUN_B_SCOPES = ("read_customer",)


class RunnerScaffoldPending(NotImplementedError):
    """Only the original 3c stub used this to enable the CP1/CP2 baseline."""


def _args_hash(args: dict) -> str:
    raw = json.dumps(args, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _guarded_call(*, tool_name: str, args: dict, fn, run_id: str, agent_id: str,
                  principal_id: str, purpose: str, classification: str,
                  agent_scopes: tuple[str, ...], expires_at: str,
                  ledger_path: Path):
    """Policy check -> ledger append -> (only if allowed) execute the tool.

    Returns (allowed, result). The ledger entry is written BEFORE the tool
    runs, so a tool call that cannot be audited never executes.
    """
    context = PolicyContext(
        data_classification=classification,
        request_purpose=purpose,
        agent_owner=agent_id,
        delegation_depth=0,
        egress_enabled=False,
        principal_id=principal_id,
        requested_tool=tool_name,
        agent_scopes=agent_scopes,
        parent_scopes=(),
        expires_at=expires_at,
    )
    allow, reason = check(context)
    ledger.append({
        "ts": datetime.now(timezone.utc).isoformat(),
        "agent_id": agent_id,
        "run_id": run_id,
        "tool": tool_name,
        "args_hash": _args_hash(args),
        "classification": classification,
        "decision": "allow" if allow else "deny",
        "reason": reason or "no reason produced",
        "on_behalf_of": principal_id,
        "expires_at": expires_at,
    }, ledger_path)
    if not allow:
        return False, None
    try:
        return True, fn()
    except tools.ToolError as exc:
        logger.warning("tool %s failed after allow: %s", tool_name, exc)
        return True, None


def _ticket_ids_from_docs(docs: list[dict]) -> list[int]:
    """Sanitize Run A output down to typed ints taken from file NAMES only."""
    ids: list[int] = []
    for doc in docs:
        match = _TICKET_FILENAME_RE.match(str(doc.get("id", "")))
        if match:
            ticket_id = int(match.group(1))
            if ticket_id not in ids:
                ids.append(ticket_id)
    return ids


def _customers_for_tickets(ticket_ids: list[int]) -> list[str]:
    """Trusted mapping ticket_id -> customer_id via customers.json."""
    wanted = set(ticket_ids)
    customers = json.loads(CUSTOMERS_FILE.read_text(encoding="utf-8"))
    found: list[str] = []
    for record in customers:
        related = record.get("related_tickets") or []
        if wanted.intersection(related):
            customer_id = str(record["customer_id"])
            if customer_id not in found:
                found.append(customer_id)
    return found


def handle(message: str, llm, log_dir: Path | None = None,
           principal_id: str = "support_l1") -> str:
    ledger_path = (Path(log_dir) / "ledger.jsonl") if log_dir else DEFAULT_LEDGER_PATH
    run_id = str(uuid.uuid4())
    expires_at = (datetime.now(timezone.utc) + RUN_TTL).isoformat()

    common = dict(run_id=run_id, principal_id=principal_id,
                  expires_at=expires_at, ledger_path=ledger_path)

    # ---- Run A: untrusted content only (no read_customer, no http_post) ----
    allowed, docs = _guarded_call(
        tool_name="search_docs", args={"query": message},
        fn=lambda: tools.search_docs(message),
        agent_id="lab24-agent/run-a", purpose="summarize-tickets",
        classification="internal", agent_scopes=RUN_A_SCOPES, **common)
    if not allowed:
        return "Request denied by policy."
    docs = docs or []

    # Detection is logged only; its customer_ids/target_url are never used.
    try:
        injected = llm.find_injection("\n\n".join(d["text"] for d in docs))
    except Exception as exc:  # detection is best-effort telemetry
        logger.warning("find_injection failed: %s", exc)
        injected = None
    if injected is not None:
        logger.warning("injection detected in corpus (markers=%s); ignored by design",
                       getattr(injected, "matched_markers", []))

    # Boundary: only list[int] derived from filenames crosses A -> B.
    ticket_ids = _ticket_ids_from_docs(docs)

    # ---- Run B: private data, input is sanitized ticket ids only ----
    for customer_id in _customers_for_tickets(ticket_ids):
        ok, _record = _guarded_call(
            tool_name="read_customer", args={"customer_id": customer_id},
            fn=lambda cid=customer_id: tools.read_customer(cid),
            agent_id="lab24-agent/run-b", purpose="support-reply",
            classification="restricted", agent_scopes=RUN_B_SCOPES, **common)
        if not ok:
            continue
        # Record is used for nothing further: no egress and no free-text
        # round trip. It is dropped here (copy not retained).

    return llm.summarize(docs)
