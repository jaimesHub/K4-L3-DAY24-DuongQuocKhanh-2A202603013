"""BƯỚC 3d — audit ledger append-only, tamper-evident (10').

JSONL, mỗi tool call một dòng. Đọc CHECKPOINTS.md (§3d).

Interface bắt buộc (tests/test_ledger.py và agent/runner.py gọi trực tiếp):

    append(entry: dict, path: pathlib.Path) -> dict
        `entry` phải có tối thiểu các field:
            ts, agent_id, run_id, tool, args_hash, classification,
            decision, reason
        Hàm tự thêm 2 field:
            prev_hash  = hash của dòng ngay trước trong file này, hoặc
                         "0" * 64 nếu là dòng đầu tiên
            hash       = sha256 tính từ nội dung dòng NÀY (bao gồm cả
                         prev_hash, KHÔNG bao gồm field hash) — dùng
                         json.dumps(..., sort_keys=True) trước khi hash
                         để thứ tự field không ảnh hưởng kết quả.
        Append 1 dòng JSON (utf-8, ensure_ascii=False) vào cuối `path`,
        tạo file/thư mục cha nếu chưa có. Trả về dict đầy đủ đã ghi
        (bao gồm prev_hash/hash).

    verify(path: pathlib.Path) -> bool
        Đọc toàn bộ file, trả về True nếu TẤT CẢ đều đúng:
          - mọi dòng có `reason` non-empty
          - prev_hash của dòng n == hash đã lưu của dòng n-1 (dòng đầu so
            với "0" * 64)
          - hash lưu trong dòng n khớp lại khi tính lại từ nội dung dòng đó
        Trả về False nếu một dòng còn trong file bị sửa mà không tính lại
        hash, nếu xoá/chèn giữa file làm đứt liên kết, hoặc thiếu reason.
        Chỉ kiểm tra file hiện có KHÔNG phát hiện được việc xoá dòng cuối
        hoặc viết lại cả file và tính lại chuỗi. Muốn phát hiện cắt đuôi
        phải lưu hash/số dòng cuối ở một nơi tin cậy bên ngoài file rồi
        đối chiếu. Bài lab không cung cấp mốc đó.

Sinh viên phải tự tay chứng minh được: sửa 1 ký tự trong 1 dòng giữa file
rồi gọi verify() phải trả về False.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

GENESIS_HASH = "0" * 64


def _compute_hash(entry: dict) -> str:
    """sha256 over canonical JSON of the entry, excluding the `hash` field."""
    body = {k: v for k, v in entry.items() if k != "hash"}
    payload = json.dumps(body, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _last_hash(path: Path) -> str:
    """Hash of the last non-blank line in `path`, or GENESIS_HASH if none."""
    if not path.exists():
        return GENESIS_HASH
    last = None
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                last = line
    if last is None:
        return GENESIS_HASH
    # A corrupt tail must not be silently chained onto: let this raise.
    prev = json.loads(last)["hash"]
    if not isinstance(prev, str) or not prev:
        raise ValueError("ledger tail has no valid hash")
    return prev


def append(entry: dict, path: Path) -> dict:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    record = {k: v for k, v in entry.items() if k != "hash"}
    record["prev_hash"] = _last_hash(path)
    record["hash"] = _compute_hash(record)

    line = json.dumps(record, sort_keys=True, ensure_ascii=False)
    with path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(line + "\n")
    return record


def verify(path: Path) -> bool:
    try:
        path = Path(path)
        expected_prev = GENESIS_HASH
        with path.open("r", encoding="utf-8") as f:
            for raw in f:
                raw = raw.strip()
                if not raw:
                    continue
                entry = json.loads(raw)
                if not isinstance(entry, dict):
                    return False
                reason = entry.get("reason")
                if not isinstance(reason, str) or not reason.strip():
                    return False
                stored = entry.get("hash")
                if not isinstance(stored, str) or entry.get("prev_hash") != expected_prev:
                    return False
                if _compute_hash(entry) != stored:
                    return False
                expected_prev = stored
        return True
    except Exception:
        return False
