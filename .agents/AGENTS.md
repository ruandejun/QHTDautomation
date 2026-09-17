# Custom Agent Rules for Workspace

This document defines specific, learned guidelines for the Antigravity agent when coding, debugging, and verifying changes in this workspace.

## 1. Systematic Debugging & Root Cause Analysis (RCA)
Before modifying any code to fix a bug (e.g., resolving issues like the NAT "Invalid class" error):
- **Mandatory 4-Phase Process**:
  1. **Replicate & Observe**: Reproduce the error and gather logs/outputs.
  2. **Trace Data Flow**: Back-trace the data flow from the point of failure to the source of data.
  3. **Analyze Race Conditions/Timing**: Verify if async operations, timing, or race conditions are causing the state discrepancy.
  4. **Formulate Fix**: Propose a fix targeting the *root cause* instead of patching the symptoms.
- **Strict Constraint**: Never write quick symptom-fixing patches. Always fix the underlying architecture/state issue.

## 2. Verification Before Completion
- **Strict Rule**: Never declare a task "done", "fixed", "passed", or "resolved" in a turn unless the actual verification command or test script has been executed and succeeded *within that same turn*.
- Always provide the execution output/logs of the test commands as proof of correctness.

## 3. Five-Axis Code Review & Quality
Before submitting code changes, perform a review across 5 axes:
1. **Correctness**: Code behavior matches requirements, edge cases handled.
2. **Readability**: Code is clean, descriptive naming, appropriate comments.
3. **Architecture**: Clean separation of concerns, appropriate design patterns.
4. **Security**: Validate inputs, sanitize data, no leaked secrets.
5. **Performance**: Verify resource usage, no unnecessary database hits or network requests.

## 4. Surgical Code Simplification (Chesterton's Fence)
- **Surgical Changes**: Only simplify or refactor code that is *directly modified* by the current task. Do not perform wide-ranging, unrelated refactoring.
- **Chesterton's Fence**: Never delete or rewrite code unless you fully understand why it was put there in the first place.
- **Alignment**: This matches Rule 8 "Surgical Changes" in `CLAUDE.md` of `c69-backend`.

## 5. Strict 6-Phase Standard Deployment Protocol (Bắt Buộc)
1. **Push lên GitHub:** Lấy local commit hash (`git rev-parse HEAD`), push lên GitHub remote branch.
2. **Server Kiểm Tra Commit Trước Khi Pull:** SSH vào VPS, `git fetch origin <branch>`, so sánh remote commit hash (`git rev-parse origin/<branch>`) với commit vừa push để chắc chắn server nhận đúng commit mới nhất trước khi pull.
3. **Server Pull Code:** `git pull origin <branch>`
4. **Backend Collectstatic & Rebuild Assets:** Chạy `python manage.py collectstatic --noinput` trong container backend (và build frontend nếu có thay đổi UI).
5. **Restart Docker Containers:** Restart service `docker restart <backend> <frontend> <nginx>` hoặc `docker compose up -d --force-recreate`.
6. **Live Verification & Kiểm Tra Cập Nhật:** Curl endpoint live (`curl -s -I <url>`), kiểm tra HTTP 200 OK và xác thực code mới live 100%.

## 4. Dây Chuyền 4 Agent Nối Ca (Four-Agent Pipeline — Chuẩn Cốt Lõi)
Mọi thay đổi tính năng hoặc bugfix đều bắt buộc tuân thủ 4 vai trò nối ca qua thư mục .bangiao/:
1. **Planner (.bangiao/ke-hoach.md)**: Thiết kế kỹ thuật, phân tích interface & edge cases. Tuyệt đối không gõ code. Mơ hồ thì dừng hỏi.
2. **Coder (.bangiao/thay-doi.md)**: Chỉ thi công đúng theo kế hoạch, tuân thủ Chesterton\'s Fence, không sửa ngoài scope.
3. **Tester (.bangiao/ket-qua-test.md)**: Viết unit/behavioral test độc lập. Chạy test. Test rớt thì dừng lại, cấm sửa code sản phẩm để ép test xanh.
4. **Reviewer (.bangiao/danh-gia.md)**: Read-only, soi git diff và ra phán quyết CHOT / CAN SUA / CHAN.
5. **Chốt chặn con người**: Tony là người duyệt cuối cùng trước khi gộp nhánh (merge). Cấm tự ý merge vào nhánh chính.
