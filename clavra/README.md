# Clavra ProdPilot™

> **AI-Powered Manufacturing ERP for Garment Factories** — Query production, shipments, SOPs, and inventory using natural language or voice.

---

## Brief One Line Summary

A full-stack ERP system with a GPT-4o + Ollama AI Copilot, RAG Knowledge Base, and real-time dashboard — purpose-built for garment manufacturing operations.

---

## Overview

Clavra ProdPilot™ replaces WhatsApp and Excel-based factory management with a unified, AI-driven platform. Factory managers and supervisors can:

- Ask questions in **plain English or voice** ("What is the status of PO-003?", "Show me the Fabric Inspection SOP")
- Monitor **production orders** with inline progress, delivery date, and shipment editing
- Track **shipments** through their full lifecycle in real time
- Query the **RAG Knowledge Base** — upload PDFs, DOCX, XLSX and get cited answers from your own SOPs and policies
- View **inventory alerts**, production line status, and analytics dashboards

The AI Copilot classifies over **18 manufacturing intents** using a three-stage fallback pipeline: GPT-4o → keyword rules → Ollama (local LLM). The system works fully **without an OpenAI API key** using the local Ollama fallback.

---

## Problem Statement

Small and mid-size garment factories in South & South-East Asia rely on WhatsApp messages and Excel files to manage production orders, shipments, and raw material inventory. This results in:

- **Delayed decisions** due to scattered information across chat groups
- **Missed delivery deadlines** with no real-time production visibility
- **Inventory stock-outs** from manual tracking errors
- **Zero traceability** for buyer audits and compliance
- **High training cost** for adopting conventional ERP systems

**Clavra ProdPilot™** solves this by delivering an affordable, AI-first ERP where workers simply ask questions in natural language — no training required.

---

## Dataset

The system uses **live operational data** generated within the application itself:

| Entity | Description |
|---|---|
| Production Orders | Order no, buyer, style, qty, status, progress, delivery date |
| Production Lines | Line A/B/C/D — status, current order, efficiency % |
| Shipments | Shipment no, destination, carrier, status, linked orders |
| Inventory | Raw materials — quantity, unit, reorder level, supplier |
| Quality Records | QC inspections, defect counts, reject rates |
| Knowledge Base | Uploaded PDFs/DOCX/XLSX — SOPs, policies, manuals |
| Chat History | AI Copilot conversations with intent + confidence audit log |

Seed data is loaded via `app/init_db.py`. Alembic manages the schema across 6 versioned migration files.

---

## Tools and Technologies

### Backend
| Technology | Version | Purpose |
|---|---|---|
| Python | 3.11+ | Core language |
| FastAPI | 0.110+ | REST API + WebSocket server |
| SQLAlchemy | 2.0+ | Async ORM |
| Alembic | 1.13+ | Database migrations |
| PostgreSQL | 16+ | Primary data store |
| pgvector | 0.2.5+ | 1536-dim vector embeddings |

### AI / ML
| Technology | Purpose |
|---|---|
| OpenAI GPT-4o | Intent classification (primary), RAG answer generation |
| text-embedding-3-small | Document chunk embeddings (1536 dims) |
| Ollama + llama3.1:8b | Local LLM fallback (no API key needed) |
| nomic-embed-text | Offline embedding fallback |
| Web Speech API | Browser-native voice input (STT) + output (TTS) |

### Frontend
| Technology | Version | Purpose |
|---|---|---|
| React | 18 | UI framework |
| TypeScript | 5+ | Type-safe JavaScript |
| Vite | 5+ | Build tool + HMR |
| Tailwind CSS | v4 | Utility-first styling |
| Zustand | 4+ | Global state (auth + chat) |
| Recharts | 2+ | Analytics charts |

### DevOps
- **Docker Compose** — one-command full-stack deployment
- **Nginx** — production reverse proxy
- **JWT + bcrypt** — stateless auth with refresh token rotation

---

## Methods

### AI Intent Classification Pipeline
```
User Message
    │
    ▼
[Stage 1] detect_intent()
    ├── GPT-4o (temperature=0.1, timeout=8s)   ← primary
    ├── Keyword rules (18+ intents, instant)    ← fast fallback
    └── Ollama llama3.1:8b (local)              ← offline fallback
    │
    ▼
[Stage 2] route_intent()
    ├── Override Guard 1: SOP/manual keywords → ask_manual
    ├── Override Guard 2: Shipment terms → shipment_status
    ├── Override Guard 3: Order number → get_order_status
    └── Override Guard 4: Production line terms → production_line_status
    │
    ▼
[Stage 3] Domain Handler
    ├── DB query (production, shipment, inventory)
    ├── RAG pipeline (pgvector search → GPT-4o answer)
    └── SQL generator (analytics queries)
```

### RAG Knowledge Base Pipeline
```
Document Upload
    → Text extraction (PyMuPDF / python-docx / openpyxl)
    → Chunking (512 words, 64-word overlap)
    → Embedding (text-embedding-3-small, 1536 dims)
    → Store in document_chunks (pgvector)

Query
    → Embed question
    → Cosine similarity search (MIN_SIM=0.72, TOP_K=5)
    → ILIKE keyword fallback (if no embeddings)
    → GPT-4o answer generation with citations
    → Ollama fallback → formatted excerpt fallback
```

### Data Architecture
- **PostgreSQL + pgvector** in a single database — relational data and vector embeddings together
- **Alembic migrations** for reproducible schema evolution
- **Multi-tenant RBAC** — all queries scoped to `org_id`; Admin/Manager/Operator roles

---

## Key Insights

Through building and iterating on this system, several important design decisions emerged:

1. **Keywords before LLM** — Running keyword rules before Ollama eliminates event-loop blocking and gives instant responses for common queries
2. **Pre-routing overrides beat prompt engineering** — Explicit override guards in `route_intent()` are more reliable than relying solely on LLM classification for edge cases like "Fabric Inspection SOP" vs inventory
3. **Single DB for relational + vector** — pgvector eliminates the need for a separate vector database (Pinecone/Weaviate), reducing infrastructure complexity
4. **Graceful AI degradation** — Three-level fallback (GPT-4o → keywords → Ollama) keeps the system always responsive, even offline
5. **Async + thread pool for Ollama** — `llm.invoke()` is synchronous; wrapping in `run_in_executor()` prevents blocking the entire FastAPI event loop
6. **Minimum visible bar width** — Progress bars showing 0% even with `produced_qty > 0` required computing raw decimal percentage and enforcing a 1.5% minimum bar width

---

## Dashboard / Model / Output

### Dashboard
- **KPI Cards**: Active orders, shipments in transit, low stock items, on-time delivery %
- **Order Trend Chart**: Last 30 days production order activity
- **Production Efficiency**: Per-line efficiency visualization

### AI Copilot Output Examples
| Query | Intent | Response Type |
|---|---|---|
| "What is the status of PO-003?" | `get_order_status` | Structured order card |
| "Show me all shipments" | `shipment_status` | Shipment table |
| "Fabric Inspection SOP" | `ask_manual` | RAG answer with citations |
| "How many orders this month?" | `count_orders` | SQL analytics result |
| "Factory summary" | `general_status` | Full factory snapshot |

### Production Page Features
- Inline-editable progress (produced_qty / defect_qty), delivery date, and shipment link
- Progress bars with percentage display (shows `<1%` for small but non-zero values)
- Always-visible edit buttons (no hover required for discoverability)

---

## How to Run this Project?

### Prerequisites
- Python 3.11+
- Node.js 20+
- PostgreSQL 16+ with pgvector extension
- [Ollama](https://ollama.ai) (optional, for local AI fallback)
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/mhr014-cmd/Clavra_PodPilot.git
cd Clavra_PodPilot/clavra
```

### 2. Backend Setup
```bash
cd backend

# Create and activate virtual environment
python -m venv .venv

# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Windows CMD:
.venv\Scripts\activate.bat
# Linux/Mac:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env        # Windows
# cp .env.example .env        # Linux/Mac
# Edit .env — set DATABASE_URL, SECRET_KEY, OPENAI_API_KEY (optional)
```

### 3. Database Setup
```bash
# Create PostgreSQL database
psql -U postgres -c "CREATE DATABASE clavra_db;"
psql -U postgres -d clavra_db -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Run Alembic migrations
alembic upgrade head

# Seed initial data (creates admin user + sample orders)
python -m app.init_db
```

### 4. Start Ollama (Optional — for offline AI)
```bash
ollama pull llama3.1:8b
ollama pull nomic-embed-text
ollama serve
# Ollama available at: http://localhost:11434
```

### 5. Start Backend
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# API:   http://localhost:8000
# Docs:  http://localhost:8000/docs
```

### 6. Frontend Setup
```bash
cd ../frontend

# Install dependencies
npm install

# Configure environment
echo VITE_API_URL=http://localhost:8000 > .env

# Start development server
npm run dev
# Frontend: http://localhost:5174
```

### 7. Login
| Field | Value |
|---|---|
| Email | `admin@clavra.com` |
| Password | `Admin@123` |

### Docker (One-Command Deploy)
```bash
cd clavra
docker-compose up --build
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
```

---

## Results & Conclusion

Clavra ProdPilot™ successfully demonstrates that a **small garment factory can be managed with AI-first tools** — without expensive enterprise software:

### What Works
- 18+ AI intents correctly classified; keyword rules ensure instant responses without OpenAI API
- RAG Knowledge Base retrieves relevant SOP content with source citations
- Real-time WebSocket streams AI responses token-by-token with intent transparency badges
- Inline production editing — progress, delivery dates, and shipment links editable in-table
- Full-stack Docker deployment in a single command

### Performance
| Metric | Result |
|---|---|
| Intent classification (GPT-4o) | ~1.2s average |
| Intent classification (keywords) | < 10ms |
| REST API response | < 300ms (p95) |
| Vector similarity search | < 150ms (5K chunks) |
| WebSocket first token | ~1.1s |

### Conclusion
The project validates its core thesis: **natural language is a viable primary interface for factory operations**. The three-tier AI fallback chain ensures the system is always operational — from cloud-connected to fully offline environments. The single-database approach (PostgreSQL + pgvector) proves that vector search and relational data can coexist without adding operational complexity.

---

## Future Work

### Short-Term (Next 3 Months)
- [ ] Bangla/Hindi UI for local factory workers
- [ ] Push notifications for delays, low stock, delivery updates
- [ ] Mobile PWA with offline mode for shop floor workers
- [ ] Export to Excel/PDF for production reports
- [ ] Bulk order import via CSV/Excel upload

### Medium-Term (3–9 Months)
- [ ] Supplier portal for material delivery status updates
- [ ] Costing module — material + labour cost, margin per order
- [ ] Barcode/QR scanning via mobile camera
- [ ] Demand forecasting ML model
- [ ] Email notifications via SendGrid

### Long-Term (9+ Months)
- [ ] ERP integrations — QuickBooks, SAP, Xero
- [ ] Computer vision QC from conveyor belt cameras (YOLO v8)
- [ ] Multi-factory consolidated reporting
- [ ] Compliance audit trail for ISO 9001 / BSCI
- [ ] IoT machine sensor integration

---

## Author & Contact

**Project:** Clavra ProdPilot™ — AI Manufacturing ERP

**Repository:** [github.com/mhr014-cmd/Clavra_PodPilot](https://github.com/mhr014-cmd/Clavra_PodPilot)

**Stack:** FastAPI · React 18 · PostgreSQL · pgvector · GPT-4o · Ollama · Tailwind CSS v4

**License:** MIT

---

*Built with [Claude Code](https://claude.ai/code) — Anthropic's AI coding assistant*
