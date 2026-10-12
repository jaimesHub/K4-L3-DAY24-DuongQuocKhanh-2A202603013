# Compliance Control Mapping — CP-5

## Summary

| Luật / Tiêu chuẩn | Control | Evidence File:Line | Trạng thái |
|---|---|---|---|
| **Luật 91/2025/QH15** (Luật bảo vệ dữ liệu cá nhân) | PII Detection & Redaction | agent/pii.py:31-76, tests/test_pii.py | ✓ Implemented |
| **NĐ 356/2025/NĐ-CP** (Quy định địa phương hoá dữ liệu) | Policy Enforcement: Restricted data + Egress = DENY | agent/policy.py:92-95, tests/test_policy.py | ✓ Implemented |
| **Luật AI 134/2025/QH15** (Luật minh bạch AI) | OBO Audit Logging with Principal, Scope, TTL | agent/ledger.py:73-110, tests/test_obo.py | ✓ Implemented |
| **OWASP API Security Top 10** (API1, API3, API4) | Injection Prevention, Auth Enforcement, Field-Level Access | agent/runner.py, agent/policy.py, agent/pii.py, tests/ | ✓ Implemented |

---

## Detailed Control Mapping

### 1. Luật 91/2025/QH15 — Law on PII Protection

**Quy định:** Bảo vệ, xử lý, truyền tải dữ liệu cá nhân cần kiểm soát chặt chẽ; cấm tách rời và rò rỉ.

**Control Implemented:** 
- **PII Detection** (agent/pii.py:31-62)
  - Detects 4 types: CCCD (12-digit), Phone (+84/0 prefix), Bank Account (9-16 digit), Email
  - Regex patterns at lines 8-16
  - Test coverage: tests/vn_pii_testset.jsonl validates >95% precision & recall
  
- **PII Redaction** (agent/pii.py:65-76)
  - Masks all detected PII with [REDACTED-{type}] tokens (line 74)
  - Applied to all data flows before logging

**Proof:**
- Test suite: `pytest tests/test_pii.py -v` passes with >95% recall on Vietnamese data
- Attack-after verification: reports/attack-after.log is **0 bytes** (no PII exfiltrated)
- Ledger check: No plaintext CCCD, STK, or phone in reports/ledger.jsonl

---

### 2. NĐ 356/2025/NĐ-CP — Decree on Data Localization

**Quy định:** Dữ liệu phân loại ("restricted") không được phép rời khỏi hệ thống; egress bị cấm.

**Control Implemented:**
- **Mandatory Egress Denial Rule** (agent/policy.py:89-95)
  - Line 93-95: `if classification == "restricted" and ctx.egress_enabled is True: return False`
  - Classification tracked: public, internal, restricted
  - Egress flag: False for Run A (corpus), False for Run B (customer read)
  - If http_post attempted with restricted data: DENY with reason

**Proof:**
- Test case: tests/test_policy.py validates restricted+egress=DENY
- Ledger entries: reports/ledger.jsonl shows 0 http_post ALLOW entries (none attempted)
- DPO principal: Can read customer (classification=restricted, egress=False) → ALLOW
- Policy enforcement: Even privilege-escalation attempt blocked by egress check

---

### 3. Luật AI 134/2025/QH15 — Law on AI Transparency

**Quy định:** AI hệ thống phải minh bạch về quyền, ai quyết định, thời hạn, audit trail.

**Control Implemented:**

- **OBO (On-Behalf-Of) Logging** (agent/ledger.py:73-84, agent/runner.py)
  - Captures: `principal_id` (who), `agent_owner` (which agent), `run_id` (execution ID)
  - Fields: on_behalf_of, principal_id, delegation_depth, expires_at, reason
  - Every tool call logged with full context

- **TTL Enforcement** (agent/policy.py:108-113)
  - Line 112: `if expiry < now: return False` (automatic expiry denial)
  - All runs have 5-minute TTL (expires_at in ledger)
  - Test case: tests/test_obo.py:39 validates expired tokens denied

- **Hash Chain (Tamper Evidence)** (agent/ledger.py:47-84)
  - SHA256 hash chain: line 79 `record["hash"] = _compute_hash(record)`
  - prev_hash links entries (line 78)
  - Verification: agent/ledger.py:87-110 detects any modification

**Proof:**
- Ledger integrity: Verified with `python -c "from agent.ledger import verify; from pathlib import Path; print(verify(Path('reports/ledger.jsonl')))"` → True
- OBO entries: reports/ledger.jsonl contains 33 entries with complete audit context
- Principal tracking: Each entry includes "on_behalf_of": "dpo" (OBO principal)
- TTL validation: All entries have expires_at with 5-minute windows
- Hash chain unbroken: No tampering detected in hash chain verification

---

### 4. OWASP API Security Top 10

**API1 (Injection Prevention)**
- Control: Trifecta split (corpus ≠ customer data) + injection detection
- Implementation: agent/runner.py (Run A vs Run B split), agent/llm.py (find_injection)
- Evidence: tests/test_injection.py replays 4 injection variants, all blocked
- Proof: reports/attack-after.log empty (0 bytes) despite injection attempt

**API3 (Broken Authentication)**
- Control: Principal-based access control with scope validation
- Implementation: agent/policy.py:119-127 (tool in allowed_tools, agent_scopes, parent_scopes)
- Evidence: tests/test_obo.py:25-40 (support_l1 denied, dpo allowed)
- Proof: support_l1 cannot read_customer (not in allowed_tools); dpo can for support-reply purpose

**API4 (Unrestricted Resource Access)**
- Control: Field-level PII redaction
- Implementation: agent/pii.py:65-76 (redact function), applied to all outputs
- Evidence: tests/test_pii.py validates 95%+ coverage on Vietnamese PII types
- Proof: No plaintext CCCD/phone/STK in any logs or outputs; attack-after.log confirms 0-byte sink

---

## Test Verification Results

```
Full test suite: 33 passed
- test_pii.py: Precision >95%, Recall >95%
- test_policy.py: Mandatory rule (restricted+egress=DENY) enforced
- test_obo.py: Both principals tested; TTL, scope, delegation validated
- test_injection.py: 4/4 injection variants blocked; attack-after.log empty
- test_ledger.py: Hash chain integrity verified
```

**Ledger Verification:**
```
reports/ledger.jsonl: 33 entries, all valid
- All entries have non-empty reason
- Hash chain unbroken (prev_hash → hash sequence)
- Principal tracking complete (on_behalf_of field present)
- TTL tracking complete (expires_at present)
```

**Attack-After Verification:**
```
reports/attack-after.log: 0 bytes
Proof: No PII exfiltrated despite:
  1. Injection attempt (4 variants in corpus)
  2. Legitimate read_customer by dpo principal
  3. Policy would deny http_post if attempted
```

---

## Boundaries & Limitations

This assessment covers **lab scope only** (synthetic data, mock principals, no TLS/PKI):
- Principals are mocked fixtures (not real authentication)
- Data is synthetic (no real customer PII processed)
- TLS/encryption not implemented (lab demonstration only)
- Production deployment would require additional controls:
  - Real authentication mechanism (OAuth, mutual TLS, etc.)
  - Encrypted transport (HTTPS, mTLS)
  - Hardware security module (HSM) for cryptographic keys
  - Audit trail stored in tamper-proof external system
  - Real PII governance & retention policies
  - Regular security audits & penetration testing
