# SkyGuard

### Smart Weather Anomaly & Tamper Detection System

**Smart India Hackathon 2026 | Problem Statement SIH26073**

A hybrid software system that detects calibration drift, sensor faults, and genuine extreme microclimate events in Automated Weather Stations (AWS) using a three-way consensus approach.

---

## Problem

India’s AWS network can suffer from:

* Sensor calibration drift (e.g. Mungeshpur-style failures)
* Physical damage / tampering
* Faulty low-cost sensors
* Difficulty distinguishing real extreme weather from sensor failure

Simple threshold alerts are not enough.

---

## Solution

**SkyGuard** compares three temperature sources at the same location and time:

| Source          | Description                                         |
| --------------- | --------------------------------------------------- |
| **T_AWS**       | Official Automated Weather Station reading          |
| **T_Witness**   | Low-cost Edge Witness Node (ESP32 + BME280)         |
| **T_Predicted** | Spatial prediction from neighbouring stations (IDW) |

### Four Possible Decisions

| Decision        | Meaning                                                 |
| --------------- | ------------------------------------------------------- |
| `PRIMARY_DRIFT` | Official AWS sensor has drifted or failed               |
| `WITNESS_FAULT` | Edge witness node is faulty (official data still valid) |
| `TRUE_EXTREME`  | Genuine extreme microclimate detected                   |
| `NORMAL`        | All readings are consistent                             |

---

## Key Features

### Detection Pipeline

1. **Layer 1 – Thermodynamic Consistency Gate**
   WMO-inspired checks using August-Roche-Magnus vapor pressure, VPD, and physical bounds.

2. **Layer 2 – Spatial Prediction**
   Inverse Distance Weighting (IDW) from neighbouring stations, with neighbour count.

3. **Layer 3 – Three-Way Arbitration**
   Compares T_AWS, T_Witness, and T_Predicted using thresholds ε and δ.

### Additional Capabilities

* **Confidence Score** (0–100%) for every decision
* **Severity** levels: LOW / MEDIUM / HIGH / CRITICAL
* **Imputation**: When Primary Drift is detected, a corrected temperature is generated
  (`T_imputed = 0.6 × T_Witness + 0.4 × T_Predicted`)
* **Root-Cause Explanation** in plain language
* **Live Command Center Dashboard** with GIS map, status cards, charts, and tickets

---

## Tech Stack

### Backend

* Python 3.12
* FastAPI
* SQLAlchemy (Async) + SQLite
* Pydantic Settings
* Spatial IDW prediction
* Thermodynamic consistency checks

### Frontend

* React + TypeScript
* Vite
* Tailwind CSS
* Leaflet (GIS map)
* Recharts (temperature trends)
* Axios

### Tooling

* Docker + Docker Compose
* Mock station simulator for demo

---

## Project Structure

```text
skyguard/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── services/
│   │   │   ├── anomaly_engine.py
│   │   │   ├── prediction_service.py
│   │   │   ├── thermodynamic_service.py
│   │   │   ├── ingestion_service.py
│   │   │   └── ticket_service.py
│   │   └── ...
│   ├── scripts/
│   │   └── simulate_stations.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── types/
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## How to Run (Local Development)

### Prerequisites

* Python 3.12
* Node.js 18+
* Git

### Terminal 1 – Backend

```bash
cd backend
python -m venv venv

# Windows:
.\venv\Scripts\Activate

# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Terminal 2 – Frontend

```bash
cd frontend
npm install
npm run dev
```

### Terminal 3 – Simulator

```bash
cd backend
.\venv\Scripts\Activate   # or source venv/bin/activate
python scripts/simulate_stations.py
```

### Open

* Dashboard: `http://localhost:5173`
* API Docs: `http://localhost:8000/docs`

---

## How to Run (Docker)

```bash
docker compose up --build
```

* Dashboard: `http://localhost`
* API Docs: `http://localhost:8000/docs`

Then run the simulator in a separate terminal (local Python) if needed.

---

## Demo Scenarios (Simulator)

The simulator is scripted to demonstrate all three anomaly types:

| Station                       | Decision        | What it shows                                |
| ----------------------------- | --------------- | -------------------------------------------- |
| **New Delhi** (`AWS-DEL-001`) | `PRIMARY_DRIFT` | Official sensor drifted + imputed correction |
| **Mumbai** (`AWS-MUM-001`)    | `WITNESS_FAULT` | Edge node faulty, official data still valid  |
| **Chennai** (`AWS-CHN-001`)   | `TRUE_EXTREME`  | Real extreme microclimate                    |
| Other stations                | `NORMAL`        | Consistent readings                          |

---

## Core Arbitration Logic (Simplified)

```python
if |AWS - Witness| > ε and |Witness - Predicted| < δ:
    → PRIMARY_DRIFT

elif |AWS - Witness| > ε and |AWS - Predicted| < δ:
    → WITNESS_FAULT

elif |AWS - Witness| < δ and (|AWS - Predicted| > ε or |Witness - Predicted| > ε):
    → TRUE_EXTREME

else:
    → NORMAL
```

### Default Thresholds

* **ε (epsilon) = 2.0°C**
* **δ (delta) = 1.5°C**

---

## API Overview

| Method | Endpoint                      | Description                          |
| ------ | ----------------------------- | ------------------------------------ |
| POST   | `/api/ingest/arbitrate`       | Run three-way arbitration            |
| GET    | `/api/stations/status`        | Live status of all stations          |
| GET    | `/api/stations/{id}/readings` | Historical readings                  |
| GET    | `/api/stations/{id}/predict`  | Spatial prediction + neighbour count |
| GET    | `/api/tickets`                | Anomaly tickets                      |
| GET    | `/api/tickets/summary`        | Dashboard summary                    |

---

## For Judges – What to Look For

1. **Live SkyGuard map** with color-coded stations
2. **Delhi** → Primary Drift + Imputed value
3. **Mumbai** → Witness Fault
4. **Chennai** → True Extreme
5. Clear **Root-Cause explanation**
6. **Confidence + Severity** on tickets
7. Scientific layers: **Thermodynamic Gate + Spatial IDW + Three-Way Arbitration**

---

## Team Notes

* Preferred Python version: **3.12**
* MQTT is disabled by default for local demo (`MQTT_ENABLED=False`)
* SQLite is used for simplicity in the demo
* Architecture is designed to scale to the full national AWS network

---

## License

Built for **Smart India Hackathon 2026**.
**SkyGuard — Problem Statement SIH26073 | IMD Weather Station Integrity**
