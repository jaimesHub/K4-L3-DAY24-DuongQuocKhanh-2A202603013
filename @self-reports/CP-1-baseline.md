---
name: CP-1-baseline
date: 2026-10-12
checkpoint: 1
status: pending-approval
---

## Mục tiêu (Goal)
Hiểu được lỗ hổng cơ bản trong agent không có các biện pháp kiểm soát.

## Bối cảnh (Context)
- Checkpoint 1 yêu cầu phân tích tệp agent/loop.py và trả lời 3 câu hỏi cơ bản
- Ngân sách thời gian: 8 phút
- Sản phẩm: reports/baseline.md với 3 tham chiếu file:dòng

## Thay đổi (Changes)
- Phân tích hàm _naive_loop() trong agent/loop.py (dòng 27-54)
- Trả lời 3 câu hỏi cơ bản trong reports/baseline.md

## Kết quả kiểm chứng (Verification Results)

### Câu hỏi 1: Agent có danh tính persistent không?
- **Phát hiện:** Không có danh tính persistent
- **Bằng chứng:** agent/loop.py:27 `_naive_loop(message: str, llm)` không nhận principal_id; dòng 74 gọi nó mà không có danh tính
- **Trạng thái:** ✓ Chính xác

### Câu hỏi 2: Kiểm tra ủy quyền cho http_post?
- **Phát hiện:** Không có kiểm tra ủy quyền
- **Bằng chứng:** agent/loop.py:44 `tools.http_post(injected.target_url, ...)` không có authz; injection chỉ xuất hiện từ dòng 34
- **Trạng thái:** ✓ Chính xác

### Câu hỏi 3: Bằng chứng gửi dữ liệu sai?
- **Phát hiện:** Dòng 44 gửi các bản ghi qua sink đã được inject tới URL sai
- **Bằng chứng:** Dòng 39 đọc `tools.read_customer(customer_id)` từ injection, không từ yêu cầu của người dùng; gửi tới `injected.target_url`
- **Trạng thái:** ✓ Chính xác

## Phát hiện & điều chỉnh (Findings & Adjustments)
Tất cả các câu trả lời chỉ đến các dòng chính xác với bằng chứng thích hợp. Không cần điều chỉnh.

## Trạng thái hiện tại (Current Status)
- [x] reports/baseline.md hoàn thành với 3 câu trả lời
- [x] Tất cả tham chiếu file:dòng được xác minh so với mã thực tế
- [x] Sẵn sàng để người dùng phê duyệt

## Rủi ro & ghi chú (Risks & Notes)
Không có; phân tích cơ bản là đọc mã một cách đơn giản.

## Bước tiếp theo (Next Step)
Chờ phê duyệt từ người dùng để tiến hành Checkpoint 2 (Kho dữ liệu Red Team injection).
