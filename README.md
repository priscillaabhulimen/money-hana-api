# MoneyHana — API

The FastAPI backend for MoneyHana, a personal finance tracking app. It handles authentication, transactions, spending goals, subscription management, AI-generated insights, and scheduled due date notifications.

**API docs:** https://your-api.onrender.com/docs  
**Frontend repo:** https://github.com/priscillaabhulimen/money-hana

---

## Tech Stack

| Technology | Why |
|---|---|
| FastAPI | Async Python, automatic OpenAPI docs, excellent Pydantic integration |
| PostgreSQL | Relational integrity for transactions, goals, and subscriptions |
| SQLAlchemy (async) | Type-safe async queries with Alembic migrations |
| JWT (access + refresh tokens) | Stateless auth with cookie-based refresh for seamless token rotation |
| Groq (LLaMA) | Fast inference for generating personalised spending insights |
| Resend | Transactional email for account verification |
| APScheduler | Background jobs for subscription due date checks |

---

## Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/auth/register` | Register a new user |
| POST | `/api/v1/auth/login` | Login and receive tokens |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| POST | `/api/v1/auth/logout` | Logout and clear tokens |
| GET | `/api/v1/transactions` | List transactions (paginated) |
| POST | `/api/v1/transactions` | Create a transaction |
| PATCH | `/api/v1/transactions/{id}` | Update a transaction |
| DELETE | `/api/v1/transactions/{id}` | Delete a transaction |
| GET | `/api/v1/goals` | List spending goals |
| POST | `/api/v1/goals` | Create a goal |
| PATCH | `/api/v1/goals/{id}` | Update a goal |
| DELETE | `/api/v1/goals/{id}` | Delete a goal |
| GET | `/api/v1/subscriptions` | List subscriptions |
| POST | `/api/v1/subscriptions` | Create a subscription |
| PATCH | `/api/v1/subscriptions/{id}` | Update a subscription |
| DELETE | `/api/v1/subscriptions/{id}` | Delete a subscription |
| GET | `/api/v1/notifications` | List pending payment confirmations |
| POST | `/api/v1/notifications/{id}/confirm` | Confirm payment and log transaction |
| POST | `/api/v1/notifications/{id}/dismiss` | Dismiss and advance due date |
| GET | `/api/v1/insights` | Get AI-generated insights |

Full interactive docs available at `/docs` when the server is running.

---

## Local Setup

### Prerequisites

- Python 3.12+
- Docker (for PostgreSQL)

### 1. Clone the repo

```bash
git clone https://github.com/priscillaabhulimen/money-hana-api.git
cd money-hana-api
```

### 2. Start PostgreSQL with Docker

```bash
docker run --name moneyhana-db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=moneyhana \
  -p 5432:5432 \
  -d postgres:16
```

### 3. Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure environment

```bash
cp .env.example .env
```

Fill in `.env`:

```env
APP_ENV=development
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/moneyhana
AUTH_SECRET_KEY=your-secret-key-here        # generate with: openssl rand -hex 32
AUTH_ALGORITHM=HS256
AUTH_ACCESS_TOKEN_EXPIRE_MINUTES=30
AUTH_REFRESH_TOKEN_EXPIRE_DAYS=14
EMAIL_PROVIDER=console                       # prints emails to terminal, no SMTP needed
EMAIL_FROM=no-reply@localhost
FRONTEND_VERIFY_URL=http://localhost:3000/verify-email
GROQ_API_KEY=your-groq-api-key
INSIGHT_TTL_DAYS=7
ALLOWED_ORIGINS=http://localhost:3000
```

### 6. Run migrations

```bash
alembic upgrade head
```

### 7. Start the server

```bash
uvicorn app.main:app --reload
```

API will be available at `http://localhost:8000`.  
Swagger docs at `http://localhost:8000/docs`.

---

## Deployment

The API is deployed on Render as a Python web service.

**Build command:**
```
pip install -r requirements.txt
```

**Start command:**
```
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Set all variables from `.env.example` in Render → Environment, plus `RESEND_TIER=free` if you're on Resend's free plan.

---

## What I Learned

Wiring async SQLAlchemy with Alembic migrations taught me a lot about how ORMs manage schema state across environments — a gap that showed up when deploying to a fresh database that had never run certain migrations. Implementing JWT token rotation with a refresh-on-401 pattern gave me a solid understanding of stateless auth, handling expired access tokens transparently without interrupting the user session. Deploying to Render also surfaced a subtle issue where the platform's `DATABASE_URL` format (`postgresql://`) differs from what SQLAlchemy's async engine expects (`postgresql+asyncpg://`), requiring URL normalization in the config layer.

---

## Planned Features

- **Receipt scanning** — OCR endpoint to parse and log transactions from receipt images
- **Premium tier** — gated endpoints for advanced AI insights, custom categories, and multi-currency support
- **Budget forecasting** — project end-of-month spend based on transaction history and upcoming subscriptions
