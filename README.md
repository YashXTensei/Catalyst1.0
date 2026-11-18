# DecisionTrail 🧭
> **AI-Powered Engineering Decision Intelligence Platform**

DecisionTrail extracts critical, hidden architectural decisions from GitHub issues, pull requests, reviews, and community discussions. It transforms scattered developer conversations into persistent project memory, enabling instant natural-language question answering and automated pull request conflict analysis.

---

## 🚀 Key Features

1. **GitHub Repository Connection**: Connect any public GitHub repository URL or slug (`https://github.com/owner/repo` or `owner/repo`).
2. **Historical Decision Extraction**: Extracts structured engineering decisions including decision summaries, accepted/rejected statuses, reasoning, rejected alternatives, affected components, code paths, direct evidence excerpts, and original discussion URLs.
3. **Structured Project Memory**: Persistent storage with PostgreSQL (pgvector) and local SQLite fallback, vector embeddings (Gemini `text-embedding-004` or deterministic semantic embeddings), and hybrid retrieval.
4. **Question-First Answering**: Answers technical questions immediately via targeted GitHub search and cached memory without forcing the user to wait for full repository indexing.
5. **PR Intelligence & Architectural Drift Detection**: Analyzes pull request changes against historical decisions to identify conflicts, regressions, and re-introduction of previously rejected libraries.
6. **Extensible Connector Architecture**: Unified interface supporting GitHub, Discourse forums, and future sources (Slack, Linear, etc.).

---

## 🏗️ System Architecture

```
                  ┌────────────────────────────────────────┐
                  │          React + Vite Frontend         │
                  │   (Dashboard, Q&A, Explorer, PR Intel) │
                  └───────────────────┬────────────────────┘
                                      │ REST / JSON
                                      ▼
                  ┌────────────────────────────────────────┐
                  │           FastAPI Backend              │
                  ├───────────────────┬────────────────────┤
                  │   Router Layer    │ /api/repositories  │
                  ├───────────────────┼────────────────────┤
                  │   Agents Layer    │ DecisionExtractor  │
                  │                   │ QuestionAnswering  │
                  │                   │ PRIntelligence     │
                  ├───────────────────┼────────────────────┤
                  │  Services Layer   │ GitHubService      │
                  │                   │ MemoryService      │
                  │                   │ CodeMappingService │
                  ├───────────────────┼────────────────────┤
                  │  Integrations     │ GitHub / Discourse │
                  └─────────┬───────────────────┬──────────┘
                            │                   │
                            ▼                   ▼
                  ┌───────────────────┐ ┌───────────────────┐
                  │ PostgreSQL /      │ │   Gemini 2.5 /    │
                  │ SQLite + pgvector │ │ Embedding Engine  │
                  └───────────────────┘ └───────────────────┘
```

---

## 📦 Tech Stack

- **Frontend**: React 19, Vite, Tailwind CSS v4, Axios, Lucide React
- **Backend**: Python 3.13, FastAPI, Pydantic v2, SQLAlchemy 2.0
- **AI & Embeddings**: Google GenAI SDK (`gemini-2.5-flash`, `text-embedding-004`)
- **Database**: PostgreSQL with `pgvector` extension (with automatic SQLite fallback)
- **External Data**: GitHub REST API & Discourse API

---

## ⚙️ Environment Variables

Create `backend/.env` (see `backend/.env.example`):

```bash
# Database (PostgreSQL with pgvector or SQLite)
DATABASE_URL=sqlite:///./decisiontrail.db
# Or PostgreSQL:
# DATABASE_URL=postgresql://postgres:password@localhost:5432/decisiontrail

# AI Provider (Gemini API)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
EMBEDDING_MODEL=text-embedding-004

# GitHub API Token (Optional, but increases rate limits from 60 to 5,000/hr)
GITHUB_TOKEN=your_github_personal_access_token

# Server Configuration
PORT=8000
HOST=0.0.0.0
CORS_ORIGINS=http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173
DEBUG=True
```

---

## 🏃 Quick Start Guide

### 1. Start the Backend

```bash
cd backend
# Optional: create virtual environment
python -m venv venv
venv\Scripts\activate   # Windows
# or: source venv/bin/activate  # macOS / Linux

pip install -r requirements.txt

# Run FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Check health endpoint: `http://localhost:8000/api/health`  
Interactive Swagger docs: `http://localhost:8000/docs`

### 2. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```
Open your browser at `http://localhost:5173`

---

## 🧪 Running Backend Tests

```bash
cd backend
$env:PYTHONPATH="."
python tests/test_backend.py
```
All 9 unit and integration tests verify:
- Health check and DB connection
- Repository URL parsing
- Code mapping and PR file overlap detection
- Vector embeddings and cosine similarity
- Deduplication and database persistence
- Question Answering pipeline with citations
- Pull Request conflict analysis

---

## 🔌 API Endpoints Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | System health, database status, and configured providers |
| `GET` | `/api/repositories` | List all connected repositories |
| `POST` | `/api/repositories/connect` | Connect a GitHub repository and initiate Question-First indexing |
| `GET` | `/api/repositories/{id}/status` | Live indexing progress, discussion count, decision count |
| `POST` | `/api/repositories/{id}/index` | Trigger background indexing |
| `GET` | `/api/repositories/{id}/decisions` | Filter and search extracted engineering decisions |
| `POST` | `/api/repositories/{id}/ask` | Natural language question answering with citations |
| `POST` | `/api/repositories/{id}/pull-requests/analyze` | Architectural drift and conflict analysis for a PR |
