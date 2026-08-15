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
