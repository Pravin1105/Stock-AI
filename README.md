# Stock AI — Two-Stage LLM Analytics Architecture

Stock AI is a conversational retail sales analytics and demand forecasting platform. It uses a **Two-Stage LLM Architecture** (Intent-to-Execution pattern) to deliver natural language interactions with zero mathematical hallucinations, grounding all numbers in deterministic SQL aggregations, statistical algorithms, and trained XGBoost machine learning models.

---

## 1. System Architecture

```text
                             USER QUERY
                                 │
                                 ↓
                        ┌─────────────────┐
                        │  Query Parser   │  ◄─── [STAGE 1]
                        │  (Gemini LLM)   │       Extracts Intent & Scope
                        └────────┬────────┘
                                 │
                                 ↓
                          Structured Intent
                                 │
                     ┌───────────┴───────────┐
                     │                       │
                  What?                   Scope?
             (ranking/trend/forecast)  (store, item, etc.)
                     │                       │
                     └───────────┬───────────┘
                                 ↓
                          ANALYTICS ENGINE   ◄─── [STAGE 2]
                                 │
                     ┌───────────┼───────────┐
                     ↓           ↓           ↓
                  SQL/Data   Statistics   XGBoost
                     │           │           │
                     └───────────┼───────────┘
                                 ↓
                          Unified Results    ◄─── Exact calculations & tables
                                 │
                                 ↓
                        ┌─────────────────┐
                        │       LLM       │  ◄─── [STAGE 3]
                        │   Explanation   │       Grounded business narrative
                        └────────┬────────┘
                                 │
                                 ↓
                        ┌─────────────────┐
                        │    Frontend     │  ◄─── [STAGE 4]
                        │ Conversational  │       React + Vite UI
                        └─────────────────┘
```

---

## 2. Project Structure

```text
StockAI/
├── src/
│   ├── api/
│   │   ├── app.py            # FastAPI application with CORS middleware
│   │   └── routes.py         # /api/health and /api/query endpoints
│   ├── core/
│   │   └── config.py         # Settings & environment configuration (.env loader)
│   ├── schemas/
│   │   ├── intent.py         # Pydantic schemas: IntentTask, QueryScope, StructuredIntent
│   │   └── results.py        # Pydantic schemas: UnifiedResult, SummaryMetrics
│   ├── data/
│   │   └── repository.py     # Caching, filtering, and stats over train.csv
│   ├── analytics/
│   │   ├── base.py           # BaseAnalyticsEngine (ABC)
│   │   ├── ranking.py        # Deterministic SQL/Data aggregations and rankings
│   │   ├── trend.py          # Time-series analysis, moving averages, and pct change
│   │   ├── forecast.py       # XGBoost feature engineering and demand prediction
│   │   └── router.py         # AnalyticsDispatcher (orchestrator for engines)
│   ├── explanation/
│   │   ├── prompts.py        # Zero-hallucination system prompt for LLM explainer
│   │   └── explainer.py      # GeminiExplainer and TemplateExplainer
│   └── pipeline.py           # StockAIPipeline master coordinator
├── frontend/
│   ├── src/
│   │   ├── components/       # ChatWorkspace, MessageItem, Sidebar, ChatInput
│   │   ├── services/api.ts   # Direct API client to FastAPI
│   │   ├── types/            # TypeScript interfaces
│   │   └── index.css         # Palette: #F7F2EB, #EAE2D6, #EEEEEE, #8B9A6E
│   └── vite.config.ts
├── tests/
│   ├── test_schemas.py       # Schema validation tests
│   ├── test_parser.py        # Router and parser tests
│   ├── test_analytics.py     # Analytical engines unit tests
│   ├── test_explanation.py   # Explanation & pipeline tests
│   └── test_api.py           # FastAPI integration tests
├── dataset/                  # Store sales dataset
├── model/                    # Trained tuned_xgboost_model.json
├── main.py                   # CLI application runner
├── run_server.py             # FastAPI backend server launcher
├── requirements.txt          # Python dependencies
└── pyproject.toml            # Project packaging & test settings
```

---

## 3. Quick Start

### A. Environment Setup

```bash
# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. (Optional) Configure Gemini API Key
cp .env.example .env
# Add GEMINI_API_KEY=your_key_here to .env
```

### B. Run Automated Test Suite (23 Tests)

```bash
pytest -v
```

### C. Run via CLI

```bash
# Ranking query
python main.py "Show me the top 5 best performing stores"

# Machine learning forecast query
python main.py "Forecast sales for store 5 item 10 for the next 7 days"

# Trend query
python main.py "Show sales trend for item 15 in store 2"
```

### D. Start Backend & Frontend

```bash
# Terminal 1 — FastAPI Backend (port 8000)
python run_server.py

# Terminal 2 — React Frontend (port 5173)
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173/` in your browser.
