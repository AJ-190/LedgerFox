# LedgerFox

A backend payments and settlement engine, built to the same architectural standard as
systems like Stripe or Paystack.

> **Project status: early development.** Authentication and JWT issuance are working.
> Organisation, roles, and settlement logic are not yet implemented. See
> [Status](#status) for the honest breakdown.

---

## Stack

| Layer | Choice |
|---|---|
| Language | Python 3.14 |
| API framework | FastAPI 0.136 |
| Data validation | Pydantic 2.13 + pydantic-settings |
| ORM | SQLAlchemy 2.0.49 (async) |
| Database | PostgreSQL via `asyncpg` (Supabase) |
| Migrations | Alembic |
| Password hashing | Argon2 via passlib |
| Tokens | PyJWT (HS256) |
| Transactional email | External notifier over HTTP (`httpx`) |
| OTP store | Redis, keys carry a TTL |
| Server | Uvicorn |

---

## Architecture

The codebase keeps HTTP concerns, business logic, and persistence in separate layers, so
that every privileged operation is reachable through exactly one router. That is what
makes the permission model enforceable in a single place.

```
src/
├── main.py            App construction, router registration, lifespan (schema creation)
├── config.py          Typed settings loaded from the environment
├── db/
│   └── database.py    Declarative Base, async engine, session factory, get_db dependency
├── auth/
│   ├── router.py      /auth endpoints — the HTTP surface
│   ├── service.py     Registration, login, and OTP logic
│   ├── schemas.py     Request/response contracts, password strength validator
│   ├── otp.py         OTP generation, Redis storage, verification
│   ├── utils.py       Argon2 hashing, JWT generation
│   └── dependencies.py  Shared FastAPI dependencies (role guards go here)
├── notify/
│   └── utils.py       Hands the OTP to the external delivery service over HTTP
├── users/
│   ├── model.py       ORM definition of the users table
│   └── router.py      User endpoints
└── organization/
    ├── router.py      Organisation endpoints
    └── service.py     Organisation business logic
```

---

## Getting started

### 1. Clone and set up the environment

```bash
git clone git@github.com:AJ-190/LedgerFox.git
cd LedgerFox

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure the environment

Create `src/.env`. This file is git-ignored and must never be committed.

```ini
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:5432/postgres
SECRET_KEY=generate-a-long-random-string
```

| Variable | Required | Default | Notes |
|---|---|---|---|
| `DATABASE_URL` | yes | — | **Dialect first, driver second.** See below. |
| `SECRET_KEY` | yes | — | Signs JWTs. Use `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `ALGORITHM` | no | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_TIME_MINUTES` | no | `60` | Access token lifetime, in minutes |
| `REFRESH_TOKEN_TIME_MINUTES` | no | `10080` | Refresh token lifetime (7 days), in minutes |
| `NOTIFIER_URL` | yes | — | The external service endpoint that renders and sends the code. |
| `NOTIFIER_API_KEY` | yes | — | Sent as `Authorization: Bearer <key>`. |
| `NOTIFIER_FROM` | yes | — | Sender address passed through to the notifier. |
| `NOTIFIER_FROM_NAME` | no | `LedgerFox` | Display name for the sender. |
| `NOTIFIER_TIMEOUT` | no | `10` | Seconds before the notifier call is abandoned. |
| `OTP_LENGTH` | no | `6` | Digits in the code. |
| `OTP_EXPIRY_SECONDS` | no | `300` | How long a code stays valid. |
| `OTP_MAX_ATTEMPTS` | no | `5` | Wrong guesses before the code is destroyed. |
| `OTP_RESEND_COOLDOWN` | no | `60` | Minimum seconds between codes for one address. |

**The notifier contract.** LedgerFox owns the code; the external service owns delivery.
`src/notify/utils.py` POSTs JSON to `NOTIFIER_URL` and is responsible for nothing else —
no templates, no SMTP, no HTML. The body is:

```json
{
  "to": "you@example.com",
  "name": "Ada Lovelace",
  "code": "481902",
  "subject": "LedgerFox verification code",
  "from": "no-reply@ledgerfox.com",
  "from_name": "LedgerFox",
  "expires_in_seconds": 300
}
```

The `code` arrives in plaintext, because the recipient has to read it. Any non-2xx
response raises, and `send_otp` returns `503` — the code is deleted from Redis so a
message that never went out cannot be guessed later. If your provider expects a different
body shape or a different auth scheme, that is the one function to edit.

**Getting `DATABASE_URL` right.** SQLAlchemy reads the scheme as `<dialect>+<driver>`, in
that order. `postgresql` is the dialect; `asyncpg` is the driver. Reversing them produces
`Can't load plugin: sqlalchemy.dialects:asyncpg.postgresql`. The same ordering applies
elsewhere: `mysql+pymysql://`, `sqlite+aiosqlite://`.

If your database password contains `@`, `:`, or `/`, it must be URL-encoded.

### 3. Run

```bash
uvicorn src.main:app --reload
```

The lifespan handler creates any missing tables on startup, so the first run against an
empty database is enough to get going. Interactive API docs are then at
<http://127.0.0.1:8000/docs>.

---

## API

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/` | no | Health check |
| `POST` | `/auth/register_account` | no | Create an account. Enforces password strength. |
| `POST` | `/auth/login` | no | Exchange credentials for a token pair. `username` accepts email **or** phone. |
| `POST` | `/auth/send_otp` | no | Email a verification code. `202` either way. |
| `POST` | `/auth/verify_otp` | no | Exchange the code for `is_verified: true`. |

Both auth endpoints take and return JSON. Login additionally accepts
`OAuth2PasswordRequestForm`, so the **Authorize** button in `/docs` works.

### Example

```bash
curl -X POST http://127.0.0.1:8000/auth/login \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=you@example.com&password=YourPassw0rd!'
```

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

Field names follow the OAuth 2.0 convention (`access_token`, `refresh_token`,
`token_type`) so standard clients interoperate without translation.

### Password requirements

At least 8 characters, containing at least one digit, one lowercase letter, one uppercase
letter, and one special character. Enforced by a validator in `src/auth/schemas.py`, so it
holds for every entry point rather than only the HTTP layer.

### Email verification

`POST /auth/send_otp` mails a six-digit code, and `POST /auth/verify_otp` exchanges it for
`is_verified: true` on the user row.

```bash
curl -X POST http://127.0.0.1:8000/auth/send_otp \
  -H 'Content-Type: application/json' \
  -d '{"email": "you@example.com"}'

curl -X POST http://127.0.0.1:8000/auth/verify_otp \
  -H 'Content-Type: application/json' \
  -d '{"email": "you@example.com", "code": "481902"}'
```

The code is held in Redis, never in Postgres. Redis holds three keys per address:

| Key | Value | TTL |
|---|---|---|
| `otp:code:<email>` | `HMAC-SHA256(SECRET_KEY, email:code)` | `OTP_EXPIRY_SECONDS` |
| `otp:attempts:<email>` | Wrong-guess counter | `OTP_EXPIRY_SECONDS` |
| `otp:cooldown:<email>` | Resend throttle | `OTP_RESEND_COOLDOWN` |

Nothing needs purging: every key expires on its own, so a restart costs nothing and a stale
code cannot outlive its window. The address is lowercased before it becomes a key, so
`You@Example.com` and `you@example.com` cannot each hold a live code.

---

## Roles and permissions

LedgerFox uses coarse roles, with fine-grained capability expressed through policy rather
than through an expanding set of role names.

| Role | Scope | Summary |
|---|---|---|
| `owner` | Organisation | Billing, ownership transfer, can delete the org. One per org. |
| `admin` | Organisation | Members, roles, API keys, settings. No billing. |
| `operator` | Organisation | Day-to-day money operations: create payments, initiate payouts. |
| `approver` | Organisation | Approves payouts above threshold. Cannot initiate. |
| `viewer` | Organisation | Read-only, plus exports. For finance and audit staff. |
| `platform_admin` | Platform | Internal staff. Held outside the org role set, separately audited. |

Three rules govern the model, and they are constraints rather than preferences:

1. **Role belongs to a membership, not to a user.** One person may be an `operator` in one
   organisation and an `owner` in another. Role therefore lives on an `org_members` row,
   not as a column on `users`.
2. **Authority over money is a separate axis from role.** Amount caps, approval
   thresholds, and 2FA requirements do not belong in an enum. The model is a coarse role
   plus a policy record that constrains it.
3. **No role may both initiate and approve a payout.** This is the primary internal control
   in a settlement engine and an explicit audit requirement. It is why `operator` and
   `approver` are separate roles, and why the capability guard alone is not sufficient —
   the initiator check belongs in the service layer, where the payout record is loaded.

Authorisation is applied as a FastAPI dependency so that no handler can forget to call it,
and it **denies by default**: a new endpoint is unreachable until a capability is
explicitly granted.

---

## Security notes

- Passwords are hashed with Argon2 and never stored or returned in plaintext.
- `SECRET_KEY` lives in a git-ignored `.env`. Verify with `git check-ignore src/.env`
  before your first commit.
- Access and refresh tokens are distinct, carry independent lifetimes, and a unique `jti`
  per token so individual tokens can be revoked.
- Login returns `403` for an unknown account and `401` for a wrong password, so the
  response does not reveal whether an account exists.
- `password` is modelled as `SecretStr` in schemas, so it is excluded from logs and
  `repr` and must be explicitly unwrapped with `.get_secret_value()` to be read.
- `NOTIFIER_API_KEY` is a `SecretStr` for the same reason, and is sent in the
  `Authorization` header only — never in the request body.
- **The OTP is not stored in plaintext.** Redis holds an HMAC keyed with `SECRET_KEY`, so a
  dump of the keyspace does not yield usable codes. Comparison is `hmac.compare_digest`,
  which is constant-time, and the guess counter caps online brute force at
  `OTP_MAX_ATTEMPTS` per code.
- **`send_otp` does not confirm whether an account exists.** An unknown address gets the
  same `202` and the same body as a known one, and the cooldown is set either way, so the
  endpoint is not an account-enumeration oracle. `verify_otp` is allowed to be blunt, since
  by then the caller already holds a secret.
- Codes are single-use. A successful verify deletes the code and the counter, so a captured
  request cannot be replayed.

---

## Status

| Area | State |
|---|---|
| Config loading | Done |
| Async DB engine, sessions, migrations | Done |
| Registration | Done |
| Login, JWT issuance | Done |
| Password hashing | Done, but synchronous — blocks the event loop |
| OTP delivery via external notifier | Done |
| OTP request, verify, `is_verified` | Done |
| Organisation & `org_members` | Stub |
| Role / capability guards | Stub |
| Payments, payouts, settlement | Not started |
| Test suite | Not started |

`src/organization/` is an empty placeholder awaiting implementation. `dependencies.py` now
holds the Redis dependency; the role guards are still to come.

### Known issues

- **Argon2 blocks the event loop.** `utils.hash` is CPU-bound and called directly from an
  `async def` service function. Harmless at low volume, materially harmful under load.
  Wrap it in `anyio.to_thread.run_sync` or Starlette's `run_in_threadpool`.
- **Response field / column mismatch.** `RegisterAccountResponse.is_verify` does not match
  the ORM column `is_verified`. Because the field carries a default this fails silently and
  always reports `false`, including for verified users. `register_account` therefore still
  reports `is_verify: false` after a successful `verify_otp`.
- **The notifier call is awaited inline.** `send_otp` blocks on the external service
  inside the request, so a slow or hanging notifier holds the connection open for up to
  `NOTIFIER_TIMEOUT`. Moving it to Celery, already pinned, would decouple the two.
- **The per-IP limiter is a single shared counter.** `auth_rate_limiter` keys on IP alone, so
  one abusive client throttles every user behind the same NAT. Keying it on IP *and*
  submitted address would fix it.
- **A send failure is a `503`, which confirms the address exists.** Everywhere else this
  endpoint is deliberately indistinguishable for known and unknown addresses. This is the
  one place the rule is broken, chosen so that a misconfigured notifier is visible rather
  than silently swallowing every code. Worth revisiting if enumeration matters more.
- **No transactional record of codes.** Redis holds the live code and then forgets it. An
  audit requirement — "prove this address was verified, and when" — wants a Postgres
  `otp_codes` table written alongside.
- **`requirements.txt` is a full `pip freeze`.** It pins transitive and unrelated packages
  (pandas, celery, reportlab, redis). It should be reduced to direct dependencies.
- **`.env.example` is git-ignored** by the current `.gitignore`, so contributors have no
  template. That entry should be removed.

---

## Roadmap

1. Close the known issues above.
2. Add `organisations` and `org_members` tables with a role check constraint.
3. Move hashing off the event loop.
4. Implement the capability guard and verify the permission matrix by exercising each
   capability as each role.
5. Add the payout conflict check to the service layer.
6. Build payments, then introduce the policy axis for limits and thresholds.

---

## Author

**Addy Samuel**  
Backend Engineer — The Unfathomable Builder 🫥  
[GitHub](https://github.com/AJ-190) · [LinkedIn](https://www.linkedin.com/in/addy-samuel-010302378/)

---

## License

Private. All rights reserved.
