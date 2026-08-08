# Project State

Living document — what's actually built and verified, updated as sprints close.
This reflects VERIFIED state (raw output checked), not just reported state.

## Phase Status

| Phase | Status | Verified |
|---|---|---|
| 1-3: Planning, Architecture, Docs | ✅ Complete | Yes |
| 4-5: DB Schema, API Spec | ✅ Complete | Yes |
| 6: Backend Development (S2) | ✅ Complete | Yes — 21/21 tests, merged commit bf7a2ee |
| 7: Machine Learning (S3) | ✅ Complete | Yes — commit 868a619, 21/21 tests, sklearn version matched |
| 8: Sensor Simulator | ⬜ Status unknown | Not yet reported to Master Chat |
| 9: Frontend (S5) | ⬜ Status unknown | Not yet reported to Master Chat |
| 10: Integration (S6) | ⬜ Blocked | Waiting on Phase 8 + 9 status |
| 11-15 | ⬜ Not started | — |

## Backend (Sprint S2 + S3 ML wiring)
- FastAPI app: auth (JWT), all REST endpoints per API_SPEC.md, MQTT subscriber, WebSocket broadcaster
- WebSocket actually mounted at `/api/v1/ws/live` (API_SPEC.md updated to match — confirm this update was committed)
- Real SVM (severity) + GMM (anomaly) inference wired in, replacing Sprint S2 stub
- `run_inference()` returns `list[InferenceResult]` (0-2 items) — see ARCHITECTURE.md § ML Inference
- `backend/app/ml/` is a self-contained synced copy from repo-root `ml/`, via `backend/app/ml/sync_models.py`
- Dependencies pinned: bcrypt==4.0.1, pydantic[email]==2.9.2, scikit-learn==1.8.0 (must match ml/ training environment)
- Test suite: 21/21 passing, verified clean (no InconsistentVersionWarning)
- Local dev requires: Docker Desktop running (postgres + mosquitto containers) — native/non-Docker Postgres will NOT work due to credential mismatch

## ML (Sprint S3)
- Repo-root `ml/`: training scripts, synthetic data generator, SVM (99.67% test accuracy) + GMM (100% recall/81% precision) models
- `ml/inference.py`: dependency-light `InferenceService`, copied into `backend/app/ml/_inference_service.py`
- Synthetic data only — no real sensor data yet (expected, per PROJECT_CONSTITUTION.md scope)

## Frontend (Sprint S5)
- Status not yet reported to Master Chat — prompt was generated and handed off, no completion report received

## Simulator (Phase 8)
- Status not yet reported to Master Chat — not yet assigned/started as far as this doc knows

## Known Process Note
Multiple sprints in this project saw specialist chats report work as "done and tested"
that did not match what was actually on disk (missing files, stale code, unapplied
diffs). Going forward: verification requires pasting raw file contents / raw command
output, not prose summaries of completion.