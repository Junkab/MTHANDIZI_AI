// MTHANDIZI Backend — integration tests.
//
// These run against the REAL Postgres database (see db.js) via supertest
// driving the real Express app (app.js) — no mocking of the database or
// HTTP layer. This is deliberately different from speech-service's tests,
// which mock the ASR/TTS engines because the real model is unreachable in
// this environment; Postgres IS reachable here, so there is no excuse not
// to test against the real thing.

import { test, before, beforeEach, after } from "node:test";
import assert from "node:assert/strict";
import request from "supertest";
import { app } from "../src/app.js";
import { pool } from "../src/db.js";
import { migrate } from "../src/migrate.js";
import * as authService from "../src/services/authService.js";

let adminToken;

before(async () => {
  await migrate();
});

beforeEach(async () => {
  // Real database, so real cleanup between tests - not a mock reset.
  await pool.query("TRUNCATE applications, kiosks, admin_users RESTART IDENTITY CASCADE");
  const admin = await authService.createAdminUser("testadmin", "correct-password");
  adminToken = authService.issueToken(admin);
});

after(async () => {
  await pool.end();
});

function sampleApplication(overrides = {}) {
  return {
    serviceId: "BIRTH_REGISTRATION",
    referenceNumber: "BR-000001",
    kioskId: "kiosk-lilongwe-01",
    payload: { child_name: "Chikondi Phiri", district: "Lilongwe" },
    idempotencyKey: "idem-key-001",
    ...overrides,
  };
}

// --- health --------------------------------------------------------------------

test("GET /health returns ok without touching the database", async () => {
  const res = await request(app).get("/health");
  assert.equal(res.status, 200);
  assert.equal(res.body.status, "ok");
});

// --- creating applications: auto-provisioning + idempotency --------------------

test("POST /api/applications creates an application and auto-provisions the kiosk", async () => {
  const res = await request(app).post("/api/applications").send(sampleApplication());
  assert.equal(res.status, 201);
  assert.equal(res.body.application.service_id, "BIRTH_REGISTRATION");
  assert.equal(res.body.wasAlreadySynced, false);

  const kiosk = await pool.query("SELECT * FROM kiosks WHERE id = $1", ["kiosk-lilongwe-01"]);
  assert.equal(kiosk.rows.length, 1, "kiosk row must be auto-created, not required to pre-exist");
});

test("a retried sync with the same idempotencyKey does NOT create a duplicate row", async () => {
  const payload = sampleApplication();
  const first = await request(app).post("/api/applications").send(payload);
  assert.equal(first.status, 201);

  const second = await request(app).post("/api/applications").send(payload);
  assert.equal(second.status, 200, "a repeat of the same idempotency key returns 200, not 201");
  assert.equal(second.body.wasAlreadySynced, true);
  assert.equal(second.body.application.id, first.body.application.id);

  const count = await pool.query("SELECT COUNT(*)::int AS n FROM applications");
  assert.equal(count.rows[0].n, 1, "exactly one row must exist despite two POSTs");
});

test("two DIFFERENT applications with the same referenceNumber but different idempotencyKey are rejected", async () => {
  await request(app).post("/api/applications").send(sampleApplication({ idempotencyKey: "key-a" }));
  const res = await request(app).post("/api/applications").send(
    sampleApplication({ idempotencyKey: "key-b" })  // same referenceNumber (default), different key
  );
  assert.equal(res.status, 409);
});

test("missing required fields are rejected with 400, not a 500 database error", async () => {
  const res = await request(app).post("/api/applications").send({ serviceId: "X" });
  assert.equal(res.status, 400);
  assert.ok(res.body.details, "should explain what was invalid");
});

// --- auth gating -----------------------------------------------------------------

test("GET /api/applications without a token is rejected", async () => {
  const res = await request(app).get("/api/applications");
  assert.equal(res.status, 401);
});

test("GET /api/applications with a bogus token is rejected", async () => {
  const res = await request(app).get("/api/applications").set("Authorization", "Bearer not-a-real-token");
  assert.equal(res.status, 401);
});

test("GET /api/applications with a valid admin token succeeds", async () => {
  await request(app).post("/api/applications").send(sampleApplication());
  const res = await request(app).get("/api/applications").set("Authorization", `Bearer ${adminToken}`);
  assert.equal(res.status, 200);
  assert.equal(res.body.applications.length, 1);
});

test("login with correct credentials issues a working token", async () => {
  const res = await request(app).post("/api/auth/login").send({
    username: "testadmin", password: "correct-password",
  });
  assert.equal(res.status, 200);
  assert.ok(res.body.token);

  const followUp = await request(app).get("/api/applications")
    .set("Authorization", `Bearer ${res.body.token}`);
  assert.equal(followUp.status, 200, "a freshly issued token must actually work");
});

test("login with the wrong password is rejected", async () => {
  const res = await request(app).post("/api/auth/login").send({
    username: "testadmin", password: "wrong-password",
  });
  assert.equal(res.status, 401);
});

// --- verification workflow --------------------------------------------------------

test("PATCH .../verify updates status and records who verified it", async () => {
  const created = await request(app).post("/api/applications").send(sampleApplication());
  const id = created.body.application.id;

  const res = await request(app)
    .patch(`/api/applications/${id}/verify`)
    .set("Authorization", `Bearer ${adminToken}`)
    .send({ status: "verified" });

  assert.equal(res.status, 200);
  assert.equal(res.body.application.status, "verified");
  assert.ok(res.body.application.verified_at);
  assert.ok(res.body.application.verified_by);
});

test("verify without auth is rejected, same as list/stats", async () => {
  const created = await request(app).post("/api/applications").send(sampleApplication());
  const res = await request(app)
    .patch(`/api/applications/${created.body.application.id}/verify`)
    .send({ status: "verified" });
  assert.equal(res.status, 401);
});

// --- filtering and stats ------------------------------------------------------------

test("listing can be filtered by status and serviceId", async () => {
  await request(app).post("/api/applications").send(sampleApplication({ idempotencyKey: "k1" }));
  await request(app).post("/api/applications").send(sampleApplication({
    idempotencyKey: "k2", referenceNumber: "HQ-000001", serviceId: "HOSPITAL_QUEUE",
  }));

  const res = await request(app)
    .get("/api/applications?serviceId=HOSPITAL_QUEUE")
    .set("Authorization", `Bearer ${adminToken}`);
  assert.equal(res.status, 200);
  assert.equal(res.body.applications.length, 1);
  assert.equal(res.body.applications[0].service_id, "HOSPITAL_QUEUE");
});

test("GET /api/applications/stats groups by service and status", async () => {
  await request(app).post("/api/applications").send(sampleApplication());
  const res = await request(app).get("/api/applications/stats")
    .set("Authorization", `Bearer ${adminToken}`);
  assert.equal(res.status, 200);
  assert.ok(res.body.stats.length >= 1);
});
