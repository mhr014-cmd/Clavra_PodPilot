# PYCHARM RUN GUIDE

## Backend

cd backend

python -m venv .venv

Windows:
.venv\Scripts\activate

pip install -r requirements.txt

Create .env from .env.example

Run backend:

uvicorn app.main:app --reload

Backend:
http://localhost:8000

## Frontend

cd frontend

npm install

npm run dev

Frontend:
http://localhost:5173
