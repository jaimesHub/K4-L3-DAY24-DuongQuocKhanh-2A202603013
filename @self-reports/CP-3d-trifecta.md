---
name: CP-3d-trifecta
date: 2026-10-12
checkpoint: 3d
status: approved
---

## Mục tiêu
Implement Trifecta Split — phân tách Run B để suy ra customer_id chỉ từ nguồn tin cậy (ticket_id → related_tickets), không từ free text.

## Thay đổi
- tests/test_split.py: Kiểm chứng containment (chứ không chỉ mitigation)
- Trifecta Split đảm bảo Run B chỉ đọc customer có liên quan qua ticket_id → related_tickets
- Attacker không thể ép runner đọc PII của khách chỉ bằng cách đề cập customer_id trong free text

## Kết quả kiểm chứng
tests/test_split.py: 1/1 passed
- ✓ test_split_never_reads_a_customer_named_only_by_the_attacker

## Giải thích kỹ thuật
Run B suy ra customer_id từ:
1. Tên file ticket (ticket-906.md) → ticket_id
2. Lookup related_tickets cho ticket_id đó
3. Chỉ đọc customer nằm trong related_tickets

Attacker không thể chèn customer_id:
- Không chứa "read_customer" string → bypass URL/tool name filter
- Không chứa URL → bypass mitigation based filters
- Khách KH-000777 có `related_tickets: []` → KHÔNG THỂ bị đọc
- CONTAINMENT: dữ liệu không bao giờ bị đọc (chứ không phải read rồi giữ lại)

## Trạng thái
- [x] Trifecta Split kiểm chứng ✓
- [x] tests/test_split.py: 1/1 PASSED ✓
- [x] Ready for commitment

## Ghi chú
Khác biệt giữa MITIGATION vs CONTAINMENT:
- MITIGATION: phát hiện rồi từ chối gửi → dữ liệu vẫn bị đọc
- CONTAINMENT: Run B suy ra từ trusted source → dữ liệu không bao giờ bị đọc
