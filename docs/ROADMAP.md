# Roadmap

## Phases

| Phase | Name | Status |
|---|---|---|
| 1 | Repository Planning | ✅ Done |
| 2 | Architecture | ✅ Done |
| 3 | Documentation | 🔄 In Progress |
| 4 | Database Design | ⬜ Not Started |
| 5 | API Design | ⬜ Not Started |
| 6 | Backend Development | ⬜ Not Started |
| 7 | Machine Learning | ⬜ Not Started |
| 8 | Sensor Simulator | ⬜ Not Started |
| 9 | Frontend | ⬜ Not Started |
| 10 | Integration | ⬜ Not Started |
| 11 | ESP32 Integration | ⬜ Not Started |
| 12 | Jetson Deployment | ⬜ Not Started |
| 13 | Testing | ⬜ Not Started |
| 14 | Documentation Finalization | ⬜ Not Started |
| 15 | Final Review | ⬜ Not Started |

## Sprint Plan

| Sprint | Phase(s) | Deliverable |
|---|---|---|
| S0 | 1–3 | Repo init, docs skeleton, architecture freeze |
| S1 | 4–5 | DB schema + API spec finalized |
| S2 | 6 | FastAPI backend: auth, CRUD, MQTT subscriber, WS broadcaster |
| S3 | 7 | ML training pipeline (SVM + GMM), exported models |
| S4 | 8 | Sensor simulator publishing MQTT |
| S5 | 9 | React dashboard: live feed, history, alerts |
| S6 | 10 | Full integration test |
| S7 | 11 | ESP32 firmware, zero-change simulator swap |
| S8 | 12 | Jetson edge deployment |
| S9 | 13–14 | Testing suite, docs finalized |
| S10 | 15 | Final review, demo prep |

## Rule
No phase begins before its dependencies (see PROJECT_CONSTITUTION.md and ARCHITECTURE.md) are complete and approved.