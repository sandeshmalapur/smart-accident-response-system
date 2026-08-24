# Smart Accident Response System — Comprehensive Project Report & Presentation Guide

---

## Executive Summary

The **Smart Accident Response System** is an end-to-end IoT, Edge-AI, and Geospatial Emergency Management platform engineered to detect traffic collisions and hazardous gas leaks in real time, score incident severity using machine learning models, dispatch nearest medical units, monitor victim welfare, and inform emergency contact relatives via SMS with live trackable status links.

- **Current Status**: **85% Completed** (Sprints 1 through 4 fully built, tested, and operational).
- **Core Purpose**: Drastically reduce emergency response time (the "Golden Hour" after accidents) by automating crash detection, nearest hospital GIS lookup, ambulance dispatching, victim check-in, and relative notification.

---

## Slide-by-Slide Presentation Outline (For AI PPT Generation)

### Slide 1: Title Slide
- **Title**: Smart Accident Response System
- **Subtitle**: Real-Time IoT Crash Detection, Edge-AI Triage, Automated Ambulance Navigation & Relative SMS Tracking
- **Key Concepts**: IoT Telemetry &bull; Machine Learning &bull; GIS Spatial Search &bull; Live Telemetry &bull; Telehealth Check-In

### Slide 2: Problem Statement & Vision
- **Problem**:
  - Delayed crash reporting due to victim incapacitation or lack of witnesses.
  - High mortality rates due to delayed medical dispatch during the critical "Golden Hour".
  - Panicked relatives receiving delayed or zero information about emergency status.
- **Solution**:
  - Vehicle sensor node publishes continuous telemetry over MQTT.
  - Edge-AI evaluates collisions and toxic gas leaks within milliseconds.
  - Automated nearest hospital suggestions, live ambulance target navigation, in-vehicle welfare check, and 24-hour public relative tracking link via SMS.

### Slide 3: System Architecture & Technology Stack
- **IoT & Telemetry Layer**: Python Sensor Simulator & ESP32 Nodes (MPU6050 Accelerometer/Gyroscope, MQ-2 Gas, NEO-6M GPS) &rarr; Eclipse Mosquitto MQTT Broker.
- **Backend Infrastructure**: Python 3.12, FastAPI (AsyncIO), SQLAlchemy 2.0, Alembic Migrations, PostgreSQL (Supabase / Docker), WebSockets.
- **Machine Learning**: Scikit-Learn Dual-Model Pipeline (Support Vector Machine for collision severity + Gaussian Mixture Model for gas anomaly detection).
- **Frontend Dashboard & Public Tracking**: React 18, TypeScript, Vite, TailwindCSS (Dark Glassmorphism UI), React-Leaflet GIS maps, TanStack React Query.
- **External Communications**: Twilio REST API for automated SMS alert dispatching.

### Slide 4: Key Modules & Features Completed (Sprints 1–4)
1. **MQTT Telemetry & Ingestion Engine**: Continuous ingestion of 6-DOF motion, gas levels, and GPS coordinates with schema validation.
2. **Dual-Model ML Classifier**: Real-time collision severity scoring (Minor/Moderate/Severe) & gas leak anomaly detection.
3. **Geospatial GIS Engine**: Haversine formula calculation for auto-suggesting nearest hospitals and available ambulances.
4. **Ambulance Fleet & Target Navigation**: Real-time MQTT telemetry feed where dispatched ambulances visibly converge towards crash coordinates (~18% linear interpolation per tick until ~50m threshold).
5. **In-Vehicle Welfare Check (`/vehicle/:deviceCode`)**: Pre-reviewed static prompt & safety guidance; 90-second automated timeout escalation if occupant fails to respond.
6. **Relative Contact & Public Trackable Link (`/track/:token`)**: Capture emergency contact on device registration, dispatch Twilio SMS alert on severe crash with 24h unguessable token link.

### Slide 5: Machine Learning Engine Deep-Dive
- **SVM Collision Classifier**:
  - Features: Accelerometer Magnitude (\(\sqrt{x^2+y^2+z^2}\)), Axis Standard Deviation, Gyroscope Rotation Rate, Jerk Rate.
  - Outputs: `minor` (logged), `moderate` (dashboard alert), `severe` (full emergency escalation).
- **GMM Gas Anomaly Detector**:
  - Features: Normalized Gas Concentration & Accelerometer Magnitude.
  - Detects gas leaks or hazardous chemical anomalies co-occurring during vehicle crashes.
- **Dual Inference Result**: Returns 0, 1, or 2 incident rows per telemetry tick without crashing or dropping data.

### Slide 6: Automated Dispatch & Live Ambulance Navigation
- Operators view live incident map with nearest hospital recommendation.
- One-click ambulance assignment switches ambulance status to `dispatched`.
- Ambulance simulator continuously polls `GET /api/v1/ambulances/{code}/active-dispatch`.
- Dispatched ambulance visibly navigates towards crash coordinates on Leaflet map in real time until holding position at scene.

### Slide 7: In-Vehicle Welfare Check & 90s Auto-Escalation
- In-vehicle tablet view (`/vehicle/:deviceCode`) opens automatically upon severe crash detection.
- Displays static, legally safe guidance ("Stay still, help is on the way") and binary response buttons (`I'M OK` / `I NEED HELP`).
- **90-Second Background Escalation Loop**: If occupant does not respond within 90 seconds, background task auto-escalates status to `no_response_escalated` and broadcasts urgent alert to operator dashboard.

### Slide 8: Relative Contact & Twilio SMS Alert Tracking
- **Device Registration**: Captures `owner_name`, `emergency_contact_name`, and `emergency_contact_phone`.
- **Automated SMS Dispatch**: Severe crashes trigger Twilio SMS containing direct link: `"{owner_name}'s vehicle was involved in a possible accident. Track live status: http://<host>/track/<token>"`.
- **Public Tracking Interface (`/track/:token`)**:
  - Unauthenticated by design (no login required for scared relatives).
  - Cryptographically random 24-hour token (`secrets.token_urlsafe(32)`).
  - Shows plain-language status, nearest hospital name & phone call button, and live 5-second polling map of ambulance navigation.

### Slide 9: Security, Auth & Privacy Architecture
- **Protected Operator Routes**: JWT Bearer authentication & role-based authorization (`admin`, `operator`).
- **Public Endpoints**:
  - `/vehicle/:deviceCode`: Vehicle display prompt.
  - `/track/:token`: Emergency relative feed (tokens unguessable, 24h expiration, no listing/enumeration endpoint).
- **Data Privacy**: Public tracking payload strips all internal database UUIDs and sensitive user IDs.

### Slide 10: Database Schema Overview
- 10 Relational Tables:
  1. `users` (Dashboard authentication & roles)
  2. `devices` (Sensor hardware nodes & emergency contact fields)
  3. `sensor_readings` (Time-series telemetry)
  4. `hospitals` (Static registry & GIS coordinates)
  5. `incidents` (Detected accidents & severity classifications)
  6. `alerts` (Notification log)
  7. `ambulances` (Fleet tracking & live coordinates)
  8. `dispatches` (Operator dispatch assignments)
  9. `welfare_checks` (In-vehicle prompt & escalation timestamps)
  10. `incident_tracking_tokens` (24h public tracking tokens)

### Slide 11: Current Project Status & Completion Percentage
- **Overall Completion: 85%**
- **Completed**:
  - [x] Phase 1 & 2: Ingestion, ML Inference, Live Dashboard, GIS Search
  - [x] Phase 3: Ambulance Fleet Triage & Dispatch Management
  - [x] Phase 4: In-Vehicle Welfare Check & 90s Auto-Escalation
  - [x] Phase 5: Live Ambulance Navigation Telemetry
  - [x] Phase 6: Emergency Relative Contact, Twilio SMS & Public Tracking Page
- **Test Coverage**: 100% passing rate across 40 backend pytest test suites and frontend production builds.

### Slide 12: Next Steps & Future Roadmap
- **Sprint 5 (Next Step - 10%)**: Multi-Agency Dispatch Triage & Police/Fire Escalation (roles for `police` & `fire`, multi-unit coordination).
- **Sprint 6 (Final Phase - 5%)**: Advanced Analytics Dashboard, Accident Spatial Heatmaps & Predictive AI Insights.

---

## Technical Specifications & Codebase Details

### API Endpoints Summary

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/api/v1/auth/login` | POST | None | Authenticates operator/admin and returns JWT token |
| `/api/v1/devices` | GET/POST | Bearer | List devices or register new device with emergency contacts |
| `/api/v1/readings` | GET | Bearer | Fetch historical or latest sensor readings |
| `/api/v1/incidents` | GET/PATCH | Bearer | List incidents or update triage status (`acknowledged`, `resolved`, `false_positive`) |
| `/api/v1/hospitals/nearest` | GET | Bearer | Haversine distance search for top N nearest hospitals |
| `/api/v1/ambulances/nearest` | GET | Bearer | Haversine distance search for available ambulance units |
| `/api/v1/ambulances/{id}/active-dispatch` | GET | None | Lightweight polling endpoint for ambulance simulator movement |
| `/api/v1/incidents/{id}/dispatch` | POST | Bearer | Create ambulance dispatch and set status to `dispatched` |
| `/api/v1/welfare-checks/device/{code}` | GET | None | In-vehicle screen polling endpoint |
| `/api/v1/welfare-checks/{id}/respond` | POST | None | In-vehicle button response (`ok`/`help`) |
| `/api/v1/track/{token}` | GET | None | Public status tracking endpoint for emergency contact relatives |

---

## Detailed Next Steps & Implementation Roadmap

1. **Sprint 5: Multi-Agency Escalation (Police & Fire Integration)**
   - Widen user role enforcement for `'police'` and `'fire'` responder views.
   - Add specialized agency dispatch workflow for high-severity crash incidents involving fire hazards or structural damage.

2. **Sprint 6: Spatial Heatmaps & Predictive Analytics**
   - Implement Leaflet Heatmap overlay on dashboard showing high-risk accident hotspots.
   - Add analytics reporting export (PDF/CSV) for emergency management authorities.
