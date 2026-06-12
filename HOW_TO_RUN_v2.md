# Clavra ProdPilot™ — How to Run (v2 Final)
> Follow every step in order. Do not skip any step.

---

## What You Need First

Install these before starting. Check versions with the commands shown.

| Tool | Min Version | Check | Download |
|---|---|---|---|
| Python | 3.11+ | `python --version` | python.org |
| Node.js | 18+ | `node --version` | nodejs.org |
| PostgreSQL | 15+ | `psql --version` | postgresql.org |
| pgvector extension | latest | installed in Step 3 | github.com/pgvector/pgvector |
| OpenAI API key | — | — | platform.openai.com |

---

## STEP 1 — Extract the project

Download **Clavra_ProdPilot_v2_FINAL.zip** and extract it.
You will get a folder called `clavra/`.

```
clavra/
├── backend/       ← Python FastAPI
├── frontend/      ← React TypeScript
├── uploads/       ← auto-created at runtime
├── docker-compose.yml
└── nginx.conf
```

Open the `clavra/` folder in **PyCharm** (recommended for backend) or **VS Code**.

---

## STEP 2 — Create the PostgreSQL database

Open a terminal and run:

```sql
psql -U postgres
```

Then paste these commands one by one:

```sql
CREATE DATABASE clavra_prodpilot;
\c clavra_prodpilot
CREATE EXTENSION IF NOT EXISTS vector;
\q
```

**Verify pgvector installed correctly:**
```sql
psql -U postgres -d clavra_prodpilot -c "SELECT extname FROM pg_extension WHERE extname = 'vector';"
```
You should see `vector` in the output.

**If pgvector is not installed on your system:**
- Windows: Download from https://github.com/pgvector/pgvector/releases
- Mac: `brew install pgvector`
- Linux: `sudo apt install postgresql-15-pgvector`

---

## STEP 3 — Backend setup

Open a terminal in the `clavra/backend/` folder.

### 3a — Create virtual environment

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Mac / Linux
python -m venv .venv
source .venv/bin/activate
```

Your prompt will show `(.venv)` when active.

### 3b — Install packages

```bash
pip install -r requirements.txt
```

Takes 3–5 minutes. If `pymupdf` fails try: `pip install pymupdf --upgrade`

### 3c — Configure environment variables

Open `backend/.env` in a text editor. Change these two lines:

```env
# Change YOUR_PASSWORD to your actual PostgreSQL password
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/clavra_prodpilot

# Paste your real OpenAI API key (get from platform.openai.com)
OPENAI_API_KEY=sk-proj-your-real-key-here
```

Everything else can stay as-is for local development.

**No OpenAI key?** Set `AI_PROVIDER=ollama` — the app will use Ollama locally.
Install Ollama from ollama.com and run: `ollama pull llama3.1:8b`

### 3d — Run database migrations

```bash
alembic upgrade head
```

You should see 6 migrations run in order:
```
Running upgrade  -> 9a2ba3c27ae0, inventory
Running upgrade 9a2ba3c27ae0 -> 1e486bb50d96, auth
Running upgrade 1e486bb50d96 -> 41b70be6c647, production_lines
Running upgrade 41b70be6c647 -> 0002_stage2_rbac_org
Running upgrade 0002_stage2_rbac_org -> 0003_rag_vector_tables
Running upgrade 0003_rag_vector_tables -> 0004_quality_planning
```

**If migration 0003 fails with "type vector does not exist":**
```bash
psql -U postgres -d clavra_prodpilot -c "CREATE EXTENSION IF NOT EXISTS vector;"
alembic upgrade head
```

### 3e — Create your admin user

```bash
python
```

Then paste this entire block and press Enter:

```python
import asyncio
from app.database import AsyncSessionLocal
from app.models.user import User
from app.models.organization import Organization
from app.core.security import hash_password

async def create_admin():
    async with AsyncSessionLocal() as db:
        org = Organization(name="My Factory", slug="my_factory_01")
        db.add(org)
        await db.flush()
        user = User(
            full_name="Admin User",
            email="admin@clavra.com",
            password_hash=hash_password("Admin@123"),
            role="admin",
            org_id=org.id,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        print("✓ Admin created: admin@clavra.com / Admin@123")

asyncio.run(create_admin())
exit()
```

### 3f — Start the backend server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

**Test it:** Open http://localhost:8000 — you should see:
```json
{"status": "running", "app": "Clavra ProdPilot™", "version": "2.0.0"}
```

**Full API docs:** http://localhost:8000/docs

---

## STEP 4 — Frontend setup

Open a **second terminal** (keep backend running in the first one).

```bash
cd clavra/frontend
npm install
```

Takes 1–3 minutes.

### 4a — Check the .env file

Make sure `frontend/.env` contains:

```env
VITE_API_URL=http://127.0.0.1:8000
VITE_WS_URL=ws://127.0.0.1:8000
```

If the file doesn't exist, create it with that content.

### 4b — Start the frontend

```bash
npm run dev
```

You should see:
```
VITE v5.x ready
➜ Local: http://localhost:5173/
```

---

## STEP 5 — Open the app and log in

Open your browser and go to: **http://localhost:5173**

You will be redirected to the login page.

```
Email:    admin@clavra.com
Password: Admin@123
```

After login you land on the **Dashboard**.

---

## STEP 6 — Add seed data (recommended)

The database starts empty. Add some data to see everything working.

### Option A — Use the UI

- **Production** page → Create a few orders (e.g. order no: PO-001, buyer: H&M, style: T-Shirt, qty: 5000)
- **Shipments** page → Create a shipment (e.g. SHP-001, buyer: H&M, destination: Germany)
- **Inventory** page → Add materials (e.g. FAB-001, Cotton Fabric, Fabric, Roll, 500)
- **Quality** page → Log a quality report

### Option B — Quick Python seed script

With your `.venv` active in `backend/`:

```bash
python
```

```python
import asyncio
from app.database import AsyncSessionLocal
from app.models.production import ProductionOrder
from app.models.shipment import Shipment
from app.models.inventory import Inventory
from app.models.production_line import ProductionLine

async def seed():
    async with AsyncSessionLocal() as db:
        # Production lines
        for name, sup, eff in [("Line A","Rahim",92),("Line B","Karim",95),("Line C","Jamal",65)]:
            db.add(ProductionLine(line_name=name, supervisor=sup, status="Running",
                                  target_output=1200, actual_output=int(1200*eff/100),
                                  efficiency=eff, defects=10, operators=35))
        # Orders
        for no, buyer, style, qty, status in [
            ("PO-001","H&M","T-Shirt",5000,"Sewing"),
            ("PO-002","Zara","Polo",12000,"Cutting"),
            ("PO-003","Next","Jacket",3000,"Completed"),
        ]:
            db.add(ProductionOrder(order_no=no, buyer=buyer, style=style,
                                   quantity=qty, status=status, org_id=1))
        # Shipments
        for no, buyer, dest, status in [
            ("SHP-001","H&M","Germany","In Transit"),
            ("SHP-002","Zara","Spain","Pending"),
        ]:
            db.add(Shipment(shipment_no=no, buyer=buyer, destination=dest,
                            status=status, org_id=1))
        # Inventory
        for code, name, cat, unit, qty in [
            ("FAB-001","Cotton Fabric","Fabric","Roll",500),
            ("THR-002","Polyester Thread","Accessories","Cone",300),
            ("BTN-003","Plastic Button","Accessories","Bag",1000),
        ]:
            db.add(Inventory(material_code=code, material_name=name, category=cat,
                             unit=unit, stock_qty=qty, reserved_qty=0,
                             available_qty=qty, status="In Stock"))
        await db.commit()
        print("✓ Seed data added")

asyncio.run(seed())
exit()
```

Refresh the Dashboard — you should see charts and KPI numbers.

---

## STEP 7 — Test the AI Copilot

Go to **AI Copilot** in the sidebar (supervisor role and above can access it).

Type these messages to test each pipeline branch:

| Message | What should happen |
|---|---|
| `Show my last 3 orders` | Intent badge: **Action** — lists orders from DB |
| `How many orders are pending?` | Intent badge: **SQL** — generates and runs a SELECT query |
| `What is our refund policy?` | Intent badge: **Docs** — searches uploaded PDFs (upload one first) |
| `Cancel order PO-001` | Intent badge: **Action** — cancels the order in DB |
| `xyz abc 123` | Intent badge: **?** — asks for clarification |

### Test voice input

Click the microphone button (🎙), speak a question, tap again to stop.
The transcript appears in the input box. Send it normally.
Requires: OpenAI API key + microphone permission in browser.

### Upload a knowledge document

Go to **Knowledge Base** in the sidebar.
Upload any PDF (policy document, SOP, machine manual).
Wait 10–30 seconds for embedding to complete.
Then ask the AI Copilot: `What does the document say about [topic]?`
The response will include a source citation showing the document name and page number.

---

## STEP 8 — Create more users (optional)

To test different roles, create additional users. In the Python shell (`backend/` with venv active):

```python
import asyncio
from app.database import AsyncSessionLocal
from app.models.user import User
from app.core.security import hash_password

async def add_users():
    async with AsyncSessionLocal() as db:
        users = [
            ("Manager User",      "manager@clavra.com",     "manager"),
            ("Supervisor User",   "supervisor@clavra.com",  "supervisor"),
            ("QC Inspector",      "qc@clavra.com",          "qc_inspector"),
            ("Viewer User",       "viewer@clavra.com",      "viewer"),
        ]
        for name, email, role in users:
            db.add(User(full_name=name, email=email,
                        password_hash=hash_password("Test@123"),
                        role=role, org_id=1, is_active=True))
        await db.commit()
        print("✓ Users created — password: Test@123")

asyncio.run(add_users())
exit()
```

Log in with each user to see how role-based access controls work:
- **viewer** → cannot access AI Copilot or Knowledge Base
- **qc_inspector** → same restrictions
- **supervisor** → full access including AI Copilot
- **manager / admin** → full access to everything

---

## STEP 9 — Mobile (Android PWA)

### Install on Android phone

1. Make sure your computer and phone are on the **same Wi-Fi network**
2. Find your computer's local IP address:
   - Windows: `ipconfig` → look for IPv4 Address (e.g. 192.168.1.100)
   - Mac/Linux: `ifconfig` → look for inet (e.g. 192.168.1.100)
3. Start the frontend with host enabled (already set in vite.config.ts)
4. Open **Chrome** on your Android phone
5. Navigate to `http://192.168.1.100:5173` (replace with your IP)
6. Tap the **three dots menu** → **Add to Home screen**
7. The app installs as a standalone app on your phone

All features work on mobile — including voice input (tap the mic button).

---

## STEP 10 — Run with Docker (all-in-one, optional)

If you have **Docker Desktop** installed:

```bash
cd clavra/
docker compose up --build
```

This starts everything automatically: PostgreSQL (with pgvector), Redis, backend, frontend, nginx.

Access:
- App: http://localhost:3000
- API: http://localhost:8000
- Docs: http://localhost:8000/docs

Create admin user in Docker:
```bash
docker exec -it clavra_backend python -c "
import asyncio
from app.database import AsyncSessionLocal
from app.models.user import User
from app.models.organization import Organization
from app.core.security import hash_password

async def setup():
    async with AsyncSessionLocal() as db:
        org = Organization(name='My Factory', slug='factory_docker_01')
        db.add(org)
        await db.flush()
        db.add(User(full_name='Admin', email='admin@clavra.com',
                    password_hash=hash_password('Admin@123'),
                    role='admin', org_id=org.id, is_active=True))
        await db.commit()
        print('Done')
asyncio.run(setup())
"
```

Stop everything: `docker compose down`

---

## Troubleshooting

### Backend won't start — ImportError or ModuleNotFoundError
```bash
# Make sure virtual env is active
.venv\Scripts\activate   # Windows
source .venv/bin/activate  # Mac/Linux
pip install -r requirements.txt
```

### `password authentication failed for user postgres`
Edit `backend/.env` → fix the password in `DATABASE_URL`

### `alembic upgrade head` fails with "vector type not found"
```bash
psql -U postgres -d clavra_prodpilot -c "CREATE EXTENSION IF NOT EXISTS vector;"
alembic upgrade head
```

### `alembic upgrade head` fails with "multiple heads"
```bash
alembic heads        # shows the conflicting heads
alembic upgrade head --resolve-conflicts
```

### AI says "OpenAI API key required"
Edit `backend/.env` → set `OPENAI_API_KEY=sk-proj-your-real-key`
Restart the backend server.

### Login fails — "Invalid email or password"
Make sure you ran the admin user creation script in Step 3e.
The email is `admin@clavra.com` and password is `Admin@123`.

### Frontend shows blank white page
```bash
cd clavra/frontend
cat .env  # must show VITE_API_URL=http://127.0.0.1:8000
npm run dev
```

### CORS error in browser console
Edit `backend/.env`:
```
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
```
Restart the backend.

### Dashboard shows zeros / no data
Run the seed script in Step 6, Option B.

### AI Copilot not in sidebar
Only `supervisor`, `manager`, and `admin` roles can see it.
Log in with `admin@clavra.com`.

---

## Quick Reference

```
Two terminals needed:
  Terminal 1 — backend:
    cd clavra/backend
    .venv\Scripts\activate   (or source .venv/bin/activate)
    uvicorn app.main:app --reload --port 8000

  Terminal 2 — frontend:
    cd clavra/frontend
    npm run dev

URLs:
  App:      http://localhost:5173
  API:      http://localhost:8000
  API docs: http://localhost:8000/docs

Login:
  Email:    admin@clavra.com
  Password: Admin@123

Migration chain (must run in this order):
  9a2ba3c → 1e486bb → 41b70be → 0002 → 0003 → 0004

AI test queries:
  "Show last 5 orders"          → Action (DB query)
  "How many pending orders?"    → SQL (generated query)
  "What is the return policy?"  → Docs (RAG search)
  "Cancel order PO-001"         → Action (cancels in DB)
  [upload defect image]         → Vision (GPT-4o analysis)
  [speak into mic]              → Voice (Whisper → AI → TTS)
```

---

*Clavra ProdPilot™ · Manufacturing AI Operating System · by Clavra · v2.0*
