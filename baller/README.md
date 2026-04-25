# Baller 🏸⚽🏓

A production-ready mobile court booking platform for Hanoi, Vietnam.

---

## Overview

**Baller** lets users search and book sports courts (bóng đá, cầu lông, pickleball) across Hanoi districts in ≤ 3 taps, with real-time slot availability, VietQR payment generation, and zero double-bookings.

### Components

| Layer | Technology |
|---|---|
| Mobile App | Flutter (Dart) |
| Backend API | FastAPI (Python 3.11+) |
| Database | PostgreSQL 15+ (asyncpg) |
| Migrations | Alembic |
| Rate Limiting | slowapi + Redis |
| Scheduling | APScheduler |
| Payments | VietQR (QR code generation) |

---

## Architecture

```
baller/
├── backend/               # FastAPI application
│   ├── app/
│   │   ├── main.py        # Application entry-point, lifespan, middleware
│   │   ├── config.py      # Settings via pydantic-settings (env vars only)
│   │   ├── database.py    # asyncpg connection pool
│   │   ├── models.py      # SQLAlchemy ORM models (async)
│   │   ├── schemas.py     # Pydantic v2 request/response schemas
│   │   ├── routers/
│   │   │   ├── courts.py  # GET /api/v1/courts, GET /api/v1/courts/{id}/slots
│   │   │   ├── bookings.py# POST /api/v1/bookings
│   │   │   └── health.py  # GET /healthz
│   │   ├── services/
│   │   │   ├── booking_service.py  # Concurrency-safe booking logic
│   │   │   └── qr_service.py       # VietQR payload + PNG generation
│   │   └── tasks/
│   │       └── expiry.py  # APScheduler: release pending_payment after 10 min
│   ├── migrations/        # Alembic migration scripts
│   │   └── versions/
│   │       └── 0001_initial.py  # Tables + indexes
│   ├── seed/
│   │   ├── seed_db.py     # Entry-point: python -m backend.seed.seed_db
│   │   ├── crawler.py     # Facebook group crawler (falls back to JSON)
│   │   └── courts_data.json  # Fallback data: ≥15 courts per sport
│   ├── tests/
│   │   ├── test_config.py
│   │   ├── test_courts.py
│   │   ├── test_bookings.py
│   │   └── test_concurrency.py
│   └── requirements.txt
└── mobile/                # Flutter application
    ├── lib/
    │   ├── main.dart
    │   ├── screens/
    │   │   ├── search_screen.dart   # Tap 1: sport + district filter
    │   │   ├── court_screen.dart    # Tap 2: court detail + slot picker
    │   │   └── booking_screen.dart  # Tap 3: confirm + VietQR display
    │   ├── widgets/
    │   │   └── vietqr_display.dart
    │   └── services/
    │       └── api_service.dart
    ├── integration_test/
    │   ├── booking_flow_test.dart
    │   └── search_performance_test.dart
    └── pubspec.yaml
```

---

## Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Flutter 3.19+
- Docker & Docker Compose (optional, recommended)

---

## Quick Start

### 1. Clone and configure

```bash
git clone <repo-url>
cd baller
cp backend/.env.example backend/.env
# Edit backend/.env with your values
```

### 2. Environment Variables

All secrets are loaded from environment variables. **Never hardcode credentials.**

```dotenv
# backend/.env (never commit this file)

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/baller

# Redis (for rate limiting)
REDIS_URL=redis://localhost:6379/0

# VietQR payment settings
VIETQR_BANK_ID=970436
VIETQR_ACCOUNT_NO=1234567890
VIETQR_ACCOUNT_NAME=BALLER SPORTS

# App mode: development | production
APP_ENV=development

# CORS (comma-separated origins; '*' only allowed in development)
CORS_ORIGINS=http://localhost:3000,http://localhost:8080

# Booking expiry (minutes)
BOOKING_EXPIRY_MINUTES=10

# Rate limiting
RATE_LIMIT_BOOKINGS=10/minute
```

All required variables are validated at startup; the app fails fast with a `RuntimeError` listing every missing variable before uvicorn binds to any port.

### 3. Backend setup

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Seed court data (crawls Facebook group, falls back to courts_data.json)
python -m backend.seed.seed_db

# Start the API server
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Flutter app setup

```bash
cd mobile

flutter pub get
flutter run
```

For integration tests:

```bash
flutter test integration_test/booking_flow_test.dart
flutter test integration_test/search_performance_test.dart
```

---

## API Reference

### Health

```
GET /healthz
→ 200 { "status": "ok", "db": "ok" }
```

### Courts

```
GET /api/v1/courts?sport_type=bong_da&district=hoan_kiem&limit=20&offset=0
→ 200 {
    "items": [ Court ],
    "total": int,
    "limit": int,
    "offset": int
  }
```

**Court object:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Sân Bóng Đá Hoàn Kiếm",
  "address": "12 Đinh Tiên Hoàng, Hoàn Kiếm, Hà Nội",
  "district": "hoan_kiem",
  "sport_type": "bong_da",
  "price_per_hour_vnd": 200000,
  "opening_time": "06:00",
  "closing_time": "22:00",
  "phone": "0912345678"
}
```

### Slots

```
GET /api/v1/courts/{court_uuid}/slots?date=2024-06-15
→ 200 [
    { "start_time": "06:00", "end_time": "06:30", "available": true },
    { "start_time": "06:30", "end_time": "07:00", "available": false },
    ...
  ]
```

- Slots are in 30-minute granularity in **Asia/Ho_Chi_Minh (UTC+7)**.
- `available: false` means the slot overlaps an existing confirmed or pending_payment booking.

### Bookings

```
POST /api/v1/bookings
Content-Type: application/json

{
  "court_id": "550e8400-e29b-41d4-a716-446655440000",
  "booking_date": "2024-06-15",
  "start_time": "18:00",
  "end_time": "19:00",
  "booker_name": "Nguyen Van A",
  "booker_phone": "0912345678"
}

→ 201 {
    "booking_id": "...",
    "status": "pending_payment",
    "qr_code_payload": "...",
    "qr_code_png_base64": "...",
    "total_amount_vnd": 200000,
    "expires_at": "2024-06-15T18:10:00+07:00"
  }
```

**Error responses:**

| Status | Condition |
|---|---|
| 409 | Slot already booked (overlap or concurrent race) |
| 422 | Invalid request body (Pydantic validation) |
| 429 | Rate limit exceeded (>10 requests/min from same IP) |

---

## Concurrency & Double-Booking Prevention

The booking service uses `SELECT ... FOR UPDATE NOWAIT` under `READ COMMITTED` isolation:

1. Within a transaction, the service locks all overlapping booking rows.
2. If any overlap exists → **409 Conflict**.
3. If another transaction holds the lock → asyncpg raises `lock_not_available` → **409 Conflict**.
4. Only one concurrent request can proceed; all others receive 409.

Overlap logic (inclusive start, exclusive end):

```
existing.start_time < new.end_time AND existing.end_time > new.start_time
```

This means:
- Booking 18:00–19:00 exists → POST 18:30–19:30 → **409**
- Booking 18:00–19:00 exists → POST 19:00–20:00 → **201** ✅

---

## Pending Payment Expiry

Bookings with `status = 'pending_payment'` older than **10 minutes** are automatically released by an APScheduler background task running every 60 seconds. Released bookings return to `status = 'expired'` and their slots become available for new bookings.

A manual endpoint is also available for cron-based invocation:

```
POST /tasks/release-expired
```

---

## Rate Limiting

- **Limit:** 10 POST `/api/v1/bookings` per IP per 60 seconds.
- **Storage:** Redis (configured via `REDIS_URL` env var).
- **Response on limit:** HTTP 429 with `Retry-After` header.

---

## Database Schema

### `courts` table

| Column | Type | Notes |
|---|---|---|
| id | UUID (PK) | UUIDv4 |
| name | VARCHAR | Court name |
| address | TEXT | Full address |
| district | VARCHAR | Hanoi district slug |
| sport_type | VARCHAR | `bong_da` / `cau_long` / `pickleball` |
| price_per_hour_vnd | INTEGER | Price in VND |
| opening_time | TIME | e.g. 06:00 |
| closing_time | TIME | e.g. 22:00 |
| phone | VARCHAR | Contact number |
| created_at | TIMESTAMPTZ | Auto |

**Indexes:**
- B-tree composite index on `(sport_type, district)` — supports sub-1s search queries.

### `bookings` table

| Column | Type | Notes |
|---|---|---|
| id | UUID (PK) | UUIDv4 |
| court_id | UUID (FK → courts.id) | |
| booking_date | DATE | Vietnam date (UTC+7) |
| start_time | TIME | Slot start |
| end_time | TIME | Slot end |
| booker_name | VARCHAR | |
| booker_phone | VARCHAR | |
| status | VARCHAR | `pending_payment` / `confirmed` / `expired` |
| total_amount_vnd | INTEGER | |
| created_at | TIMESTAMPTZ | Auto |
| expires_at | TIMESTAMPTZ | pending_payment expiry |

**Indexes:**
- Unique index on `(court_id, booking_date, start_time)` — enforced at DB level.

---

## Seeding Court Data

```bash
python -m backend.seed.seed_db
```

The seeder:
1. Attempts to crawl the Facebook group `https://www.facebook.com/groups/603786827732066`.
2. On any crawler failure (network error, parse error, rate limit), **falls back deterministically** to `backend/seed/courts_data.json`.
3. Inserts ≥ 15 courts per sport type: `bong_da`, `cau_long`, `pickleball`.

Verify after seeding:

```sql
SELECT sport_type, COUNT(*) FROM courts GROUP BY sport_type;
```

Expected output:

```
 sport_type  | count
-------------+-------
 bong_da     |    15+
 cau_long    |    15+
 pickleball  |    15+
```

---

## Security

### Principles

- All secrets via environment variables (`.env` file, never committed).
- No `shell=True` in any subprocess call.
- All SQL queries parameterized — no string interpolation.
- `bandit -r backend/ -ll -i` exits **0** (zero HIGH or MEDIUM findings).
- `pip-audit -r backend/requirements.txt` shows **zero HIGH/CRITICAL CVEs**.
- CORS `allow_origins` never includes `*` in non-development mode.

### Secret scanning

```bash
# Must return zero matches
grep -rE "(postgres://[^$]|sk_[a-zA-Z0-9]+|BANK_ID=[0-9]+)" backend/**/*.py
```

### Bandit scan

```bash
pip install bandit
bandit -r backend/ -ll -i
```

### Dependency audit

```bash
pip install pip-audit
pip-audit -r backend/requirements.txt
```

---

## Running Tests

```bash
cd backend
pytest tests/ -v
```

Key test modules:

| File | What it tests |
|---|---|
| `tests/test_config.py` | Startup fails with RuntimeError listing missing env vars |
| `tests/test_courts.py` | Search endpoint, indexes, UUID-only IDs in response |
| `tests/test_bookings.py` | Booking creation, VN timezone handling, expiry release |
| `tests/test_concurrency.py` | 10 concurrent POSTs → exactly 1 × 201, 9 × 409 |

Flutter integration tests:

```bash
cd mobile
flutter test integration_test/booking_flow_test.dart      # ≤3 taps to QR
flutter test integration_test/search_performance_test.dart # <3000ms e2e
```

---

## Docker Compose (Recommended for Local Dev)

```bash
docker compose up -d          # Starts PostgreSQL + Redis
cd backend
alembic upgrade head
python -m backend.seed.seed_db
uvicorn backend.app.main:app --reload
```

`docker-compose.yml` example:

```yaml
version: "3.9"
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: baller
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  pgdata:
```

---

## Flutter Booking Flow (≤ 3 Taps)

```
Tap 1 → Search screen: select sport type + district → shows court list
Tap 2 → Court detail screen: select time slot → pre-filled booking form
Tap 3 → Confirm booking → displays VietQR code for payment
```

No unnecessary intermediate screens or forms between these three taps.

---

## Performance Targets

| Metric | Target | Measurement |
|---|---|---|
| Court search API (p95) | < 200ms | locust / pytest-benchmark, 100 requests |
| Booking creation API (p95) | < 200ms | locust / pytest-benchmark |
| End-to-end booking (UI) | < 3,000ms | `search_performance_test.dart` |
| Slot query | < 200ms | benchmark test |

---

## Timezone Handling

All date/time operations use **Asia/Ho_Chi_Minh (UTC+7)**:

- `booking_date` represents the **Vietnam calendar date**.
- Slot availability is computed in Vietnam local time.
- A booking is never rejected as "in the past" if the Vietnam date is today or future, even if the server's UTC clock shows the previous UTC date.

Example: Server UTC `2024-06-01 17:00:00Z` = Vietnam `2024-06-02 00:00:00+07:00` — a booking for `booking_date = 2024-06-02` is **valid**.

---

## Contributing

1. Never commit `.env` files or any file containing credentials.
2. Run `bandit` and `pip-audit` before opening a PR.
3. All new API fields must use UUID strings — no integer IDs in responses.
4. All date/time logic must reference `Asia/Ho_Chi_Minh` explicitly.
5. Add tests for any new booking logic, especially concurrency paths.

---

## License

MIT
