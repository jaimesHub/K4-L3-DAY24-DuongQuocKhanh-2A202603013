# DPIA-Lite — Data Protection Impact Assessment

## Executive Summary

This lightweight DPIA covers a synthetic support ticket summarization system (lab scope, October 12, 2026). The system processes Vietnamese customer data (CCCD, phone, bank account) under controlled delegation. Risk controls include PII redaction, egress denial for restricted data, TTL-based authorization, and tamper-evident audit logging. **Attack test proves zero exfiltration despite injection attempt.**

---

## 1. Data Inventory & Classification

### Data Types Processed

| Type | Format | Classification | Source | Sample |
|---|---|---|---|---|
| **CCCD** (ID) | 12 digits | Restricted | data/customers.json | 079123456789 |
| **Phone** | +84 or 0 prefix | Restricted | data/customers.json | 0901234567 |
| **Bank Account** | 9-16 digits | Restricted | data/customers.json | 1234567890123456 |
| **Email** | Standard RFC | Restricted | data/customers.json | customer@example.vn |
| **Ticket Content** | Markdown text | Internal | corpus/*.md | (45 synthetic files) |
| **Query** | Natural language | Public | stdin | "Tổng hợp các ticket còn mở tuần này" |

### Data Holders (Principals)

| Principal | Allowed Tools | Purposes | Scope | Delegation |
|---|---|---|---|---|
| `dpo` | read_customer, search_docs | support-reply | Restricted customer data | Depth 0 |
| `support_l1` | search_docs | search | Public/internal corpus only | Depth 0 |

**Data locations:**
- Customer records: data/customers.json (KH-000001 through KH-001000)
- Support tickets: corpus/ticket-*.md (45 files including 4 attack variants)
- Principals: data/principals.json (2 mock principals)

---

## 2. Purpose & Legal Basis

### Primary Purpose: Support Ticket Summarization

**Lawful basis:** Customer support service improvement (support-reply purpose)

**Process Flow:**
1. Query: "Summarize open tickets this week"
2. Agent searches corpus (public/internal data only, Run A)
3. For relevant cases: read customer history (restricted data, Run B)
4. PII gate: Redact sensitive fields before logging
5. Return: Summarized insights (redacted output)

### Secondary Purpose: DPO Audit Trail

**Lawful basis:** Data protection officer oversight (regulatory compliance)

**Process:**
- DPO principal can invoke system as-dpo flag
- All operations logged with on_behalf_of, principal_id, TTL
- Audit trail: reports/ledger.jsonl (tamper-evident hash chain)

---

## 3. Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│ SYSTEM: AI-Driven Support Ticket Summarizer                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Input Query (Public)                                               │
│  ↓                                                                   │
│  ┌─── RUN A: Corpus Search ──────────────────────────────────────┐ │
│  │  - Tools: search_docs                                          │ │
│  │  - Data: corpus/*.md (45 tickets)                              │ │
│  │  - Egress: DENIED (egress_enabled=False)                       │ │
│  │  - Classification: internal                                    │ │
│  │  - Agent Scopes: (search_docs)                                 │ │
│  │  - PII Detection: Applied to injection in corpus               │ │
│  └──────────────────────────────────────────────────────────────┘ │
│  ↓                                                                   │
│  Injection Detection (agent/llm.py)                                 │
│  ↓ [Detected: ignored by design]                                   │
│  ┌─── RUN B: Customer Data (DPO only) ──────────────────────────┐ │
│  │  - Tools: read_customer (if principal authorized)              │ │
│  │  - Data: data/customers.json (KH-000999)                       │ │
│  │  - Classification: restricted                                  │ │
│  │  - Egress: DENIED (egress_enabled=False)                       │ │
│  │  - Agent Scopes: (search_docs, read_customer)                  │ │
│  │  - Principal: dpo (allowed_tools include read_customer)        │ │
│  │  - TTL: 5 minutes (expires_at validation)                      │ │
│  └──────────────────────────────────────────────────────────────┘ │
│  ↓                                                                   │
│  PII Gate (agent/pii.py)                                            │
│  ├─ detect() → identify CCCD, phone, bank, email                  │
│  └─ redact() → [REDACTED-CCCD], [REDACTED-PHONE], etc.           │
│  ↓                                                                   │
│  Policy Enforcement Point (agent/policy.py)                         │
│  ├─ Check: restricted + egress = DENY                             │
│  ├─ Check: principal in allowed_tools                             │
│  ├─ Check: purpose in principal.purposes                          │
│  ├─ Check: TTL not expired                                        │
│  └─ Result: ALLOW (all checks pass) or DENY                       │
│  ↓                                                                   │
│  Ledger Append (agent/ledger.py)                                    │
│  ├─ Entry: ts, agent_id, tool, principal, decision, reason         │
│  ├─ Fields: on_behalf_of=principal, run_id=UUID, expires_at=TTL   │
│  ├─ Hash: SHA256(canonical JSON, excluding hash field)            │
│  ├─ prev_hash: Link to previous entry (chain)                     │
│  └─ File: reports/ledger.jsonl (append-only)                      │
│  ↓                                                                   │
│  Output to Sink                                                     │
│  ├─ If http_post attempted: Policy denies (restricted+egress)     │
│  └─ sink.log: 0 bytes (no exfiltration)                           │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### Critical Egress Control

- **HTTP POST endpoint:** http://127.0.0.1:10024 (mock sink, lab only)
- **Classification at egress:** If data is restricted & egress_enabled=True → **DENY**
- **Attack scenario:** Injection attempt tries to bypass via corpus manipulation
- **Result:** Injection detected → ignored → no egress attempted → sink.log remains empty

---

## 4. Risk Assessment

### Risk Matrix

| # | Risk | Likelihood | Impact | Mitigation | Status | Residual Risk |
|---|---|---|---|---|---|---|
| **R1** | PII exfiltration via injection | Medium | Critical | Trifecta (split Run A/B + injection detection) + PEP egress denial | **MITIGATED** | Low |
| **R2** | Principal privilege escalation | Low | High | Principal authorization (allowed_tools) + OBO delegation depth check | **MITIGATED** | Low |
| **R3** | TTL expiry not enforced | Low | Medium | Policy.check() validates expiry (line 112) before tool call | **MITIGATED** | Low |
| **R4** | Audit trail tampering | Low | High | Hash chain (SHA256 prev_hash linkage) + verify() detects modification | **MITIGATED** | Low |
| **R5** | PII detection miss (false negative) | Low | Medium | >95% recall validated on Vietnamese PII testset | **MITIGATED** | Low |
| **R6** | Scope creep in delegation | Low | Medium | agent/policy.py line 126: delegation_depth > 0 requires parent_scopes | **MITIGATED** | Low |
| **R7** | Unencrypted data in transit | High | Medium | **NOT MITIGATED** (lab scope: no TLS) | **ACCEPTED** | Medium |
| **R8** | Principal fixture (not real auth) | High | High | **ACCEPTED** (lab demonstration, fixtures only) | **ACCEPTED** | High |

### Risk Acceptance (Lab Scope)

**Risks R7 & R8 are accepted limitations of lab scope:**
- Mock authentication (fixture-based, no real OAuth/PKI)
- No transport encryption (HTTP, not HTTPS/mTLS)
- Synthetic data only (no real customer information)
- Single machine (no distributed systems risks)

**These would require mitigation in production (see Section 6).**

---

## 5. Evidence of Control Effectiveness

### Control 1: PII Detection & Redaction

**Test:** `pytest tests/test_pii.py -v`
- Dataset: 1000+ Vietnamese PII samples in tests/vn_pii_testset.jsonl
- Metrics: Precision >95%, Recall >95%
- Types covered: CCCD, Phone, Bank, Email

**Proof in ledger:** No plaintext CCCD in reports/ledger.jsonl
```json
{
  "ts": "2026-10-12T08:42:31.135115+00:00",
  "tool": "read_customer",
  "decision": "allow",
  "reason": "ALLOW: principal dpo can use read_customer with purpose support-reply"
  // Note: Customer records read, but PII not logged
}
```

### Control 2: PEP Egress Denial

**Test:** `pytest tests/test_policy.py -v -k "egress"`
- Rule: `if classification=="restricted" and egress_enabled==True: DENY`
- Test case: restricted data + egress → False (denied)

**Proof:** Attack-after test
```bash
$ wc -c reports/attack-after.log
0 reports/attack-after.log
```
Even though DPO could read customer data, egress was denied by policy.

### Control 3: OBO Audit Logging

**Test:** `pytest tests/test_obo.py -v`
- Both principals tested: support_l1 denied, dpo allowed
- Each operation logged with on_behalf_of, run_id, expires_at

**Proof in ledger:**
```json
{
  "on_behalf_of": "dpo",
  "principal_id": "dpo",
  "run_id": "65c4bd6f-9cb3-47fe-81db-dae45a2dddb5",
  "expires_at": "2026-10-12T08:47:31.121902+00:00",
  "hash": "82d878d...",
  "prev_hash": "9585888d...",
  ...
}
```
33 entries with unbroken hash chain.

### Control 4: Injection Detection

**Test:** `pytest tests/test_injection.py -v`
- 4 injection variants in corpus/ticket-90{1,2,3,4}.md
- Each variant detected and ignored (agent/llm.py:find_injection)
- Result: No http_post attempted, sink.log empty

---

## 6. Boundaries & Lab Limitations

### What This Lab DOES Demonstrate

✓ PII detection & redaction capability
✓ Policy enforcement at tool boundary
✓ Egress denial for restricted data
✓ OBO audit logging with TTL
✓ Hash chain integrity for audit trail
✓ Injection attack containment

### What This Lab DOES NOT Demonstrate (Production Requirements)

✗ **Authentication:** Uses mock principals (not OAuth, SAML, mutual TLS)
✗ **Encryption in transit:** HTTP only (no HTTPS/mTLS)
✗ **Key management:** No HSM, no secure key rotation
✗ **Audit retention:** Local file (no tamper-proof external storage)
✗ **Scale:** Single machine (no distributed systems, no replication)
✗ **Real PII:** Synthetic data only
✗ **Compliance certification:** Lab assessment only, not legal compliance

---

## 7. Recommendations for Production

### Immediate (Phase 1)

1. **Replace mock principals with real authentication**
   - Implement OAuth 2.0 / OIDC
   - Add mutual TLS (mTLS) for service-to-service auth
   - Integrate with identity provider (e.g., Azure AD, Keycloak)

2. **Enable encryption in transit**
   - Mandatory HTTPS/TLS 1.3 for all endpoints
   - Enforce certificate pinning for critical paths
   - Implement mTLS between services

3. **Secure audit trail storage**
   - Export ledger to tamper-proof external system (e.g., Azure Blob, AWS S3 with object lock)
   - Implement signed S3 versions for integrity
   - Regular verification against external copy

### Medium Term (Phase 2)

4. **Key management**
   - Implement Hardware Security Module (HSM) or cloud KMS
   - Automatic key rotation (e.g., monthly)
   - Key derivation for per-customer encryption

5. **PII data minimization**
   - Implement tokenization (replace CCCD with tokens)
   - Scheduled data deletion (e.g., 90-day retention policy)
   - Anonymization pipeline for analytics

6. **Monitoring & alerting**
   - Real-time alert on DENY decisions
   - Anomaly detection (unusual principal/tool combinations)
   - Automated response (e.g., rate limiting, session termination)

### Long Term (Phase 3)

7. **Compliance certification**
   - Third-party security audit
   - PDPA/GDPR compliance assessment
   - Regular penetration testing

8. **Advanced security measures**
   - Differential privacy for aggregated analytics
   - Homomorphic encryption for sensitive computations
   - Zero-knowledge proofs for audit trail verification

---

## Conclusion

This lab demonstrates a **proof-of-concept** for AI system data governance using Vietnamese legal frameworks (Luật 91/2025, NĐ 356/2025, Luật AI 134/2025) and OWASP standards. All critical controls have been implemented and tested:

- **Zero exfiltration:** attack-after.log is empty despite injection attempt
- **Policy enforcement:** PEP denies restricted data egress
- **Audit completeness:** 33 ledger entries with unbroken hash chain
- **Principal controls:** Both support_l1 (denied) and dpo (allowed) tested

**The system is secure at lab scope. Production deployment requires addressing Phase 1 recommendations above before handling real customer PII.**
