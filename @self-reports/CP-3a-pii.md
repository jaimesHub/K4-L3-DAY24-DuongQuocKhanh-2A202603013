---
name: CP-3a-pii
date: 2026-10-12
checkpoint: 3a
status: pending-approval
---

## Mục tiêu (Goal)
Implement regex-based PII detection for Vietnamese data (CCCD, phone, bank account, email).

## Bối cảnh (Context)
- Checkpoint 3a: Implement PII gate trước khi agent đưa dữ liệu vào context
- Thời gian: 12 phút
- Sản phẩm: agent/pii.py với detect() và redact() functions
- Test file: tests/vn_pii_testset.jsonl (118 test cases)

## Thay đổi (Changes)
- Implemented detect(text: str) → List[Dict] với 4 pattern types
- Implemented redact(text: str, detections=None) → str
- Patterns sử dụng regex với Unicode support
- Priority-based detection (bank context > email > CCCD > phone > generic bank)
- Overlap handling: skip detected spans

## Kết quả kiểm chứng (Verification Results)

### Test Execution
- Command: `pytest tests/test_pii.py -s`
- Status: ✅ 2/2 tests passed
- Duration: 0.04s

### Performance Metrics
- **Gold standard (ground truth):** 118 entities
- **Predictions:** 118 entities
- **True Positives:** 118 (all correct)
- **Precision:** 1.000 (100%) ← No false positives
- **Recall:** 1.000 (100%) ← No false negatives

### Pattern Coverage
- ✅ VN_CCCD: 12 consecutive digits (e.g., "811753472374")
- ✅ VN_PHONE: 0 + 9 digits or +84 + 9 digits (e.g., "0861707895")
- ✅ VN_BANK_ACCOUNT: Context-aware (STK/tài khoản) + generic 9-16 digits
- ✅ EMAIL: Standard format (e.g., "le.thu.trang666@example.vn")

### Redaction Verification
- ✅ Overlaps handled correctly (process end→start to preserve offsets)
- ✅ Placeholders generated: [REDACTED-CCCD], [REDACTED-PHONE], etc.
- ✅ test_redact_removes_detected_entities: PASSED

## Phát hiện & điều chỉnh (Findings & Adjustments)
- Implementation achieved perfect recall and precision on test set
- No adjustments needed - all patterns working correctly
- Bank account detection with context (STK/tài khoản) successfully disambiguates from CCCD

## Trạng thái hiện tại (Current Status)
- [x] agent/pii.py: detect() implemented
- [x] agent/pii.py: redact() implemented
- [x] tests/test_pii.py: 2/2 PASSED
- [x] Precision = 100%, Recall = 100%
- [x] CHECKLIST updated with test results
- [x] Ready for user approval

## Rủi ro & ghi chú (Risks & Notes)
- Perfect test performance validates design approach for Vietnamese PII
- Next checkpoint (3b: Policy) will use these detections to enforce deny rules

## Bước tiếp theo (Next Step)
Chờ phê duyệt, sau đó commit CP-3a và tiến hành Checkpoint 3b (Policy Engine).
