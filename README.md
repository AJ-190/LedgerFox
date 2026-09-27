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
│   ├── service.py     Registration and login logic
│   ├── schemas.py     Request/response contracts, password strength validator
│   ├── utils.py       Argon2 hashing, JWT generation
│   └── dependencies.py  Shared FastAPI dependencies (role guards go here)
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

---

## Status

| Area | State |
|---|---|
| Config loading | Done |
| Async DB engine, sessions, migrations | Done |
| Registration | Done |
| Login, JWT issuance | Done |
| Password hashing | Done, but synchronous — blocks the event loop |
| Organisation & `org_members` | Stub |
| Role / capability guards | Stub |
| Payments, payouts, settlement | Not started |
| Test suite | Not started |

`src/organization/`, `src/auth/dependencies.py` are empty placeholders awaiting
implementation.

### Known issues

- **Argon2 blocks the event loop.** `utils.hash` is CPU-bound and called directly from an
  `async def` service function. Harmless at low volume, materially harmful under load.
  Wrap it in `anyio.to_thread.run_sync` or Starlette's `run_in_threadpool`.
- **Response field / column mismatch.** `RegisterAccountResponse.is_verify` does not match
  the ORM column `is_verified`. Because the field carries a default this fails silently and
  always reports `false`, including for verified users.
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
[GitHub](https://github.com/AJ-190) · [LinkedIn](https://linkedin.com/in/your-profile)

---

## License

Private. All rights reserved.
