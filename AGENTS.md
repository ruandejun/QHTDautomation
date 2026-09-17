# gstack Multi-Agent Operating Model & Quality Rules

## 1. Core Operating Philosophy (Garry Tan Model)
- **Role-Driven Execution**: Work through specialized personas: CEO/Product (autoplan, spec), Eng Manager (plan-eng-review, review), Security (cso), QA (qa, browse), Release (ship).
- **Verify-Before-Commit**: Never mark a task as resolved without automated tests and live DOM/API verification logs.
- **Atomic Rollbacks**: Every production patch must be backward-compatible and preserve DB state.

## 2. Code Quality & Security Standards
- **Zero Raw Exceptions**: Never use bare `except:` clauses — catch specific exception types (`except Exception as e:`).
- **Concurrency & Race Condition Protection**: Encapsulate financial, order, and balance updates within `with transaction.atomic():` blocks and apply `.select_for_update()` with deduplication checks.
- **Dynamic Configuration**: Avoid hardcoded domain names, extension URLs, or secrets in component code — use centralized configuration providers (`siteBrandConfig`, DRF settings).
- **Fallback Integrity**: Provide explicit UI fallbacks (e.g. `!isNaN()`, safe price parsing, image `onError` handlers) to prevent React ErrorBoundary crashes.

## 3. Deployment & Release Protocol
- **Parallel Multi-Site Sync**: Run `bash /root/Workspace/Python/.ai/scripts/deploy_all_3_sites.sh` when deploying shared backend/frontend changes across Maidzo, Alo68, and ChuyenHang365.
- **Asset Integrity**: Purge legacy JS bundles on remote VPS hosts after building new Vite/Rollup bundles to prevent asset mismatch reload loops.

## 4. Dây Chuyền 4 Agent Nối Ca (Four-Agent Pipeline — Chuẩn Cốt Lõi)
Mọi thay đổi tính năng hoặc bugfix đều bắt buộc tuân thủ 4 vai trò nối ca qua thư mục .bangiao/:
1. **Planner (.bangiao/ke-hoach.md)**: Thiết kế kỹ thuật, phân tích interface & edge cases. Tuyệt đối không gõ code. Mơ hồ thì dừng hỏi.
2. **Coder (.bangiao/thay-doi.md)**: Chỉ thi công đúng theo kế hoạch, tuân thủ Chesterton\'s Fence, không sửa ngoài scope.
3. **Tester (.bangiao/ket-qua-test.md)**: Viết unit/behavioral test độc lập. Chạy test. Test rớt thì dừng lại, cấm sửa code sản phẩm để ép test xanh.
4. **Reviewer (.bangiao/danh-gia.md)**: Read-only, soi git diff và ra phán quyết CHOT / CAN SUA / CHAN.
5. **Chốt chặn con người**: Tony là người duyệt cuối cùng trước khi gộp nhánh (merge). Cấm tự ý merge vào nhánh chính.
