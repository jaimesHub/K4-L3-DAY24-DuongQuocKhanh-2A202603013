# Secret giả trong lịch sử Git — CP-4 Supply Chain & Secrets

## Scanner và phiên bản
- **Scanner**: Gitleaks (gitleaks binary)
- **Phiên bản**: v8.30.1
- **Config file**: `.gitleaks.toml` (custom rule `lab24-synthetic-token`)

## Commit chứa token giả
- **Commit hash**: `1bdd849922156c868a5ee9293d68f5b72e242d2c`
- **Commit message**: `chore: seed student lab with synthetic secret exercise`
- **Author**: VinUni AI20k Lab <lab@users.noreply.github.com>
- **Date**: 2026-10-09T16:22:06Z
- **Status**: Đã xoá từ HEAD, chỉ tồn tại trong lịch sử

## File, rule và kết quả quét lịch sử
- **File chứa secret**: `lab-fake-secret.txt` (line 1)
- **Rule triggered**: `lab24-synthetic-token`
- **Pattern**: `LAB24_FAKE_TOKEN=LAB24-DEMO-[A-Z0-9]{16}`
- **Entropy**: 4.600922
- **Kết quả**: ✓ **1 finding found** (exactly as expected)
- **Commit scan**: 10 commits scanned, ~215.79 KB scanned in 351ms
- **Fingerprint**: `1bdd849922156c868a5ee9293d68f5b72e242d2c:lab-fake-secret.txt:lab24-synthetic-token:1`

## Kết quả quét file hiện tại
- **Scan type**: Directory scan (`gitleaks dir --config .gitleaks.toml .`)
- **Status**: ✓ **No leaks found** (clean)
- **Bytes scanned**: ~321.20 KB
- **Time**: 66ms
- **Conclusion**: Không có credential/secret nào trong các file hiện tại

## Nếu đây là credential thật, cần xử lý thế nào

### Immediate actions (ngay lập tức)
1. **Revoke credential immediately**: Xoá/reset token/password trên mọi service (API key, password, token, etc.)
2. **Rotate all dependent credentials**: Nếu credential này có quyền access lên nhiều service, cần reset tất cả
3. **Audit access logs**: Kiểm tra xem ai/gì đã dùng credential này từ lúc leak đến khi revoke
4. **Notify stakeholders**: Thông báo cho security team, ops team, hoặc organization

### Medium-term actions
1. **Force push history cleanup**: Dùng `git-filter-repo` hoặc `BFG repo-cleaner` để xoá credential khỏi tất cả commits
   - Lưu ý: Cần force push, impact tất cả developers, coordinate team
2. **Audit downstream**: Nếu repo đã push lên public repository (GitHub, GitLab), credential có thể bị crawler scan
3. **Monitor for reuse**: Set up alerts nếu credential pattern xuất hiện lại

### Long-term preventive measures
1. **Pre-commit hooks**: (đã cài ✓) Prevent credential commit
2. **Secret scanning**: Enable GitHub secret scanning, GitLab secret detection
3. **Credential management**: Dùng `.env` + `.gitignore`, hoặc secret vault (HashiCorp Vault, AWS Secrets Manager)
4. **Training**: Developer awareness về security best practices

## Vì sao xoá file khỏi HEAD hoặc pin dependency vẫn chưa đủ

### 1. Git history is immutable (without force operations)
- Xoá file từ HEAD (HEAD~0) không xoá credential từ commit 1bdd849
- Credential vẫn tồn tại trong object database Git: `git show 1bdd849:lab-fake-secret.txt` vẫn có thể access
- Clone toàn bộ repo từ bất cứ developer nào = tải toàn bộ lịch sử bao gồm credential

### 2. Dependency pinning (requirements.lock) is orthogonal
- `requirements.lock` pins package versions, không liên quan đến credential leak
- Pinning dependency không thể giải quyết secret trong source code
- Chỉ pinning là cho reproducibility & security patching, không phải credential rotation

### 3. Why force-push is risky but necessary
- **Option A: Just delete from HEAD** → credential vẫn trong history, có thể extract
- **Option B: Force push with git-filter-repo** → xoá hoàn toàn, nhưng:
  - Disruptive: tất cả developers cần rebasing
  - Cannot be undone easily
  - Public mirrors/archives có thể giữ credential
- **Option C: Accept breach, rotate credential** → production approach: rotate immediately, accept history exists

### 4. The real defense layers (tầng bảo vệ thực tế)
1. **Prevention (prevent layer)**: Pre-commit hooks, secret scanning rules
2. **Detection (detect layer)**: Gitleaks on PR/CI, GitHub secret scanning
3. **Incident response (respond layer)**:
   - Immediate credential revocation
   - Audit access logs để biết scope of exposure
   - Force-push chỉ khi absolutely necessary
4. **Monitoring (monitor layer)**: Alert nếu credential pattern tái-xuất hiện

### Kết luận cho CP-4
- Gitleaks scanning cơ cấu đang setup sẽ prevent incident này trong tương lai
- Pre-commit hook đã active, chặn bất kỳ commit nào chứa secret pattern
- Credential giả (lab-fake-secret.txt) đã được xoá khỏi HEAD
- Chỉ deleting file không đủ; cần full incident response plan nếu là credential thật
