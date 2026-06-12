# Clavra ProdPilot™ — Project Structure

```
clavra/
├── backend/                          # FastAPI Python backend
│   ├── app/
│   │   ├── ai/                       # AI pipeline
│   │   │   ├── intent_engine.py      # Intent detection (GPT-4o → keywords → Ollama)
│   │   │   ├── intent_router.py      # Intent routing + 4 pre-routing override guards
│   │   │   ├── rag_service.py        # RAG pipeline (embed → vector search → answer)
│   │   │   ├── ollama_service.py     # Local Ollama LLM (async thread pool wrapper)
│   │   │   ├── sql_generator.py      # Text-to-SQL for analytics queries
│   │   │   ├── vision_service.py     # Image defect analysis (moondream)
│   │   │   ├── voice_service.py      # Voice transcription helpers
│   │   │   ├── tool_calling.py       # OpenAI function calling bridge
│   │   │   └── provider.py           # AI provider abstraction layer
│   │   ├── core/
│   │   │   ├── security.py           # JWT creation/validation, bcrypt hashing
│   │   │   ├── permissions.py        # RBAC permission checks
│   │   │   └── constants.py          # App-wide enums and constants
│   │   ├── models/                   # SQLAlchemy ORM models
│   │   │   ├── user.py               # User + Organisation
│   │   │   ├── production.py         # ProductionOrder
│   │   │   ├── production_line.py    # ProductionLine
│   │   │   ├── shipment.py           # Shipment
│   │   │   ├── inventory.py          # InventoryItem
│   │   │   ├── quality.py            # QCRecord
│   │   │   ├── knowledge_document.py # Uploaded SOP/policy documents
│   │   │   ├── document_chunk.py     # pgvector-embedded document chunks
│   │   │   ├── ai_chat.py            # Chat session + message history
│   │   │   ├── intent_audit.py       # Intent classification audit log
│   │   │   ├── notification.py       # In-app notifications
│   │   │   ├── planning.py           # Production planning records
│   │   │   └── vision_analysis.py    # Vision/defect analysis results
│   │   ├── routes/                   # FastAPI routers (one file per domain)
│   │   │   ├── ai_chat.py            # WebSocket AI Copilot endpoint
│   │   │   ├── ai_routes.py          # REST AI endpoints (image upload etc.)
│   │   │   ├── auth_routes.py        # /auth/login, /auth/refresh, /auth/me
│   │   │   ├── orders.py             # CRUD + link-shipment for production orders
│   │   │   ├── shipment.py           # Shipment CRUD
│   │   │   ├── inventory.py          # Inventory CRUD
│   │   │   ├── production_lines.py   # Production line management
│   │   │   ├── production.py         # Production summary endpoints
│   │   │   ├── analytics.py          # Order/production analytics
│   │   │   ├── inventory_analytics.py# Inventory trend analytics
│   │   │   ├── knowledge_routes.py   # Document upload + RAG query
│   │   │   ├── quality_routes.py     # QC records
│   │   │   └── notification.py       # Notifications
│   │   ├── schemas/                  # Pydantic v2 request/response models
│   │   ├── services/                 # Business logic layer
│   │   │   ├── ai_service.py         # AI orchestration
│   │   │   ├── auth_service.py       # Auth business logic
│   │   │   ├── production_service.py # Production order logic
│   │   │   ├── shipment_service.py   # Shipment logic
│   │   │   ├── inventory_service.py  # Inventory logic
│   │   │   ├── quality_service.py    # Quality control logic
│   │   │   └── summary_service.py    # Factory summary aggregation
│   │   ├── utils/
│   │   │   └── logger.py             # Structured JSON logging
│   │   ├── config.py                 # Pydantic settings (reads .env)
│   │   ├── database.py               # Async SQLAlchemy engine + session factory
│   │   ├── dependencies.py           # FastAPI dependency injectors (get_db, get_user)
│   │   ├── init_db.py                # DB bootstrap + seed data
│   │   └── main.py                   # FastAPI app + router registration + CORS
│   ├── alembic/                      # Database migrations
│   │   └── versions/                 # 6 migration scripts
│   ├── .env                          # Environment variables (git-ignored)
│   ├── .env.example                  # Template for new developers
│   ├── requirements.txt              # Python dependencies
│   └── Dockerfile                    # Backend Docker image
│
├── frontend/                         # React 18 + TypeScript SPA
│   ├── src/
│   │   ├── pages/
│   │   │   ├── DashboardPage.tsx     # KPI dashboard with charts
│   │   │   ├── AICopilotPage.tsx     # AI chat interface (WebSocket streaming)
│   │   │   ├── ProductionPage.tsx    # Orders + inline progress/date/shipment editing
│   │   │   ├── ProductionLinePage.tsx# Line A/B/C/D status
│   │   │   ├── ShipmentPage.tsx      # Shipment tracking
│   │   │   ├── InventoryPage.tsx     # Inventory management
│   │   │   ├── QualityPage.tsx       # QC records
│   │   │   ├── KnowledgePage.tsx     # RAG document upload + query
│   │   │   └── LoginPage.tsx         # JWT auth
│   │   ├── components/
│   │   │   ├── chat/
│   │   │   │   ├── ChatBubble.tsx    # Message bubbles with markdown rendering
│   │   │   │   ├── IntentBadge.tsx   # Intent + confidence badge
│   │   │   │   ├── VoiceButton.tsx   # Web Speech API voice input button
│   │   │   │   ├── ImageUploadZone.tsx# Drag-drop for defect image analysis
│   │   │   │   ├── SourceCitation.tsx# RAG document citations
│   │   │   │   ├── SqlViewPanel.tsx  # Expandable SQL view for analytics
│   │   │   │   └── TypingIndicator.tsx# Animated "thinking" dots
│   │   │   └── ui/                   # Button, Card, Input, Badge
│   │   ├── hooks/
│   │   │   ├── useAIChat.ts          # WebSocket chat hook
│   │   │   ├── useAuth.ts            # Auth state hook
│   │   │   └── useVoice.ts           # Voice input hook
│   │   ├── store/
│   │   │   ├── authStore.ts          # Zustand auth store
│   │   │   └── chatStore.ts          # Zustand chat store
│   │   ├── api/                      # Axios instance + interceptors
│   │   ├── services/                 # REST API + auth services
│   │   └── widgets/                  # Dashboard mini-widgets
│   ├── tailwind.config.js
│   ├── vite.config.ts
│   ├── package.json
│   └── Dockerfile
│
├── docker-compose.yml                # One-command full-stack deployment
├── nginx.conf                        # Production reverse proxy config
└── uploads/docs/                     # Knowledge base document storage
```

## Key Architecture Decisions

| Decision | Choice | Reason |
|---|---|---|
| Async framework | FastAPI + asyncpg | Non-blocking I/O for concurrent WebSocket streams |
| ORM | SQLAlchemy 2.0 async | Type-safe queries + Alembic migration support |
| Vector DB | pgvector (PostgreSQL extension) | Single DB for relational + vector — no extra service |
| State management | Zustand | Minimal boilerplate, simpler than Redux |
| Styling | Tailwind CSS v4 | Utility-first, consistent dark theme |
| AI fallback chain | GPT-4o → keywords → Ollama | Graceful degradation without OpenAI API key |
| Auth | JWT + refresh token rotation | Stateless, horizontally scalable |
| Embeddings | text-embedding-3-small (1536d) | Cost-effective; keyword fallback works without OpenAI |

## Database Schema (Key Tables)

| Table | Key Columns |
|---|---|
| users | id, email, hashed_password, role, org_id |
| organisations | id, name, plan |
| production_orders | id, order_no, buyer, status, total_qty, produced_qty, defect_qty, delivery_date, org_id |
| production_lines | id, line_name, status, current_order_id, efficiency_pct, org_id |
| shipments | id, shipment_no, status, order_id, destination, estimated_delivery, org_id |
| inventory_items | id, material_name, quantity, unit, reorder_level, supplier, org_id |
| knowledge_documents | id, original_name, doc_type, file_path, chunk_count, org_id |
| document_chunks | id, document_id, content, embedding (vector 1536), page_number |
| ai_messages | id, session_id, role, content, intent, confidence, action_type |
