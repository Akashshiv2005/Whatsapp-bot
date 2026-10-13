# iZone Technologies — WhatsApp Automation Bot

A production-ready, selection- and state-driven WhatsApp Business automation platform for **iZone Technologies**, built with **Python**, **FastAPI**, **PostgreSQL**, **SQLAlchemy 2.0**, **Alembic**, **Pydantic v2**, and **httpx**.

---

## 🚀 Key Features

- **Deterministic State Machine**: Clear, modular state transitions (`MAIN_MENU`, submenus, lead collection wizard, contact info, and support handoff).
- **Meta WhatsApp Cloud API**: High-performance async client supporting interactive lists, button replies, text, location pins, and templates.
- **Strict Webhook Idempotency**: Guards against Meta webhook retries using `whatsapp_message_id`.
- **Database-Driven Menus & Services**: Services, menu options, FAQs, message templates, and automation rules stored in PostgreSQL.
- **CRM & Lead Capture**: Conversational multi-step lead capture (Name, Business Type, Requirement, Budget, Email, Phone confirmation) saving directly into PostgreSQL with status lifecycle (`NEW`, `CONTACTED`, `QUALIFIED`, `IN_PROGRESS`, `CONVERTED`, `LOST`, `CLOSED`).
- **Universal Navigation**: Full support for `0`/`menu` (home), `back` (step back), `cancel` (reset), and numeric inputs (`1`, `2`, `3`...).
- **Secure Admin REST API**: Complete `/api/v1/` endpoints for services, leads, conversations, messages, FAQs, templates, and analytics protected by API key authentication.
- **Enterprise Ready**: Full logging, structured error masking, and 100% automated test coverage.

---

## 🏢 Company Profile (iZone Technologies)

- **Website**: [https://izonetech.in/](https://izonetech.in/)
- **Primary Location**: 3rd Floor, Aruvi Arcade Complex, 5th Cross Thillainagar, North Extension Road, Tiruchirappalli, Tamil Nadu – 620018
- **Phone**: +91-9940048776
- **Email**: info@izonetech.in
- **Working Hours**: Monday – Saturday, 10:00 AM – 6:30 PM

---

## 📁 Project Structure

```
d:/Chat BOT/
├── .env                      # Active environment configuration
├── .env.example              # Environment variables template
├── alembic.ini               # Alembic database migration config
├── requirements.txt          # Python dependencies
├── README.md                 # Project documentation
├── alembic/                  # Database migration scripts
│   ├── env.py
│   └── versions/
├── app/
│   ├── main.py               # FastAPI application entrypoint
│   ├── core/
│   │   ├── config.py         # Pydantic Settings
│   │   ├── database.py       # Async SQLAlchemy engine & session factory
│   │   ├── logging.py        # Structured logging configuration
│   │   └── security.py       # Admin API authentication
│   ├── models/               # SQLAlchemy ORM models
│   │   ├── user.py
│   │   ├── conversation.py
│   │   ├── message.py
│   │   ├── service.py
│   │   ├── menu_option.py
│   │   ├── lead.py
│   │   ├── faq.py
│   │   ├── template.py
│   │   └── automation_rule.py
│   ├── schemas/              # Pydantic models for validation & serialization
│   ├── services/             # Core business logic
│   │   ├── whatsapp.py       # Meta Cloud API HTTP client
│   │   ├── message_parser.py # Webhook payload extractor & normalizer
│   │   ├── message_handler.py# State machine processing engine
│   │   ├── workflow_engine.py# Menus, lists & card builders
│   │   ├── lead_service.py   # Lead persistence & status transitions
│   │   ├── faq_service.py    # Database-driven keyword matcher
│   │   └── ai_service.py     # Modular AI fallback interface
│   ├── api/
│   │   ├── deps.py           # Dependency injection
│   │   ├── webhook.py        # GET/POST /webhook
│   │   └── v1/               # Admin REST API endpoints
│   └── seed/
│       └── seed_data.py      # iZone database catalog seeder
└── tests/                    # Comprehensive automated test suite
```

---

## 🛠️ How to Run (Local Python + PostgreSQL)

### 1. Database Setup
Ensure PostgreSQL is running locally with database `Bot` and password `1234`.

```ini
# .env
DATABASE_URL=postgresql+psycopg://postgres:1234@localhost:5432/Bot
```

### 2. Run Database Migrations
```powershell
.\venv\Scripts\alembic.exe upgrade head
```

### 3. Seed Services, Menus & FAQs
```powershell
.\venv\Scripts\python.exe -m app.seed.seed_data
```

### 4. Start the Application Server
```powershell
.\venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🧪 Running Automated Tests

```powershell
.\venv\Scripts\pytest.exe -v tests/
```

---

## 🌐 API Endpoints

### WhatsApp Webhooks
- `GET /webhook` — Meta Webhook verification handshake
- `POST /webhook` — Incoming WhatsApp event receiver with idempotency check
- `GET /health` — Health check endpoint

### Admin REST API (`/api/v1/`)
All Admin endpoints require the header `X-Admin-API-Key: izone_admin_secret_api_key_2026`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/services` | List all services & categories |
| `POST` | `/api/v1/services` | Create a new service |
| `GET` | `/api/v1/leads` | List and search customer leads |
| `PATCH` | `/api/v1/leads/{id}` | Update lead status (`NEW`, `QUALIFIED`, `CONVERTED`, etc.) |
| `GET` | `/api/v1/conversations` | List active user conversations |
| `GET` | `/api/v1/conversations/{id}/messages` | View full conversation transcript |
| `GET` | `/api/v1/faqs` | List database-driven FAQs |
| `POST` | `/api/v1/faqs` | Create new FAQ |
| `GET` | `/api/v1/analytics/summary` | Real-time bot metrics & lead KPIs |

---

## 📱 Meta WhatsApp Cloud API Webhook Configuration

1. In the [Meta App Dashboard](https://developers.facebook.com/), navigate to **WhatsApp > Configuration**.
2. Set **Callback URL** to: `https://your-domain.com/webhook` (or your ngrok / local tunnel URL during development).
3. Set **Verify Token** to: `izone_meta_verify_token_secure_123` (from `.env`).
4. Subscribe to the `messages` webhook field.
5. Add your `META_ACCESS_TOKEN`, `META_PHONE_NUMBER_ID`, and `META_BUSINESS_ACCOUNT_ID` to `.env`.
