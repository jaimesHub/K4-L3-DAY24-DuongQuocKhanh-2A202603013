# Baseline — điền trong checkpoint 1

1. Agent có identity mỗi run chưa? Dẫn file/hàm:
   **No:** `agent/loop.py:27` defines `_naive_loop(message: str, llm)` with no `principal_id` parameter; line 74 calls it without passing identity, so baseline lacks persistent identity across runs.

2. Ai cho phép `http_post`? Dẫn file/hàm:
   **No one:** `agent/loop.py:44` calls `tools.http_post(injected.target_url, ...)` with no authorization check; the URL and customer_ids come from `llm.find_injection()` at line 34, driven entirely by injected text.

3. Nếu gửi sai PII ra sink, bằng chứng ở đâu? Dẫn file/hàm:
   **Line 44 sends to injected sink:** `tools.http_post(injected.target_url, {"records": collected})` posts records at line 39 read by `tools.read_customer(customer_id)` with no relation to user's legitimate request.
