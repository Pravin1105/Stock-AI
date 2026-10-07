# Stock AI — Two-Stage LLM Analytics & Demand Forecasting (v1.0 & v2.0)

Stock AI is an enterprise conversational retail analytics and inventory demand forecasting platform. It employs a **Two-Stage LLM Architecture** (Intent-to-Execution pattern) that completely eliminates mathematical hallucinations by strictly grounding all figures, rankings, and forecasts in deterministic SQL aggregations, statistical algorithms, and a trained gradient-boosted XGBoost machine learning model.

- **Version 1.0**: Introduces **Multi-Provider LLM Model Selection** and **Bring Your Own Key (BYOK)** support across **Google Gemini**, **OpenAI**, **Anthropic Claude**, and **Groq** with minimal external dependencies.
- **Version 2.0**: Introduces **Continuous Data Ingestion** and **Independent Model Retraining Pipelines**, establishing the central database as the single source of truth while completely decoupling data ingestion from model training.

---

## 1. System Architecture (v1.0)

```text
                             USER QUERY
                                 │
                                 ↓
                     ┌───────────────────────┐
                     │   Stage 1: Intent     │ ◄─── Multi-Provider Parser
                     │     Query Parser      │      (Gemini / OpenAI / Claude / Groq)
                     └───────────┬───────────┘      [Fallback: RuleBasedQueryParser]
                                 │
                                 ↓
                         Structured Intent
                                 │
                     ┌───────────┴───────────┐
                     │                       │
                  Task ("What?")          Scope ("Where/When?")
             (ranking/trend/forecast)  (store, item, horizon, etc.)
                     │                       │
                     └───────────┬───────────┘
                                 ↓
                     ┌───────────────────────┐
                     │   Stage 2: Analytics  │ ◄─── Zero-Hallucination Engines
                     │   Execution Dispatch  │
                     └───────────┬───────────┘
                                 │
                     ┌───────────┼───────────┐
                     ↓           ↓           ↓
                 SQL/Data    Statistics   XGBoost
                 Ranking       Trends    Forecasting
                     │           │           │
                     └───────────┼───────────┘
                                 ↓
                          Unified Results     ◄─── Exact mathematical tables
                                 │
                                 ↓
                     ┌───────────────────────┐
                     │   Stage 3: Synthesis  │ ◄─── Multi-Provider Explainer
                     │     LLM Explainer     │      (Gemini / OpenAI / Claude / Groq)
                     └───────────┬───────────┘      [Fallback: TemplateExplainer]
                                 │
                                 ↓
                     ┌───────────────────────┐
                     │   Stage 4: Frontend   │ ◄─── Conversational Workspace
                     │   React + Vite UI     │      Model Selector & BYOK Modal
                     └───────────────────────┘
```

---

## 2. Core Features (v1.0)

### Multi-Provider LLM & BYOK (Bring Your Own Key)
- **4 LLM Providers Supported**:
  - **Google Gemini**: `gemini-2.0-flash` (default), `gemini-1.5-flash`, `gemini-1.5-pro`, `gemini-2.5-flash`
  - **OpenAI**: `gpt-4o-mini` (default), `gpt-4o`, `gpt-4-turbo`, `o3-mini`, `gpt-3.5-turbo`
  - **Anthropic Claude**: `claude-3-5-haiku-latest` (default), `claude-3-7-sonnet-latest`, `claude-3-5-sonnet-latest`, `claude-3-haiku-20240307`
  - **Groq**: `llama-3.3-70b-versatile` (default), `llama-3.1-8b-instant`, `mixtral-8x7b-32768`, `gemma2-9b-it`
- **Zero-SDK Overhead**: Built on lightweight pure-Python `httpx` clients directly consuming standard REST / OpenAI-compatible / Anthropic endpoints. No heavy third-party vendor SDKs added.
- **Client-Side Privacy (BYOK)**: API keys are securely held in browser `localStorage` and sent per query request without being permanently stored in any server database.
- **Server Key Fallback**: Automatically leverages environment variables (`GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GROQ_API_KEY`) when no BYOK key is specified.
- **Deterministic Offline Fallback**: In the absence of an API key or during network disruptions, queries automatically fall back to deterministic regex routing and template synthesis without crashing.

### Deterministic Analytics Engines
- **Ranking Engine**: Fast aggregations over historical records (913,000 rows), grouping by store or item, ordering ascending/descending with exact sales totals.
- **Trend Engine**: Historical trajectory analysis, moving metrics, peak and trough identification over custom timeframes.
- **Forecasting Engine**: Trained XGBoost gradient-boosted regression model (`SMAPE ~ 6.19%`) generating daily demand projections with multi-day horizons.

### Interactive Conversational Frontend
- **Model Selector Pill**: Shows current provider, model, and key status dot in the top navigation bar.
- **Provider & BYOK Modal**: Tabbed settings to switch providers, pick preset models, input custom model IDs, and manage API keys with visibility toggles.
- **Visual Analytics**: Dynamic SVG bar charts (rankings) and multi-point line charts (forecasts and trends) generated directly in the conversation flow.
- **Response Attribution**: Clear model badges on assistant replies (e.g. `⚡ GROQ · llama-3.3-70b-versatile`, `OPENAI · gpt-4o-mini`).

---

## 3. Stock AI v2.0 Architecture — Continuous Data Ingestion & Independent Model Retraining

Version **2.0** evolves Stock AI from a static, one-time ML application into a production-grade system that continuously receives new sales data and periodically updates its forecasting models.

### Core Architectural Principle

> **The database becomes the central source of truth, while data ingestion and model training remain completely independent pipelines.**

```text
Data Ingestion (CSV / Sales Entry / POS) ──> Central Database <── Model Retraining (Scheduler / Job)
                                                   │
                                                   ▼
                                       Instant Analytics Visibility
                                      (Rankings, Trends, Summaries)
```

### Why Separate the Pipelines?
This architectural separation prevents the severe bottleneck of blocking HTTP upload requests on heavy training compute:
```text
[Anti-Pattern Avoided]:  CSV Upload ──> Train Model (Slow) ──> Wait ──> HTTP Response
[v2.0 Decoupled Design]:
      Data Ingestion (Fast <1s)        Independent Retraining (Background Job)
               ↓                                     ↓
            Database ◄───────────────────────────────┘
```

### 1. Data Ingestion Pipeline (`src/data/ingestion.py`)
- **Fast, Non-Blocking Ingestion**: Data uploads validate, deduplicate, and write directly to the database in milliseconds without triggering model training.
- **Validation & Cleaning**:
  - Requires standard retail columns: `date`, `store`, `item`, `sales`.
  - Enforces type validity: `store > 0`, `item > 0`, `sales >= 0`, ISO date strings (`YYYY-MM-DD`).
  - Drops corrupted or unparseable records and reports granular validation statistics.
- **In-Batch & Database Deduplication**:
  - Automatically identifies in-batch duplicates on `(store, item, date)`, preserving the most recent record.
  - Enforces relational uniqueness (`PRIMARY KEY (store, item, date)`) with configurable `upsert` or `ignore` modes.
- **Immediate Analytics Visibility**:
  - Calls `DataRepository.invalidate_cache()` upon successful write.
  - Newly ingested sales records are instantly reflected in SQL queries, trend calculations, and ranking analyses without needing model retraining.

### 2. Independent Model Retraining Pipeline (`src/training/`)
- **Scheduler & Asynchronous Coordination (`scheduler.py`)**:
  - Retraining operates independently on a periodic schedule or via on-demand trigger (`POST /api/train/retrain`).
  - Thread-safe mutex lock ensures only one training job can execute at any time.
- **Dynamic Feature Engineering (`features.py`)**:
  - Reads accumulated historical sales from the database.
  - Automatically computes calendar features (`day`, `month`, `year`, `dayofweek`, `weekofyear`), historical store-item summary metrics (`sales_mean`, `sales_median`, `sales_std`), and lag features (`lag_7`, `lag_14`, `lag_28`, `lag_365`).
- **Temporal Train/Holdout Splitting**:
  - Splits data strictly along time boundaries (e.g. 90-day holdout) to ensure realistic out-of-time evaluation.
- **Champion vs. Challenger Governance (`evaluator.py`)**:
  - Trains candidate XGBoost booster (Challenger).
  - Evaluates both candidate and incumbent champion model on the exact same holdout window.
  - Computes comprehensive accuracy metrics: `SMAPE`, `MAE`, `RMSE`, `WAPE`.
  - **Auto-Promotion Rule**: If the candidate beats or matches the incumbent champion within acceptable tolerance, it is promoted. If it performs worse, it is rejected and archived with the decision reason.
- **Versioned Model Registry (`registry.py`)**:
  - Maintains model versions in `model/versions/` and full audit trails in `model/registry.json`.
  - Automatically updates the active champion pointer so `ForecastEngine` hot-reloads the active model without restarting the server.

### 3. Future Evolution Stages
- **Stage 1 (Implemented):** CSV → Central Database (`POST /api/ingest/csv`).
- **Stage 2 (Implemented):** Scheduler → Independent Retraining → Model Registry (`POST /api/train/retrain`, `GET /api/train/models`).
- **Stage 3 & 4 (Implemented backend contracts):** Direct Sales Batch Entry (`POST /api/ingest/sales`) → Central Database → Scheduled Retraining.
- **Stage 5:** Automated external data connectors (streaming/POS/APIs) feeding directly into the database.

---

## 4. Project Structure

```text
StockAI/
├── src/
│   ├── api/
│   │   ├── app.py            # FastAPI factory with static asset mounting
│   │   └── routes.py         # Analytical queries, v2 ingestion & retraining endpoints
│   ├── core/
│   │   ├── config.py         # Multi-provider configs, paths & database settings
│   │   └── llm_client.py     # Lightweight unified HTTP client (Gemini/OpenAI/Claude/Groq)
│   ├── data/
│   │   ├── database.py       # [v2.0] SQLite DatabaseManager with WAL mode & indexes
│   │   ├── ingestion.py      # [v2.0] DataIngestionPipeline (validation, cleaning, deduplication)
│   │   └── repository.py     # Database-backed sales data access & cache invalidation
│   ├── training/             # [v2.0] Independent Model Training Pipeline
│   │   ├── features.py       # Dynamic feature engineering & temporal holdout splitting
│   │   ├── evaluator.py      # SMAPE/MAE/RMSE/WAPE & Champion vs. Challenger comparison
│   │   ├── registry.py       # ModelRegistry versioning & active champion pointer
│   │   ├── trainer.py        # ModelTrainer executing XGBoost retraining & evaluation
│   │   └── scheduler.py      # TrainingScheduler coordinating async background jobs
│   ├── schemas/
│   │   ├── intent.py         # StructuredIntent, QueryScope, IntentTask schemas
│   │   └── results.py        # UnifiedResult, SummaryMetrics schemas
│   ├── analytics/
│   │   ├── base.py           # BaseAnalyticsEngine abstraction
│   │   ├── ranking.py        # SQL/Data aggregation and ranking engine
│   │   ├── trend.py          # Time-series trend and trajectory engine
│   │   ├── forecast.py       # Dynamic XGBoost forecasting engine with registry hot-reloading
│   │   └── router.py         # AnalyticsDispatcher routing engine
│   ├── explanation/
│   │   ├── prompts.py        # Numerical faithfulness system prompts
│   │   └── explainer.py      # Gemini, OpenAI, Claude, Groq & Template explainers
│   ├── routing/
│   │   ├── prompts.py        # Structured JSON extraction prompts
│   │   └── parser.py         # Multi-provider LLM query parsers & rule-based parser
│   └── pipeline.py           # StockAIPipeline master coordinator
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ModelSelectorModal.tsx  # Provider selection & BYOK management modal
│   │   │   ├── ChatWorkspace.tsx       # Message stream & header with model pill
│   │   │   ├── MessageItem.tsx         # Message cards with charts & model attribution
│   │   │   ├── Sidebar.tsx             # Conversation history & settings trigger
│   │   │   └── ChatInput.tsx           # Text input with suggestion chips
│   │   ├── services/api.ts   # API client for query and models endpoints
│   │   ├── types/            # TypeScript interfaces
│   │   └── index.css         # Warm, accessible design palette
│   └── vite.config.ts
├── api/                      # Vercel serverless function bundle entrypoint
│   └── index.py
├── tests/                    # 42 Automated unit and integration tests
│   ├── test_v2_pipelines.py  # [v2.0] Ingestion, database, evaluator & retraining tests
│   ├── test_api.py           # API endpoints & BYOK routing tests
│   ├── test_parser.py        # Multi-provider query parser tests
│   ├── test_explanation.py   # Multi-provider explainer tests
│   ├── test_analytics.py     # Ranking, trend, and forecast engine tests
│   └── test_schemas.py       # Pydantic schema validation tests
├── dataset/                  # Historical store-item sales dataset & central SQLite DB
├── model/                    # Model registry, versions & tuned_xgboost_model.json
├── run_server.py             # Backend launcher script
├── build.sh                  # Vercel & production build orchestration
└── requirements.txt          # Python dependencies
```

---

## 5. Quick Start

### A. Environment Setup

```bash
# 1. Clone repository
git clone https://github.com/Pravin1105/Stock-AI.git
cd Stock-AI

# 2. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install backend dependencies
pip install -r requirements.txt

# 4. (Optional) Set default server API keys in .env
cat <<EOF > .env
GEMINI_API_KEY=your_gemini_key
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
GROQ_API_KEY=your_groq_key
EOF
```

### B. Run Automated Test Suite (42 Tests)

```bash
pytest -v
```

### C. Run the Application

```bash
# 1. Start FastAPI Backend (serves both API and bundled frontend on port 8000)
python run_server.py

# 2. (Optional) Start Vite Development Server for live hot-reloading (port 5173)
cd frontend
npm install
npm run dev
```

Open **`http://localhost:5173/`** (Vite dev) or **`http://127.0.0.1:8000/`** (FastAPI production) in your browser.

---

## 6. API Reference

### Conversational & Model Selection Endpoints

#### `GET /api/models`
Returns supported providers, available preset models, and server-key availability status.

**Sample Response:**
```json
{
  "default_provider": "gemini",
  "providers": {
    "gemini": {
      "name": "Google Gemini",
      "default_model": "gemini-2.0-flash",
      "models": ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.5-flash"],
      "has_server_key": true
    },
    "openai": {
      "name": "OpenAI",
      "default_model": "gpt-4o-mini",
      "models": ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "o3-mini", "gpt-3.5-turbo"],
      "has_server_key": false
    },
    "anthropic": {
      "name": "Anthropic Claude",
      "default_model": "claude-3-5-haiku-latest",
      "models": ["claude-3-5-haiku-latest", "claude-3-7-sonnet-latest", "claude-3-5-sonnet-latest"],
      "has_server_key": false
    },
    "groq": {
      "name": "Groq",
      "default_model": "llama-3.3-70b-versatile",
      "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
      "has_server_key": false
    }
  }
}
```

#### `POST /api/query`
Executes natural-language analytical query with optional provider, model, and BYOK key.

**Request Payload:**
```json
{
  "query": "Forecast sales for store 5 item 10 for the next 7 days",
  "provider": "groq",
  "model": "llama-3.3-70b-versatile",
  "api_key": "gsk_..."
}
```

---

### v2.0 Data Ingestion Endpoints

#### `POST /api/ingest/csv`
Uploads raw CSV text to validate, clean, deduplicate, and insert into the central database.
```json
{
  "csv_data": "date,store,item,sales\n2018-01-01,1,1,45.0\n2018-01-02,1,1,50.0",
  "mode": "upsert"
}
```

#### `POST /api/ingest/sales`
Direct structured JSON sales batch ingestion (for POS & sales entry applications).
```json
{
  "records": [
    {"date": "2018-01-01", "store": 1, "item": 1, "sales": 45.0},
    {"date": "2018-01-02", "store": 1, "item": 1, "sales": 50.0}
  ],
  "mode": "upsert"
}
```

---

### v2.0 Independent Retraining Endpoints

#### `POST /api/train/retrain`
Triggers an asynchronous or synchronous retraining job using accumulated database data.
```json
{
  "holdout_days": 90,
  "n_estimators": 60,
  "max_depth": 6,
  "learning_rate": 0.08,
  "tolerance_pct": 0.0,
  "background": true
}
```

#### `GET /api/train/status`
Returns the status, timing, and last evaluation outcome of model retraining jobs.

#### `GET /api/train/models`
Lists all model versions in the registry, their holdout evaluation metrics, and the currently active champion.

---

## 7. License
MIT License.
