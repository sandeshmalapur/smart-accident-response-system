# Project Constitution

## Project Name
Smart Accident Response System (AI-Based Accident Detection and Emergency Response System)

## Repository
smart-accident-response-system

## Purpose
Detect vehicle accidents in real time, predict severity, track location, detect gas leaks, and trigger emergency notifications — via a two-phase system (software simulation, then real ESP32 hardware).

## Locked Technology Stack

**Frontend:** React, TypeScript, Vite, Tailwind CSS, shadcn/ui
**Backend:** FastAPI, Python, SQLAlchemy, Alembic, PostgreSQL (Supabase), JWT, WebSockets
**Machine Learning:** Scikit-learn, Pandas, NumPy, Joblib — SVM (severity classification), GMM (anomaly detection)
**IoT:** ESP32, MQTT (Mosquitto), MPU6050, MQ2, GPS NEO-6M
**Edge AI:** NVIDIA Jetson Nano / Xavier (Phase 12+)
**Dev Tools:** Git, GitHub, Docker, Antigravity IDE, Gemini (IDE debugging only)

## Non-Negotiables
1. Simulator and ESP32 must publish identical MQTT payload schemas — swapping one for the other requires zero backend changes.
2. All REST endpoints are versioned under `/api/v1/`.
3. No later phase begins before its dependencies are complete (see ROADMAP.md).
4. SVM handles supervised severity classification; GMM handles unsupervised anomaly detection (gas leak / abnormal sensor patterns). These are not interchangeable.
5. Secrets (DB creds, JWT secret, MQTT broker address) live in `.env`, never committed.
6. Local dev uses Docker Postgres + Mosquitto; production Postgres is Supabase.

## Out of Scope (Phase 1)
- Real hardware (ESP32, sensors) — Phase 11+
- Jetson edge deployment — Phase 12+
- Real emergency service integration (police/ambulance APIs) — notifications are mocked in Phase 1

## Governance
This document is the source of truth for architecture and stack decisions. Changes require explicit approval and a CHANGELOG.md entry.