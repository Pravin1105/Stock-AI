# Stock AI — Two-Stage LLM Analytics & Demand Forecasting (v1.0)

Stock AI is an enterprise conversational retail analytics and inventory demand forecasting platform. It employs a **Two-Stage LLM Architecture** (Intent-to-Execution pattern) that completely eliminates mathematical hallucinations by strictly grounding all figures, rankings, and forecasts in deterministic SQL aggregations, statistical algorithms, and a trained gradient-boosted XGBoost machine learning model.

Version **1.0** introduces **Multi-Provider LLM Model Selection** and **Bring Your Own Key (BYOK)** support across **Google Gemini**, **OpenAI**, **Anthropic Claude**, and **Groq** with minimal external dependencies.

---

## 1. System Architecture

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

## 3. Project Structure

```text
StockAI/
├── src/
│   ├── api/
│   │   ├── app.py            # FastAPI factory with static asset mounting
│   │   └── routes.py         # /api/query, /api/models, /api/health endpoints
│   ├── core/
│   │   ├── config.py         # Multi-provider configs, defaults & metadata
│   │   └── llm_client.py     # Lightweight unified HTTP client (Gemini/OpenAI/Claude/Groq)
│   ├── schemas/
│   │   ├── intent.py         # StructuredIntent, QueryScope, IntentTask schemas
│   │   └── results.py        # UnifiedResult, SummaryMetrics schemas
│   ├── data/
│   │   └── repository.py     # Data access layer over 5-year sales dataset
│   ├── analytics/
│   │   ├── base.py           # BaseAnalyticsEngine abstraction
│   │   ├── ranking.py        # SQL/Data aggregation and ranking engine
│   │   ├── trend.py          # Time-series trend and trajectory engine
│   │   ├── forecast.py       # Trained XGBoost demand forecasting engine
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
├── tests/                    # 33 Automated unit and integration tests
│   ├── test_api.py           # API endpoints & BYOK routing tests
│   ├── test_parser.py        # Multi-provider query parser tests
│   ├── test_explanation.py   # Multi-provider explainer tests
│   ├── test_analytics.py     # Ranking, trend, and forecast engine tests
│   └── test_schemas.py       # Pydantic schema validation tests
├── dataset/                  # Historical store-item sales dataset
├── model/                    # Trained tuned_xgboost_model.json
├── run_server.py             # Backend launcher script
├── build.sh                  # Vercel & production build orchestration
└── requirements.txt          # Python dependencies
```

---

## 4. Quick Start

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

### B. Run Automated Test Suite (33 Tests)

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

## 5. API Reference

### `GET /api/models`
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

### `POST /api/query`
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

## 6. License
MIT License.
