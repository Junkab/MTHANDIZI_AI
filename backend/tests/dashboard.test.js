// MTHANDIZI Backend — admin dashboard test.
//
// This does NOT just check the HTML source contains certain strings. It
// uses jsdom to load the REAL page over REAL HTTP from a REAL running
// server, execute its ACTUAL <script> tag, simulate a real login form
// submission, and then inspect the resulting DOM - the same thing a human
// clicking around in a browser would see. Real Postgres underneath, same as
// api.test.js.

import { test, before, beforeEach, after } from "node:test";
import assert from "node:assert/strict";
import { JSDOM } from "jsdom";
import { app } from "../src/app.js";
import { pool } from "../src/db.js";
import { migrate } from "../src/migrate.js";
import * as authService from "../src/services/authService.js";
import * as applicationsService from "../src/services/applicationsService.js";

const TEST_PORT = 3901;
let server;

before(async () => {
  await migrate();
  server = app.listen(TEST_PORT);
});

beforeEach(async () => {
  await pool.query("TRUNCATE applications, kiosks, admin_users RESTART IDENTITY CASCADE");
  await authService.createAdminUser("dashtest", "dashpassword123");
});

after(async () => {
  server.close();
  await pool.end();
});

async function loadDashboard() {
  const dom = await JSDOM.fromURL(`http://localhost:${TEST_PORT}/admin/`, {
    runScripts: "dangerously",
    resources: "usable",
    pretendToBeVisual: true,
  });
  dom.window.fetch = fetch;  // jsdom has no built-in fetch - use Node's real one
  // sessionStorage in jsdom is per-origin and real (not mocked) - fine as-is.
  return dom;
}

function byId(dom, id) {
  return dom.window.document.getElementById(id);
}

async function login(dom, username, password) {
  byId(dom, "username").value = username;
  byId(dom, "password").value = password;
  byId(dom, "loginForm").dispatchEvent(new dom.window.Event("submit", { cancelable: true }));
  await flush();
}

/** Real async work (the page's own fetch calls) needs real event-loop turns
 *  to resolve - this isn't a fake timer, it's giving the actual HTTP
 *  request/response cycle a moment to complete. */
async function flush(ms = 300) {
  await new Promise((resolve) => setTimeout(resolve, ms));
}

// --- the page itself loads and is structured as expected -----------------------

test("GET /admin/ serves the real dashboard HTML", async () => {
  const res = await fetch(`http://localhost:${TEST_PORT}/admin/`);
  assert.equal(res.status, 200);
  const html = await res.text();
  assert.match(html, /MTHANDIZI Admin/);
});

test("the login form is visible and the dashboard is hidden before logging in", async () => {
  const dom = await loadDashboard();
  assert.equal(byId(dom, "loginForm").classList.contains("hidden"), false);
  assert.equal(byId(dom, "dashboard").classList.contains("hidden"), true);
});

// --- real login, through the real form, against the real backend ---------------

test("submitting the login form with correct credentials reveals the real dashboard", async () => {
  const dom = await loadDashboard();
  await login(dom, "dashtest", "dashpassword123");

  assert.equal(byId(dom, "dashboard").classList.contains("hidden"), false,
    "dashboard should be visible after a successful login");
  assert.equal(byId(dom, "loginForm").classList.contains("hidden"), true);
});

test("submitting the login form with the WRONG password shows a real error, not a crash", async () => {
  const dom = await loadDashboard();
  await login(dom, "dashtest", "wrong-password");

  assert.equal(byId(dom, "dashboard").classList.contains("hidden"), true,
    "dashboard must stay hidden on failed login");
  assert.match(byId(dom, "loginError").textContent, /invalid/i);
});

// --- the dashboard shows REAL data from the REAL database, not mocked ----------

test("stat cards reflect real application counts from the database", async () => {
  await applicationsService.createApplication({
    serviceId: "BIRTH_REGISTRATION", referenceNumber: "BR-DASH-001",
    kioskId: "kiosk-test", payload: { child_name: "Test Child" },
    idempotencyKey: "dash-key-1",
  });
  await applicationsService.createApplication({
    serviceId: "BIRTH_REGISTRATION", referenceNumber: "BR-DASH-002",
    kioskId: "kiosk-test", payload: { child_name: "Test Child 2" },
    idempotencyKey: "dash-key-2",
  });

  const dom = await loadDashboard();
  await login(dom, "dashtest", "dashpassword123");
  await flush();

  const statGrid = byId(dom, "statGrid").innerHTML;
  assert.match(statGrid, /BIRTH_REGISTRATION/);
  assert.match(statGrid, />2</, "the real count (2) must appear in the rendered stat card");
});

test("the empty state shows when there are genuinely no applications, not a fake row", async () => {
  const dom = await loadDashboard();
  await login(dom, "dashtest", "dashpassword123");
  await flush();

  assert.match(byId(dom, "statGrid").innerHTML, /No applications yet/);
});

test("the applications table lists a real created application with the correct reference number", async () => {
  await applicationsService.createApplication({
    serviceId: "HOSPITAL_QUEUE", referenceNumber: "HQ-DASH-999",
    kioskId: "kiosk-test", payload: { patient_name: "Grace Banda" },
    idempotencyKey: "dash-key-hq",
  });

  const dom = await loadDashboard();
  await login(dom, "dashtest", "dashpassword123");
  await flush();

  const tableHtml = byId(dom, "tableWrap").innerHTML;
  assert.match(tableHtml, /HQ-DASH-999/);
  assert.match(tableHtml, /pending verification/);
});

// --- verify/reject actions actually change the real database -------------------

test("clicking Verify on a real row actually updates the database, not just the DOM", async () => {
  const { application } = await applicationsService.createApplication({
    serviceId: "NATIONAL_ID", referenceNumber: "ID-DASH-001",
    kioskId: "kiosk-test", payload: { name: "Test Person" },
    idempotencyKey: "dash-key-verify",
  });

  const dom = await loadDashboard();
  await login(dom, "dashtest", "dashpassword123");
  await flush();

  const verifyBtn = dom.window.document.querySelector(`[data-verify="${application.id}"]`);
  assert.ok(verifyBtn, "a Verify button must exist for a pending application");
  verifyBtn.dispatchEvent(new dom.window.Event("click", { bubbles: true }));
  await flush();

  // Check the REAL database, not the DOM - the DOM could lie, Postgres can't.
  const dbRow = await pool.query("SELECT status FROM applications WHERE id = $1", [application.id]);
  assert.equal(dbRow.rows[0].status, "verified");

  // And the DOM should have refreshed to reflect it too.
  const tableHtml = byId(dom, "tableWrap").innerHTML;
  assert.match(tableHtml, /class="pill verified"/);
});

test("the service filter dropdown is populated from real data, not a hardcoded list", async () => {
  await applicationsService.createApplication({
    serviceId: "IMMIGRATION", referenceNumber: "IM-DASH-001",
    kioskId: "kiosk-test", payload: {}, idempotencyKey: "dash-key-imm",
  });

  const dom = await loadDashboard();
  await login(dom, "dashtest", "dashpassword123");
  await flush();

  const options = [...dom.window.document.getElementById("serviceFilter").options]
    .map((o) => o.value);
  assert.ok(options.includes("IMMIGRATION"),
    "a service that actually has applications must appear as a filter option");
});
