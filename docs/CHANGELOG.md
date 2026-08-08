# Changelog

## 2026-08-08 — ML inference wiring (Sprint S3)

**Decided:** `run_inference()` returns `list[InferenceResult]` (0–2 items), not a
single result, because `incidents.incident_type` is a single-value enum and a
reading can trip both the SVM severity model and the GMM anomaly model at once.
`backend/app/mqtt/client.py` updated accordingly (loops over results instead of
handling one). See ARCHITECTURE.md § ML Inference — Design Decisions.

**Decided:** `backend/app/ml/` is a self-contained copy of inference code/models
(not a cross-folder import from repo-root `ml/`), to keep backend independently
deployable. Synced via `backend/app/ml/sync_models.py`; see
`backend/app/ml/README.md`.

**Fixed:** `backend/app/mqtt/client.py` had a bug where `run_inference()`'s list
return value was used as if it were a single object (`result.is_incident` on a
list) — caught in review before merge, fixed to `for result in results:`.

**Note:** An externally-generated ML wiring prompt (Sprint S3, dated prior to
these decisions) assumed the old single-result contract and forbade touching
`client.py`. That prompt is now superseded — do not reuse it. This entry is the
frozen reference for any future ML-wiring prompt.