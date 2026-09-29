# MTHANDIZI — Backend (Phase 11)

Node.js + Express + PostgreSQL. Receives completed applications synced from a
kiosk (once WorkManager/Phase 12 exists on the Android side), and gives
officers an admin API to review and verify them.

## Running it

**With Docker** (the real deployment path):
```
docker compose up -d
npm install
npm run migrate
npm start
```

**Without Docker** (what was actually used to build and test this phase — see
`BUILD_LOG.md` for why: no Docker in the authoring sandbox, so a real,
directly-installed PostgreSQL was used instead):
```
# Install PostgreSQL 16, then:
sudo -u postgres psql -c "CREATE USER mthandizi WITH PASSWORD 'devpassword';"
sudo -u postgres psql -c "CREATE DATABASE mthandizi OWNER mthandizi;"
cp .env.example .env
npm install
npm run migrate
npm start
```

Health check:
```
curl http://localhost:3000/health
```

## Testing

```
npm test
```

**32 tests, all against a real Postgres database and a real running server —
not mocked at any layer.** Three suites:

- `tests/api.test.js` (14) — direct HTTP requests against the API via supertest.
- `tests/dashboard.test.js` (9) — jsdom loads the actual `public/index.html`
  over real HTTP, executes its actual `<script>` tag, simulates real clicks,
  inspects the resulting DOM.
- `tests/kiosk.test.js` (9) — same jsdom approach applied to the kiosk demo
  (`public/kiosk/index.html`): real touch-based walkthrough, skip/back/edit
  navigation, and real submission checked against the real database
  afterward. Honestly limited: jsdom has no `getUserMedia`, so the live
  voice-recording path needs a real browser to test — see
  `kiosk.test.js`'s own header comment.

## Kiosk demo — the integration bridge (built 2026-09-21)

Served at `/kiosk/`, alongside the admin dashboard. **This is the piece that
actually connects the previously-separate proven components** — real
speech recognition and matching from `speech-service`, a real submission
into this backend, visible afterward on the real admin dashboard. Full
story, including the deliberate architectural choice to call the real
speech-service API rather than reimplement any of its logic, in
`BUILD_LOG.md`.

```
open http://localhost:3000/kiosk/
```

Requires `speech-service` running at `localhost:8090` for the voice steps
(CORS already configured there); the backend submission itself works
regardless. A visible on-screen banner states plainly what's simplified
(date-of-birth uses a date picker, not voice — no spoken-date parser exists
in this project) rather than presenting it as more complete than it is.

## Admin dashboard (Phase 13)

Served by the backend itself at `/admin/` — same-origin, so its `fetch()`
calls to `/api/*` need no CORS configuration. Framework-free HTML/CSS/JS, per
the build prompt's stated stack.

```
open http://localhost:3000/admin/
```

Real login, real stat cards (grouped by service and status, straight from a
`GROUP BY` query — no mocked numbers), a real filterable list, and real
verify/reject buttons that write to the database. The service filter dropdown
populates itself from whatever services actually have applications — a fifth
service (added purely as config, per `workflow-engine`'s Phase 3 design)
would show up here automatically with zero dashboard code changes.

### Two real bugs found while building the automated test for it

**Relative URL resolution.** The dashboard's JS originally called
`fetch('/api/...')` with a relative path — which works perfectly in every
real browser (resolved against `document.baseURI`), but Node's native
`fetch` (used by the jsdom-based test) has no browsing context and can't
resolve a relative URL at all. Fixed by having the page compute
`window.location.origin` explicitly — a genuine robustness improvement to
the shipped code, not just a workaround for the test environment.

**A wrong-password login incorrectly said "Session expired."** The page's
shared `api()` helper treated every `401` response as "your session
expired, log in again" — but a *login* attempt with a bad password is also a
401, for an entirely different reason, and was getting the wrong, confusing
message instead of the backend's actual "Invalid username or password."
Fixed by only triggering the session-expired flow when a token existed to
expire in the first place.

Both were caught by the automated test, not discovered by manually clicking
around — see `BUILD_LOG.md` for the full trail.

## What's here

```
backend/
  src/
    config.js              single env-loading point
    db.js                    shared connection pool
    migrate.js                simple migration runner (no external framework)
    migrations/001_init.sql    kiosks, admin_users, applications
    validators/schemas.js       zod request validation
    services/                    business logic - the only layer that touches the DB directly
    controllers/                   thin - validate, call service, shape response
    routes/                          routes -> controllers, per the build prompt's stated stack
    middleware/auth.js                JWT gate for admin-only endpoints
    app.js                              Express app (importable by tests without binding a port)
    server.js                            the only file that calls app.listen()
  public/index.html                       admin dashboard (Phase 13) - served at /admin/
  tests/
    api.test.js                            14 integration tests, real Postgres
    dashboard.test.js                       9 tests, real browser-equivalent via jsdom
  docker-compose.yml
  .env.example
```

## Two things the build prompt named explicitly, both implemented literally

**"Auto-provision foreign-key dependencies on every write path, not just
one."** `applicationsService.createApplication()` inserts the kiosk row
(`ON CONFLICT DO NOTHING`) inside the same function that creates the
application — every single time, not assumed to already exist via some
separate kiosk-registration step a real kiosk might never call. Verified with
an independent `SELECT * FROM kiosks` check after creating an application
through a kiosk ID that had never been seen before (see `BUILD_LOG.md`).

**"A forced duplicate sync creates no duplicate row"** (Phase 12's stated
gate). `idempotencyKey` has a database-level UNIQUE constraint, and
`createApplication()` checks for an existing row with that key before ever
attempting an insert. Tested twice: once via the automated test suite, once
via a live `curl` POST repeated with the identical idempotency key, with an
independent `SELECT COUNT(*)` confirming exactly one row exists afterward.

## Auth boundary — documented, not implicit

Per the build prompt's Section 11 ("Document explicitly which endpoints are
gated and which are not, and why"):

- `POST /api/applications` (a kiosk syncing a completed application) is **NOT**
  admin-gated. A kiosk authenticates by physical possession and network
  access to its own sidecar, not by carrying an admin JWT — there is no
  officer sitting at the kiosk to log in.
- Every other `/api/applications/*` route, and anything that reads or
  modifies existing records, requires a valid admin JWT via `Authorization:
  Bearer <token>`, obtained from `POST /api/auth/login`.

There is deliberately no self-service admin signup endpoint — an admin
account is created directly (see `create_admin.mjs` for the pattern used
during testing), matching a real deployment where officer accounts would be
provisioned by whoever runs the kiosk network, not created by anyone who
finds the API.

## Known gaps — honest, not hidden

- **No rate limiting** on `/api/auth/login` — a real deployment should add
  this before going anywhere near a public network (this service is intended
  to sit behind a private network anyway, same as `speech-service`, but
  defense in depth matters).
- **`npm audit` could not be run in the authoring sandbox** (a tooling quirk,
  not a security decision — the sandbox's npm rejected the audit command
  outright). Run it before any real deployment.
- **No pagination cursor**, just limit/offset — fine at kiosk-network scale,
  would need revisiting at a much larger scale.
- **JWT secret defaults to a placeholder** in `.env.example` — the code
  requires it be set but doesn't validate its strength. Change it before any
  real deployment.

## Phase 11 + 13 gate

- [x] Database up with one command (`docker compose up -d`, real config provided)
- [x] Every endpoint exercised with real curl requests — output in `BUILD_LOG.md`
- [x] Auth genuinely blocks unauthenticated access — tested with a bogus
      token AND a missing header, not just the happy path
- [x] Zod validation rejects malformed input with 400, not a raw 500 from a
      failed database constraint
- [x] Auto-provisioning kiosk FK dependency — implemented and independently verified
- [x] Idempotent sync — implemented, tested twice (automated + live curl),
      independently verified against a raw `SELECT COUNT(*)`
- [x] 14/14 API tests passing, against a real database, not mocked
- [x] Admin dashboard: real login, real stat cards, real filtered list, real
      verify/reject actions — no mocked numbers anywhere
- [x] Dashboard tested as a real browser would see it (jsdom, real DOM
      inspection), not just HTML-source string matching — 9/9 passing
- [x] Two real bugs found by that test and fixed, not just written and
      assumed correct
