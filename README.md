# Investment Platform

Full-stack investment platform starter: **Next.js** + **FastAPI** + **PostgreSQL**, JWT auth, wallet ledger, buy/sell orders, portfolio P&L, admin APIs, Docker Compose.

> Demo/starter software. It does NOT connect to a broker, bank, UPI or any real-money payment gateway – deposits/withdrawals are ledger entries only. Do not use with real money without regulatory compliance (KYC, SEBI/RBI rules, payment gateway, audits).

## Run

```bash
cp .env.example .env        # then set a strong JWT_SECRET
docker compose up --build
```
- Frontend: http://localhost:3000
- API docs (Swagger): http://localhost:8000/docs
- Demo admin: `admin@example.com` / `Admin@12345` (change via `ADMIN_EMAIL` / `ADMIN_PASSWORD`)

Tables and demo products are created automatically on backend startup.

## Run backend tests (no Docker needed)
```bash
cd backend
pip install -r requirements-dev.txt
pytest -q
```

## Run backend without Docker
```bash
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload     # uses SQLite (investment.db) if DATABASE_URL is not set
```

## API overview
| Area | Endpoints |
|---|---|
| Auth | `POST /auth/register`, `POST /auth/login`, `POST /auth/change-password`, `GET/PATCH /me` |
| Products | `GET /products?category=&risk=&q=`, `GET /products/{id}`, `GET /products/{id}/history` |
| Wallet | `GET /wallet`, `POST /wallet/deposit`, `POST /wallet/withdraw`, `GET /transactions?type=&limit=&offset=` |
| Orders | `POST /orders`, `GET /orders?side=&product_id=`, `GET /orders/{id}` |
| Portfolio | `GET /portfolio` (value, invested, unrealised P&L per holding + totals) |
| Admin | `GET/POST /admin/products`, `PATCH /admin/products/{id}` (price/active/…), `GET /admin/users`, `PATCH /admin/users/{id}`, `GET /admin/orders`, `GET /admin/transactions`, `GET /admin/stats` |

## Backend design notes
- Money uses `Decimal` / `NUMERIC` (never float); wallet balance & holdings can't go negative (DB check constraints).
- Wallet/holding rows are locked (`SELECT … FOR UPDATE`) during deposits, withdrawals and orders to prevent double-spend races.
- Every money movement writes a ledger row with `balance_after`; orders store realised P&L on sells.
- Admin price changes are recorded in `price_history`. Inactive products can't be bought but can still be sold.
- Login has a basic in-memory brute-force throttle (10 fails / 15 min per email+IP) – use Redis/proxy rate limiting for multi-instance setups.
