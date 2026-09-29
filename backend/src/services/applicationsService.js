// MTHANDIZI Backend — applications service (business logic layer).
// routes -> controllers -> services -> db, per the build prompt's stated
// stack. Controllers never touch `pool`/`query` directly.

import { pool, withTransaction } from "../db.js";

/**
 * Create (or, if already synced once, return unchanged) a completed
 * application.
 *
 * TWO THINGS THIS FUNCTION EXISTS TO GUARANTEE, BOTH NAMED DIRECTLY IN THE
 * BUILD PROMPT'S OWN QUALITY BAR:
 *
 * 1. "Auto-provision foreign-key dependencies on every write path, not just
 *    one." The kiosk row is created here, inside the same function, every
 *    time - not assumed to already exist, not provisioned only by some
 *    separate kiosk-registration endpoint that a real kiosk might never
 *    call. `ON CONFLICT DO NOTHING` makes this safe to run unconditionally.
 *
 * 2. Idempotent sync (Phase 12: "a forced duplicate sync creates no
 *    duplicate row"). `idempotencyKey` has a UNIQUE constraint at the
 *    database level (see migrations/001_init.sql), and this function
 *    checks for an existing row with that key FIRST and returns it
 *    unchanged rather than attempting a second insert. A retried sync from
 *    a flaky kiosk connection is expected and must be harmless.
 */
export async function createApplication({
  serviceId, referenceNumber, kioskId, payload, idempotencyKey,
}) {
  return withTransaction(async (client) => {
    const existing = await client.query(
      "SELECT * FROM applications WHERE idempotency_key = $1",
      [idempotencyKey]
    );
    if (existing.rows.length > 0) {
      return { application: existing.rows[0], wasAlreadySynced: true };
    }

    // Auto-provision the kiosk row before it's ever referenced.
    await client.query(
      "INSERT INTO kiosks (id) VALUES ($1) ON CONFLICT (id) DO NOTHING",
      [kioskId]
    );

    const result = await client.query(
      `INSERT INTO applications
         (service_id, reference_number, kiosk_id, payload, idempotency_key)
       VALUES ($1, $2, $3, $4, $5)
       RETURNING *`,
      [serviceId, referenceNumber, kioskId, payload, idempotencyKey]
    );
    return { application: result.rows[0], wasAlreadySynced: false };
  });
}

export async function listApplications({ status, serviceId, limit, offset }) {
  const conditions = [];
  const params = [];

  if (status) {
    params.push(status);
    conditions.push(`status = $${params.length}`);
  }
  if (serviceId) {
    params.push(serviceId);
    conditions.push(`service_id = $${params.length}`);
  }

  const where = conditions.length ? `WHERE ${conditions.join(" AND ")}` : "";
  params.push(limit);
  const limitParam = `$${params.length}`;
  params.push(offset);
  const offsetParam = `$${params.length}`;

  const result = await pool.query(
    `SELECT * FROM applications ${where}
     ORDER BY created_at DESC
     LIMIT ${limitParam} OFFSET ${offsetParam}`,
    params
  );
  return result.rows;
}

export async function getApplicationById(id) {
  const result = await pool.query("SELECT * FROM applications WHERE id = $1", [id]);
  return result.rows[0] ?? null;
}

export async function verifyApplication(id, status, verifiedByAdminId) {
  const result = await pool.query(
    `UPDATE applications
     SET status = $1, verified_at = now(), verified_by = $2
     WHERE id = $3
     RETURNING *`,
    [status, verifiedByAdminId, id]
  );
  return result.rows[0] ?? null;
}

export async function statsSummary() {
  const result = await pool.query(`
    SELECT
      status,
      service_id,
      COUNT(*)::int AS count
    FROM applications
    GROUP BY status, service_id
    ORDER BY service_id, status
  `);
  return result.rows;
}
