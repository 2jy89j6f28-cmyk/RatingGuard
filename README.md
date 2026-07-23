<p align="right">
  <a href="README.zh-CN.md">🇨🇳 中文</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Next.js-14-000000?style=for-the-badge&logo=nextdotjs&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/Tailwind_CSS-3.4-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white" />
  <img src="https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white" />
  <img src="https://img.shields.io/badge/DeepSeek-4F46E5?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cGF0aCBkPSJNMTIgMkM2LjQ4IDIgMiA2LjQ4IDIgMTJzNC40OCAxMCAxMCAxMCAxMC00LjQ4IDEwLTEwUzE3LjUyIDIgMTIgMnptMCAxOGMtNC40MSAwLTgtMy41OS04LTggMC00LjQxIDMuNTktOCA4LThzOCAzLjU5IDggOC04IDMuNTktOCA4eiIgZmlsbD0id2hpdGUiLz48L3N2Zz4=&logoColor=white" />
  <img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge" />
  <br />
  <img src="https://img.shields.io/github/stars/BanananaCavendish/ratingguard?style=social" />
  <img src="https://img.shields.io/github/issues/BanananaCavendish/ratingguard?style=social" />
</p>

<h1 align="center">🛡️ RatingGuard</h1>
<h3 align="center">AI-Powered Negative Review Recovery Agent for Cross-Border E-Commerce</h3>

<p align="center">
  Automatically detect negative reviews from <b>Shopify</b> / <b>Amazon</b> stores,
  analyze root causes with <b>DeepSeek</b> LLM, and generate culturally-tailored
  recovery emails — streamed in real-time to a sleek <b>Next.js</b> SaaS dashboard.
  <br />
  <b>Turn angry customers into loyal ones. Fully open-source.</b>
</p>

<p align="center">
  <a href="#features">✨ Features</a> •
  <a href="#architecture">🏗️ Architecture</a> •
  <a href="#tech-stack">🛠️ Tech Stack</a> •
  <a href="#quick-start">🚀 Quick Start</a> •
  <a href="#project-structure">📂 Project Structure</a> •
  <a href="#api-reference">📡 API Reference</a> •
  <a href="#license">📄 License</a>
</p>

---

<h2 id="features">✨ Core Features</h2>

<table>
  <tr>
    <td width="50%">
      <h4>🤖 Review Input</h4>
      Two ways to get reviews: <b>Auto-scrape</b> from Shopify stores (JSON-LD / Judge.me / HTML) with no API key needed, or <b>manually paste</b> reviews from any platform (Amazon, Shopee, TikTok Shop, etc.). Automatically filters for ≤3 star reviews.
    </td>
    <td width="50%">
      <h4>🧠 AI Root-Cause Analysis</h4>
      Powered by <b>DeepSeek-V4 Flash</b> with prompt caching. Classifies complaints into 9 categories (shipping delay, product quality, sizing, damaged goods, etc.) and assesses customer anger level on a 1–5 scale.
    </td>
  </tr>
  <tr>
    <td>
      <h4>🌍 Multi-Language Recovery Emails</h4>
      Generates culturally-appropriate, compliance-safe emails in <b>11+ languages</b> (US/GB English, Japanese 敬語, German Sie-Form, French vous, Korean 존댓말, etc.). Includes <code>[Customer Name]</code> and <code>[Discount Code]</code> placeholders.
    </td>
    <td>
      <h4>⚡ Real-Time SSE Streaming</h4>
      Watch the AI write the recovery email <b>character by character</b> via Server-Sent Events. Powered by FastAPI <code>StreamingResponse</code> + <code>AsyncOpenAI</code> — no polling, no waiting.
    </td>
  </tr>
  <tr>
    <td>
      <h4>🛡️ Compliance Guardrails</h4>
      XML-tagged system prompt enforces platform-safe language. Never suggests "refund for review deletion." All outputs are pure JSON, with automatic fallback when parsing fails.
    </td>
    <td>
      <h4>🎨 Modern SaaS Dashboard</h4>
      Dark-themed, responsive UI built with <b>Next.js 14 App Router</b> and <b>Tailwind CSS</b>. Review list panel + live analysis panel, skeleton loading states, one-click copy, and mock send.
    </td>
  </tr>
</table>

---

<h2 id="tech-stack">🛠️ Tech Stack</h2>

<table>
  <tr>
    <th align="center">Backend</th>
    <th align="center">Frontend</th>
    <th align="center">AI Engine</th>
  </tr>
  <tr>
    <td valign="top">
      <ul>
        <li><b>FastAPI</b> 0.115 — async web framework</li>
        <li><b>Uvicorn</b> — ASGI server</li>
        <li><b>Requests</strong> + <strong>BeautifulSoup4</b> — Shopify scraping</li>
        <li><b>Pydantic</b> V2 — data modeling & validation</li>
        <li><b>aiosqlite</b> — async SQLite persistence</li>
        <li><b>OpenAI SDK</b> — DeepSeek API client</li>
        <li><b>python-dotenv</b> — environment management</li>
      </ul>
    </td>
    <td valign="top">
      <ul>
        <li><b>Next.js</b> 14 — App Router (React 18)</li>
        <li><b>TypeScript</b> 5 — strict mode</li>
        <li><b>Tailwind CSS</b> 3.4 — utility-first styling</li>
        <li><b>Custom SSE Hook</b> — <code>useRecoveryStream</code></li>
        <li><b>Fetch API</b> + <code>ReadableStream</code> — streaming consumer</li>
      </ul>
    </td>
    <td valign="top">
      <ul>
        <li><b>DeepSeek-V4 Flash</b> — primary LLM</li>
        <li><b>LLMDriver</b> adapter pattern — swap GPT-4o / Claude / DeepSeek freely</li>
        <li><b>Structured system prompt</b> — XML-tagged, injection-resistant</li>
        <li><b>Prompt caching</b> — lower latency & cost</li>
        <li><b>9-category</b> root cause classifier</li>
        <li><b>11-country</b> localization map</li>
      </ul>
    </td>
  </tr>
</table>

---

<h2 id="architecture">🏗️ Architecture & Data Flow</h2>

```mermaid
flowchart LR
    A[🛍️ Shopify Store] -->|HTTP GET| B[🕷️ Scraper<br/>requests + BS4]
    B -->|JSON-LD / Judge.me / HTML| C[📋 Structured Reviews<br/>≤3 stars only]

    C --> D[💾 Database<br/>SQLite + aiosqlite]
    D -->|GET /api/reviews| H[🌐 Next.js Frontend<br/>SaaS Dashboard]

    H -->|select review + POST /api/stream-recovery| G[⚡ FastAPI SSE Endpoint<br/>/api/stream-recovery]
    G -->|review_text + country_code| E[🧠 AI Agent<br/>DeepSeek Flash]
    E -->|System Prompt + Caching| F[📊 Analysis: reason, anger, persona]
    E -->|Stream=True| I[✉️ Recovery Email<br/>Multi-language]

    F --> G
    I --> G

    G -->|SSE event stream| H
    H -->|token events| J[⌨️ Typewriter Effect]
    H -->|done event| K[📋 Analysis Cards]
    H -->|done event| L[📧 Email Preview]
    L --> M[📋 Copy to Clipboard]
    L --> N[✈️ Mock Send Email]

    G -->|done + review_id| D

    style A fill:#1e293b,stroke:#3b82f6,color:#fff
    style B fill:#1e293b,stroke:#10b981,color:#fff
    style D fill:#1e293b,stroke:#8b5cf6,color:#fff
    style G fill:#1e293b,stroke:#f59e0b,color:#fff
    style H fill:#1e293b,stroke:#06b6d4,color:#fff
```

### Processing Pipeline

| Step | Component | What Happens |
|------|-----------|-------------|
| **① Input** | `page.tsx` — `ManualReviewForm` | Paste review text from any platform, or scrape from Shopify URL |
| **② Scrape** | `scraper.py` | Fetches product page HTML, tries 3 strategies (JSON-LD → Judge.me → generic HTML) |
| **③ Filter** | `scraper.py` | Keeps only ≤3 star reviews, sorts by rating ascending |
| **④ Store** | `scrape_routes.py` + `database.py` | Writes reviews to SQLite, deduplicates by (reviewer, content, product) |
| **⑤ Analyze** | `main.py` + `ai_agent.py` | Sends review to DeepSeek with XML-tagged system prompt + country-specific localization |
| **⑥ Stream** | `main.py` | FastAPI `StreamingResponse` forwards each LLM delta token as an SSE event |
| **⑦ Display** | `page.tsx` | `useRecoveryStream` hook parses SSE events, renders typewriter animation, shows structured results |
| **⑧ Persist** | `main.py` + `database.py` | After stream completes, saves analysis result to `analyses` table |
| **⑨ Act** | `ActionBar` | Copy email to clipboard or trigger mock send |

---

<h2 id="quick-start">🚀 Quick Start</h2>

### Prerequisites

- Python **3.11+**
- Node.js **18+**
- A DeepSeek API key ([get one here](https://platform.deepseek.com/api_keys))

### 1. Clone & Configure

```bash
git clone https://github.com/BanananaCavendish/ratingguard.git
cd ratingguard

# Create environment file
cp .env.example .env
# └─ Edit .env: fill in DEEPSEEK_API_KEY, SHOPIFY_STORE_DOMAIN
```

### 2. Install Dependencies

```bash
# Backend
pip install -r backend/requirements.txt

# Frontend
cd frontend && npm install && cd ..
```

### 3. Start the Backend Server

```bash
python -m backend.main
# → FastAPI running at http://localhost:8000
# → Swagger docs at http://localhost:8000/docs
```

### 4. Start the Frontend Dev Server

```bash
cd frontend
npm run dev
# → Next.js running at http://localhost:3000
```

### 5. Open the Dashboard

Navigate to **http://localhost:3000**. Choose your input method:

- **🔗 Scrape** — enter a Shopify product URL to auto-fetch reviews
- **✏️ Manual** — paste a review directly from any platform

Select a review card (or submit manual input) and watch the AI generate a recovery email in real-time.

### Configuration Reference

| Environment Variable | Required | Default | Description |
|---------------------|----------|---------|-------------|
| `SHOPIFY_STORE_DOMAIN` | ✅ | — | Your Shopify store domain (e.g., `mystore.myshopify.com`) |
| `DEEPSEEK_API_KEY` | ✅ | — | DeepSeek API key for LLM inference |
| `DEEPSEEK_MODEL_NAME` | ❌ | `deepseek-chat` | Model identifier (V4 Flash or custom) |
| `DEEPSEEK_BASE_URL` | ❌ | `https://api.deepseek.com/v1` | API endpoint base URL |
| `OPENAI_API_KEY` | ❌ | — | Alternative: OpenAI key for GPT-4o |
| `LOG_LEVEL` | ❌ | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`) |
| `SCRAPER_REQUEST_DELAY_MIN` | ❌ | `2.0` | Minimum delay between requests (seconds) |
| `SCRAPER_REQUEST_DELAY_MAX` | ❌ | `5.0` | Maximum delay between requests (seconds) |
| `DATABASE_PATH` | ❌ | `ratingguard.db` | SQLite database file path |
| `CORS_ORIGINS` | ❌ | `http://localhost:3000` | Comma-separated allowed CORS origins |

### Docker Deployment (Production)

```bash
# 1. Build and start all services
docker-compose up --build

# 2. Open the dashboard
#    → http://localhost:3000

# 3. Stop and clean up
docker-compose down -v
```

The Docker setup includes:
- **Backend** — Python 3.11-slim, Uvicorn with 4 workers, healthcheck
- **Frontend** — Node 20-alpine, Next.js standalone output, production-optimized
- **Persistent volume** — SQLite data survives container restarts
- **Network** — Internal Docker network, frontend proxies `/api/*` to backend

---



<h2 id="project-structure">📂 Project Structure</h2>

```
ratingguard/
├── backend/
│   ├── main.py                  # FastAPI app — SSE streaming endpoint + health check
│   ├── config.py                # Centralized .env → frozen dataclass (single source of truth)
│   ├── database.py              # Async SQLite persistence (products/reviews/analyses tables)
│   ├── scrape_routes.py         # POST /api/scrape — trigger review scraping
│   ├── review_routes.py         # GET /api/reviews — list & detail APIs
│   ├── logger.py                # Dual-output logger (console + file)
│   ├── scraper.py               # Shopify review scraper — 3-strategy parser
│   ├── ai_agent.py              # DeepSeek AI agent — system prompt, streaming client
│   ├── requirements.txt
│   ├── ai_chain/                # Pluggable LLM architecture (community-extensible)
│   │   ├── base.py              #   Abstract LLMDriver interface
│   │   ├── openai_driver.py     #   GPT-4o implementation
│   │   ├── deepseek_driver.py   #   DeepSeek implementation
│   │   ├── prompts.py           #   All prompt templates
│   │   └── parser.py            #   JSON extraction + validation
│   └── utils/
│       ├── helpers.py           #   UA pool, retry decorator, rate limiter
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx         # Main dashboard — dual-panel (reviews + recovery)
│   │   │   ├── layout.tsx       # Root layout with dark mode
│   │   │   └── globals.css      # Global styles + skeleton + cursor animations
│   │   ├── hooks/
│   │   │   ├── useRecoveryStream.ts  # SSE streaming React hook
│   │   │   └── useReviews.ts         # Review state management (scrape/load/select)
│   │   └── lib/
│   │       └── api.ts               # Unified API client (fetch wrappers)
│   ├── package.json
│   ├── tailwind.config.ts       # Custom dark SaaS theme
│   └── next.config.js           # API proxy rewrites → localhost:8000
│
├── Dockerfile.backend           # Python 3.11-slim Docker image
├── Dockerfile.frontend          # Node 20-alpine multi-stage build
├── docker-compose.yml           # Backend + Frontend + persistent volume
├── .env.example                 # Environment template (all keys documented)
├── .gitignore
├── LICENSE                      # MIT License
├── README.md
└── README.zh-CN.md
```

---

<h2 id="api-reference">📡 API Reference</h2>

### `POST /api/stream-recovery`

Analyze a negative review and stream the recovery email in real-time.

**Request Body:**

```json
{
  "review_text": "The bag arrived with a broken zipper",
  "country_code": "US",
  "customer_name": "Sarah",
  "rating": 2,
  "product_title": "Leather Backpack"
}
```

**Response — SSE Event Stream:**

```
data: {"type":"token","content":"{"}
data: {"type":"token","content":"\n  "}
data: {"type":"token","content":"\"reason"}
...
data: {"type":"done","result":{
  "reason_category": "damaged_defective",
  "anger_level": 4,
  "customer_persona": {
    "communication_style": "direct",
    "cultural_traits": "expects prompt resolution",
    "suggested_approach": "..."
  },
  "recovery_email": {
    "subject": "We're so sorry about the zipper, Sarah",
    "body": "Dear [Customer Name],\n\nI'm truly sorry to hear...",
    "language": "en"
  }
}}
```

| Event Type | When | Contains |
|-----------|------|----------|
| `token` | Per LLM delta | `content`: partial text chunk |
| `done` | Stream complete | `result`: full structured analysis + email |
| `error` | API/misconfiguration failure | `message`: error description |

### `POST /api/scrape`

Trigger scraping for a product URL. Stores reviews in the database.

**Request Body:**

```json
{ "product_url": "https://example.myshopify.com/products/product-handle" }
```

**Response:**

```json
{
  "status": "success",
  "product_id": 1,
  "reviews_count": 12,
  "message": "成功抓取 12 条差评"
}
```

### `GET /api/reviews`

List scraped negative reviews (paginated, ≤3 stars only).

| Query Param | Type | Default | Description |
|------------|------|---------|-------------|
| `product_id` | int | — | Filter by product |
| `limit` | int | `50` | Page size (max 200) |
| `offset` | int | `0` | Pagination offset |

### `GET /api/reviews/{id}`

Get a single review with its AI analysis result (if available).

### `GET /health`

```json
{ "status": "ok", "database": "connected", "model": "deepseek-chat", "shopify_domain": "..." }
```

---

<h2 id="extending">🔌 Extending: Adding a New LLM</h2>

RatingGuard's AI chain uses a **strategy pattern** — adding a new model requires just 3 steps:

```python
# 1. Create a new driver in backend/ai_chain/
class ClaudeDriver(LLMDriver):
    def chat(self, messages, **kwargs) -> str: ...
    async def chat_async(self, messages, **kwargs) -> str: ...
    @property
    def model_name(self) -> str: ...

# 2. Add your API key to .env
# 3. Inject into ReviewAgent:  agent = ReviewAgent(client=ClaudeDriver())
```

The system prompt, few-shot examples, JSON parser, and validation layer all remain **unchanged**.

---

<h2 id="roadmap">🗺️ Roadmap</h2>

- [x] Shopify review scraper (3 parsing strategies)
- [x] DeepSeek AI integration with streaming
- [x] Multi-language recovery emails (11 locales)
- [x] SSE real-time SaaS dashboard
- [x] Persistent SQLite storage (products / reviews / analyses)
- [x] Docker deployment (docker-compose, multi-stage builds)
- [x] Amazon review scraping support
- [x] Batch review processing & scheduling
- [x] OAuth / JWT authentication
- [x] Webhook integration (Slack, email)
- [x] A/B testing for recovery email effectiveness
- [x] Analytics dashboard (recovery rate, response metrics)

---

<h2 id="contributing">🤝 Contributing</h2>

Contributions are what make the open-source community such an amazing place. Any ideas, bug reports, or pull requests are **warmly welcome**.

1. Fork the project
2. Create your feature branch (`git checkout -b feature/amazing-idea`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-idea`)
5. Open a Pull Request

---

<h2 id="license">📄 License</h2>

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for more information.

---

<p align="center">
  <b>Built with ❤️ for cross-border e-commerce sellers who refuse to lose customers to bad reviews.</b>
  <br />
  <a href="https://github.com/BanananaCavendish/ratingguard/issues">Report Bug</a>
  ·
  <a href="https://github.com/BanananaCavendish/ratingguard/issues">Request Feature</a>
</p>
