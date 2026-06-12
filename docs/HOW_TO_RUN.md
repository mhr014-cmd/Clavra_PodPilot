# How to Run Clavra ProdPilot™
## Step-by-Step Guide — PyCharm & PowerShell

---

## Prerequisites

Install these before starting:

| Tool | Version | Download |
|---|---|---|
| Python | 3.11+ | https://python.org/downloads |
| Node.js | 20+ | https://nodejs.org |
| PostgreSQL | 16+ | https://postgresql.org/download |
| pgvector extension | latest | Installed via psql (step below) |
| Git | latest | https://git-scm.com |
| Ollama (optional) | latest | https://ollama.ai |
| PyCharm (optional) | Community/Pro | https://jetbrains.com/pycharm |

---

## Part A — PowerShell Setup (Step by Step)

### Step 1: Clone the Repository

```powershell
git clone https://github.com/mhr014-cmd/Clavra_PodPilot.git
cd Clavra_PodPilot\clavra
```

---

### Step 2: PostgreSQL Database Setup

Open **pgAdmin** or run in PowerShell (replace `your_password` with your postgres password):

```powershell
# Connect to PostgreSQL and create database
psql -U postgres -c "CREATE DATABASE clavra_db;"
psql -U postgres -d clavra_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

> If `psql` is not in PATH, find it in: `C:\Program Files\PostgreSQL\16\bin\psql.exe`

---

### Step 3: Backend — Virtual Environment

```powershell
cd backend

# Create virtual environment
python -m venv .venv

# Activate it
.\.venv\Scripts\Activate.ps1

# If you get an execution policy error, run this first:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Verify activation (should show .venv in prompt)
python --version
```

---

### Step 4: Install Python Dependencies

```powershell
# With venv active:
pip install -r requirements.txt

# This installs: FastAPI, SQLAlchemy, pgvector, openai, langchain-ollama,
# pymupdf, python-jose, passlib, and all other dependencies
```

---

### Step 5: Configure Environment Variables

```powershell
# Copy the example file
copy .env.example .env

# Open .env in notepad and fill in values:
notepad .env
```

Edit `.env` with these values:

```
DATABASE_URL=postgresql+asyncpg://postgres:your_password@localhost:5432/clavra_db
SECRET_KEY=your-secret-key-here-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Optional — leave blank to use keyword/Ollama fallback:
OPENAI_API_KEY=sk-your-openai-key-here

# Ollama (runs locally)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
```

---

### Step 6: Run Database Migrations

```powershell
# Still in backend/ with .venv active:
alembic upgrade head

# You should see output like:
# INFO  [alembic.runtime.migration] Running upgrade -> 1e486bb50d96, auth
# INFO  [alembic.runtime.migration] Running upgrade 1e486bb50d96 -> 0002, stage2_rbac_org
# ... (6 migrations total)
```

---

### Step 7: Seed Initial Data

```powershell
python -m app.init_db

# This creates:
# - Default organisation (Clavra Factory)
# - Admin user: admin@clavra.com / Admin@123
# - Sample production orders, shipments, inventory items
```

---

### Step 8: Start Ollama (Optional — Local AI)

Open a **new PowerShell window** and run:

```powershell
# Pull models (one-time setup, ~5GB download)
ollama pull llama3.1:8b
ollama pull nomic-embed-text

# Start Ollama server
ollama serve
# Runs at: http://localhost:11434
```

> Without Ollama, the AI Copilot still works via OpenAI (if key set) or keyword rules.

---

### Step 9: Start the Backend Server

```powershell
# In backend/ with .venv active:
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Expected output:
# INFO:     Started server process
# INFO:     Waiting for application startup.
# INFO:     Application startup complete.
# INFO:     Uvicorn running on http://0.0.0.0:8000
```

Keep this window open. Open a **new PowerShell window** for the next step.

---

### Step 10: Start the Frontend

```powershell
cd ..\frontend

# Install Node.js dependencies
npm install

# Create frontend .env
'VITE_API_URL=http://localhost:8000' | Out-File -FilePath .env -Encoding utf8

# Start development server
npm run dev

# Expected output:
#   VITE v5.x.x  ready in xxx ms
#   ➜  Local:   http://localhost:5174/
```

---

### Step 11: Open the Application

1. Open your browser and go to: **http://localhost:5174**
2. Login with:
   - **Email**: `admin@clavra.com`
   - **Password**: `Admin@123`

---

## Part B — PyCharm Setup

### Step 1: Open the Project

1. Launch PyCharm
2. **File → Open** → select the `clavra/backend` folder
3. PyCharm will detect it as a Python project

---

### Step 2: Configure the Python Interpreter

1. Go to **File → Settings → Project → Python Interpreter**
2. Click the gear icon → **Add Interpreter → Add Local Interpreter**
3. Select **Existing environment**
4. Browse to: `clavra\backend\.venv\Scripts\python.exe`
5. Click **OK**

PyCharm will index the virtual environment and show all packages.

---

### Step 3: Configure Environment Variables in PyCharm

1. Go to **Run → Edit Configurations**
2. Click **+** → **Python**
3. Set:
   - **Name**: `Backend Server`
   - **Script path**: select `backend/` folder's Python module mode
   - **Module name**: `uvicorn`
   - **Parameters**: `app.main:app --reload --host 0.0.0.0 --port 8000`
   - **Working directory**: `D:\path\to\clavra\backend`
   - **Environment variables**: Click the folder icon and add all values from your `.env` file

---

### Step 4: Run Migrations from PyCharm Terminal

1. Open **Terminal** in PyCharm (bottom panel)
2. The terminal should already be in `backend/` with `.venv` activated
3. Run:

```bash
alembic upgrade head
python -m app.init_db
```

---

### Step 5: Run the Backend from PyCharm

1. Click the green **Run** button (▶) or press **Shift+F10**
2. The **Run** panel shows server output
3. Look for: `Uvicorn running on http://0.0.0.0:8000`

---

### Step 6: Run the Frontend from PyCharm Terminal

1. Open a **second Terminal tab** in PyCharm
2. Navigate to frontend:

```bash
cd ../frontend
npm install
npm run dev
```

---

### Step 7: Access the App

Open browser: **http://localhost:5174**

Use the built-in PyCharm browser or any external browser.

---

## Part C — Docker (Simplest Option)

If you have Docker Desktop installed:

```powershell
cd clavra

# Build and start everything (PostgreSQL + backend + frontend + Nginx)
docker-compose up --build

# First run takes ~5 minutes to build images
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
# API Docs: http://localhost:8000/docs
```

To stop:
```powershell
docker-compose down
```

To stop and remove all data:
```powershell
docker-compose down -v
```

---

## Troubleshooting

### Backend won't start — "cannot connect to PostgreSQL"
- Ensure PostgreSQL is running: `Get-Service postgresql*` in PowerShell
- Check `DATABASE_URL` in `.env` — password and port must match

### "Module not found" errors
- Ensure the virtual environment is activated (`.venv` in prompt)
- Run `pip install -r requirements.txt` again

### Ollama not responding
- Check Ollama is running: `Invoke-WebRequest http://localhost:11434 -UseBasicParsing`
- If port is busy, check: `netstat -an | findstr 11434`

### Frontend "Network Error" / API calls failing
- Confirm backend is running on port 8000
- Check `.env` in frontend has: `VITE_API_URL=http://localhost:8000`
- Check browser console for CORS errors

### "alembic: command not found"
- Virtual environment not activated — run `.\.venv\Scripts\Activate.ps1` first

### pgvector not found
```sql
-- Run in psql as superuser:
CREATE EXTENSION IF NOT EXISTS vector;
```

### PowerShell execution policy error
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## Quick Reference

| Service | URL | Command |
|---|---|---|
| Frontend | http://localhost:5174 | `npm run dev` (in frontend/) |
| Backend API | http://localhost:8000 | `uvicorn app.main:app --reload --port 8000` |
| API Docs (Swagger) | http://localhost:8000/docs | (auto) |
| Ollama | http://localhost:11434 | `ollama serve` |
| PostgreSQL | localhost:5432 | pgAdmin or psql |

| Credential | Value |
|---|---|
| Admin email | admin@clavra.com |
| Admin password | Admin@123 |
| DB name | clavra_db |
| DB user | postgres |
