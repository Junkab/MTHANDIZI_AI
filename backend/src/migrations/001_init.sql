-- MTHANDIZI Backend — initial schema.
--
-- kiosks: a kiosk row must exist before an application can reference it.
-- Every write path that creates an application auto-provisions the kiosk row
-- first (see applicationsService.js) — this is a direct implementation of a
-- lesson named explicitly in the build prompt's quality bar: "Auto-provision
-- foreign-key dependencies on every write path, not just one."

CREATE TABLE IF NOT EXISTS kiosks (
    id         TEXT PRIMARY KEY,
    label      TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS admin_users (
    id            SERIAL PRIMARY KEY,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS applications (
    id                SERIAL PRIMARY KEY,
    service_id        TEXT NOT NULL,
    reference_number  TEXT UNIQUE NOT NULL,
    kiosk_id          TEXT NOT NULL REFERENCES kiosks(id),
    payload           JSONB NOT NULL,
    status            TEXT NOT NULL DEFAULT 'pending_verification'
                          CHECK (status IN ('pending_verification', 'verified', 'rejected')),
    -- idempotency_key lets a retried sync (Phase 12: WorkManager retry with
    -- backoff) never create a duplicate row, even if the same application is
    -- submitted twice due to a network retry.
    idempotency_key   TEXT UNIQUE NOT NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    synced_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    verified_at       TIMESTAMPTZ,
    verified_by       INTEGER REFERENCES admin_users(id)
);

CREATE INDEX IF NOT EXISTS idx_applications_service_id ON applications(service_id);
CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);
CREATE INDEX IF NOT EXISTS idx_applications_kiosk_id ON applications(kiosk_id);
