# EXCEL-lent

### *Your data analyst, built into Excel.*

**Upload your data. Tell us what you need. Get the analysis.**

EXCEL-lent is an **Excel Data Analyst Engine** — a guided analytics platform that turns raw Excel/CSV data into calculations, pivots, charts, dashboards, reports, and insights **without requiring advanced Excel knowledge**.

> Upload Data → Select What You Want → Engine Processes Data → Get Result

---

## Product positioning

- **Excel Data Analyst Engine** — *Your data analyst, built into Excel.*
- Unlock Excel’s power for people who don’t know formulas, pivots, or charts
- Excel remains the calculation environment; EXCEL-lent is the **intelligence & orchestration layer**

---

## Features (MVP → roadmap)

| Area | Status |
|------|--------|
| Upload Excel / CSV | ✅ MVP |
| Data profiling (types, missing, duplicates) | ✅ MVP |
| Clean data (blanks, duplicates, trim, case) | ✅ MVP |
| Calculate (sum, avg, min, max, %, growth) | ✅ MVP |
| Compare periods / categories | ✅ MVP |
| Summarize / group-by | ✅ MVP |
| Pivot builder | ✅ MVP |
| Charts (bar, line, pie data + export) | ✅ MVP |
| Find problems (duplicates, outliers, missing) | ✅ MVP |
| Ask the data (natural language → analysis) | ✅ MVP |
| Auto insights & recommendations | ✅ MVP |
| Dashboard generator (Sales + custom) | ✅ MVP |
| Report generator | ✅ MVP |
| Excel workbook export | ✅ MVP |
| Template library (Sales, Finance, HR, CRM…) | 🚧 Scaffold |
| Live Power Query / desktop add-in | 📋 Roadmap |
| Multi-user / cloud sync | 📋 Roadmap |

---

## Architecture

```text
                    DATA ANALYST ENGINE
                           │
            ┌──────────────┴──────────────┐
            │                             │
       DATA INGESTION                USER REQUEST
            │                             │
     Excel / CSV / Table            Select / Ask
            │                             │
            └──────────────┬──────────────┘
                           │
                    DATA PROFILING
                           │
                    DATA CLEANING
                           │
                    FORMULA ENGINE
                           │
        ┌──────────┬──────┼──────┬──────────┐
        │          │      │      │          │
     Formula    Lookup   Pivot  Chart    Analysis
        │          │      │      │          │
        └──────────┴──────┴──────┴──────────┘
                           │
                    INSIGHT ENGINE
                           │
             ┌─────────────┼─────────────┐
             │             │             │
         Dashboard       Report       Recommendation
```

| Layer | Tech |
|-------|------|
| Frontend | Next.js 14, React, TypeScript, Tailwind |
| Backend API | FastAPI, Python 3.11+ |
| Analytics | pandas, numpy |
| Excel I/O | openpyxl, xlsxwriter |
| Deploy | Docker Compose (local & VPS) |

---

## Quick start

### Prerequisites

- Node.js 20+
- Python 3.11+
- Docker (optional, for one-command deploy)

### 1. Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:3000

### 3. Docker (full stack)

```bash
docker compose up --build
```

- App: http://localhost:3000  
- API: http://localhost:8000  

---

## User flow

1. **HOME** — “What would you like to do?”
2. **Upload** — Excel or CSV
3. **Objective** — Calculate · Compare · Clean · Pivot · Chart · Dashboard · Analyze · Ask
4. **Configure** — columns, metrics, filters, group-by
5. **Result** — tables, charts, insights, downloadable `.xlsx`

---

## Project structure

```text
EXCEL-lent/
├── backend/                 # FastAPI analytics engine
│   ├── app/
│   │   ├── engines/         # Profile, clean, formula, pivot, insight, NL
│   │   ├── routers/         # REST API
│   │   ├── services/        # Sessions, Excel export
│   │   └── models/          # Pydantic schemas
│   └── requirements.txt
├── frontend/                # Next.js guided UI
├── samples/                 # Sample datasets
├── docker-compose.yml
└── README.md
```

---

## Environment

Copy examples if needed:

```bash
# backend/.env
CORS_ORIGINS=http://localhost:3000
MAX_UPLOAD_MB=50

# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Deploy

### Docker on a VPS

```bash
git clone https://github.com/ktiwari54/EXCEL-lent.git
cd EXCEL-lent
docker compose up -d --build
```

### Frontend (Vercel) + Backend (Railway / Render / Fly)

1. Deploy `backend/` as a Python web service (`uvicorn app.main:app --host 0.0.0.0 --port $PORT`)
2. Deploy `frontend/` to Vercel
3. Set `NEXT_PUBLIC_API_URL` to your API URL
4. Set backend `CORS_ORIGINS` to your frontend URL

---

## License

MIT — see [LICENSE](LICENSE)

---

**EXCEL-lent** — *Upload. Ask. Analyze.*
