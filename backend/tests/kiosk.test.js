// MTHANDIZI Backend — kiosk demo test.
//
// Same approach as dashboard.test.js: jsdom loads the REAL page over REAL
// HTTP, runs its ACTUAL script, and checks the resulting DOM and the REAL
// database afterward. HONEST LIMITATION, stated directly rather than
// glossed over: jsdom does not implement getUserMedia/MediaRecorder, so the
// live voice→ASR path cannot be exercised here - only a real browser with a
// real microphone and a real running speech-service can do that (see
// BUILD_LOG.md and DEMO_SCRIPT.md). What CAN be tested here, and is: the
// touch/date fallback path end to end, skip/back navigation, and - the part
// that matters most for proving real integration - actual submission to the
// actual backend, verified against the actual database.

import { test, before, beforeEach, after } from "node:test";
import assert from "node:assert/strict";
import { JSDOM } from "jsdom";
import { app } from "../src/app.js";
import { pool } from "../src/db.js";
import { migrate } from "../src/migrate.js";

const TEST_PORT = 3902;
let server;

before(async () => {
  await migrate();
  server = app.listen(TEST_PORT);
});

beforeEach(async () => {
  await pool.query("TRUNCATE applications, kiosks, admin_users RESTART IDENTITY CASCADE");
});

after(async () => {
  server.close();
  await pool.end();
});

async function loadKiosk() {
  const dom = await JSDOM.fromURL(`http://localhost:${TEST_PORT}/kiosk/`, {
    runScripts: "dangerously",
    resources: "usable",
    pretendToBeVisual: true,
  });
  dom.window.fetch = fetch;
  return dom;
}

function byId(dom, id) {
  return dom.window.document.getElementById(id);
}

async function flush(ms = 200) {
  await new Promise((resolve) => setTimeout(resolve, ms));
}

function fillViaTouch(dom, text) {
  byId(dom, "touchArea").classList.remove("hidden");  // force touch mode for this test step
  byId(dom, "voiceArea").classList.add("hidden");
  byId(dom, "touchText").value = text;
  byId(dom, "touchSubmitBtn").dispatchEvent(new dom.window.Event("click", { bubbles: true }));
}

function fillDate(dom, isoDate) {
  byId(dom, "dateInput").value = isoDate;
  byId(dom, "dateSubmitBtn").dispatchEvent(new dom.window.Event("click", { bubbles: true }));
}

function clickService(dom) {
  // Downstream workflow regression tests start after intent confirmation; the
  // voice classifier itself is covered by speech-lab's unit tests.
  dom.window.enterWorkflow("BIRTH_REGISTRATION");
}

// --- page structure ------------------------------------------------------------

test("GET /kiosk/ serves the real demo page", async () => {
  const res = await fetch(`http://localhost:${TEST_PORT}/kiosk/`);
  assert.equal(res.status, 200);
  const html = await res.text();
  assert.match(html, /Mthandizi/);
  assert.match(html, /Demo simulator, not the real kiosk/,
    "the honesty banner must be present - this must never look like the real kiosk");
});

test("the open-ended greeting is shown first with no service list", async () => {
  const dom = await loadKiosk();
  assert.equal(byId(dom, "screen-intent").classList.contains("hidden"), false);
  assert.equal(byId(dom, "micStatus").tagName, "DIV",
    "voice listening should start automatically, not require a tap-to-speak button");
  assert.equal(byId(dom, "micBtn"), null);
  assert.equal(byId(dom, "screen-slot").classList.contains("hidden"), true);
  assert.match(byId(dom, "intentPrompt").textContent, /Ndingakuthandizeni bwanji lero/);
  assert.equal(dom.window.document.querySelector(".service-grid"), null);
  assert.equal(dom.window.document.querySelector(".service-card"), null);
});

test("a confident birth intent is repeated back and only enters after an affirmative reply", async () => {
  const dom = await loadKiosk();
  dom.window.handleIntentClassification({
    outcome: "ACCEPT", key: "BIRTH_REGISTRATION", score: 1,
    runner_up: null, confidence: "high",
  });
  assert.match(byId(dom, "intentPrompt").textContent, /Mukufuna kulembetsa mwana/);
  assert.equal(byId(dom, "screen-intent").classList.contains("hidden"), false);
  assert.equal(byId(dom, "intentChoices").classList.contains("hidden"), false);

  byId(dom, "intentYesBtn").dispatchEvent(new dom.window.Event("click", { bubbles: true }));
  assert.equal(byId(dom, "screen-slot").classList.contains("hidden"), false);
  assert.equal(byId(dom, "slotPrompt").textContent, "Dzina la mwana ndi ndani?");

  let spokenConfirmation = "NO";
  dom.window.fetch = async (url) => ({
    ok: true,
    json: async () => String(url).includes("slot=yesno")
      ? { text: spokenConfirmation === "YES" ? "inde" : "ayi", likely_silent: false,
          resolution: { outcome: "ACCEPT", key: spokenConfirmation } }
      : { text: "Chikondi Phiri", likely_silent: false },
  });
  await dom.window.handleRecordedAudio(new dom.window.Blob(["audio"]));
  assert.equal(byId(dom, "slotChoices").classList.contains("hidden"), false);
  await dom.window.handleRecordedAudio(new dom.window.Blob(["audio"]));
  assert.equal(byId(dom, "slotPrompt").textContent, "Dzina la mwana ndi ndani?",
    "a spoken no must leave the current slot unanswered");
  assert.equal(byId(dom, "slotChoices").classList.contains("hidden"), true,
    "a spoken no must return to listening for the answer again");

  await dom.window.handleRecordedAudio(new dom.window.Blob(["audio"]));
  assert.equal(byId(dom, "slotChoices").classList.contains("hidden"), false,
    "the citizen must be able to say the name again after rejecting it");
  spokenConfirmation = "YES";
  await dom.window.handleRecordedAudio(new dom.window.Blob(["audio"]));
  assert.equal(byId(dom, "slotPrompt").textContent.includes("anabadwa"), true);
});

test("ambiguous intent asks a conversational question instead of showing a list", async () => {
  const dom = await loadKiosk();
  dom.window.handleIntentClassification({
    outcome: "DISAMBIGUATE", key: "BIRTH_REGISTRATION", score: 1,
    runner_up: "IMMIGRATION", runner_up_score: 1,
  });
  assert.match(byId(dom, "intentPrompt").textContent, /Kodi mukufuna .* kapena .*\?/);
  assert.equal(dom.window.document.querySelector(".service-grid"), null);
  assert.equal(byId(dom, "screen-intent").classList.contains("hidden"), false);
});

// --- graceful degradation when the real speech pipeline isn't reachable --------

test("unavailable speech audio is reported instead of silently starting an unreadable flow", async () => {
  const dom = await loadKiosk();
  dom.window.fetch = async () => ({ ok: false });
  clickService(dom);
  await flush();
  assert.match(byId(dom, "errorLine").textContent, /Phokoso silikugwira ntchito/);
});

test("repeated undecodable microphone clips stop retrying and hand off to staff", async () => {
  const dom = await loadKiosk();
  let retryCount = 0;
  dom.window.speakAndListen = async () => { retryCount++; };

  await dom.window.handleRecordedAudio(new dom.window.Blob([]));
  await dom.window.handleRecordedAudio(new dom.window.Blob([]));
  await dom.window.handleRecordedAudio(new dom.window.Blob([]));

  assert.equal(retryCount, 2, "only two automatic retries should occur");
  assert.match(byId(dom, "intentError").textContent, /Pemphani thandizo/);
});

test("spoken dates accept supported Chichewa month names and reject impossible dates", async () => {
  const dom = await loadKiosk();
  assert.equal(dom.window.parseSpokenDate("10 Malichi 2024"), "2024-03-10");
  assert.equal(dom.window.parseSpokenDate("2024-02-29"), "2024-02-29");
  assert.equal(dom.window.parseSpokenDate("30 February 2024"), null);
  assert.equal(dom.window.parseSpokenDate("10 03 2024"), null);
});

test("the review reads birth details aloud and accepts spoken confirmation", async () => {
  const dom = await loadKiosk();
  dom.window.Audio = class {
    constructor() { this.ended = false; this.paused = true; }
    addEventListener() {}
    async play() { this.ended = true; this.paused = true; }
  };
  dom.window.fetch = async (url, options) => {
    if (String(url).includes("/tts")) {
      return { ok: true, blob: async () => new dom.window.Blob(["audio"]) };
    }
    if (String(url).includes("/asr?slot=yesno")) {
      return { ok: true, json: async () => ({ likely_silent: false, resolution: { key: "YES" } }) };
    }
    if (options?.method === "POST") return { ok: true };
    return { ok: false };
  };

  dom.window.enterWorkflow("BIRTH_REGISTRATION");
  dom.window.advanceSlot("Chikondi Phiri");
  dom.window.advanceSlot("2024-03-10");
  dom.window.advanceSlot("Kamuzu Central Hospital");
  dom.window.advanceSlot("Grace Phiri");
  byId(dom, "skipBtn").click();
  dom.window.advanceSlot("Chilinde");
  dom.window.advanceSlot("Lilongwe");

  assert.match(byId(dom, "reviewStatus").textContent, /10 Malichi 2024/);
  await dom.window.handleReviewConfirmationAudio(new dom.window.Blob(["voice"]));
  assert.equal(byId(dom, "screen-done").classList.contains("hidden"), false);
});

// --- the touch fallback path, end to end ----------------------------------------

test("walking the full birth registration flow via touch reaches the review screen with correct values", async () => {
  const dom = await loadKiosk();
  clickService(dom);
  await flush();

  assert.equal(byId(dom, "slotPrompt").textContent, "Dzina la mwana ndi ndani?");
  fillViaTouch(dom, "Chikondi Phiri");
  await flush();

  assert.equal(byId(dom, "slotPrompt").textContent.includes("anabadwa"), true);
  fillDate(dom, "2024-03-10");
  await flush();

  fillViaTouch(dom, "Kamuzu Central Hospital");   // birth_place
  await flush();
  fillViaTouch(dom, "Grace Phiri");                 // mother_name
  await flush();

  // father_name is optional - skip it
  assert.equal(byId(dom, "skipBtn").classList.contains("hidden"), false,
    "skip must be offered for the optional father_name slot");
  byId(dom, "skipBtn").dispatchEvent(new dom.window.Event("click", { bubbles: true }));
  await flush();

  fillViaTouch(dom, "Chilinde");                    // village
  await flush();
  fillViaTouch(dom, "Lilongwe");                    // district (touch, not voice, in this test)
  await flush();

  assert.equal(byId(dom, "screen-review").classList.contains("hidden"), false);
  const reviewHtml = byId(dom, "reviewList").innerHTML;
  assert.match(reviewHtml, /Chikondi Phiri/);
  assert.match(reviewHtml, /Kamuzu Central Hospital/);
  assert.match(reviewHtml, /skipped/, "father_name must show as skipped, not blank or fabricated");
  assert.match(reviewHtml, /Lilongwe/);
});

test("skip is never offered for a required slot (child_name)", async () => {
  const dom = await loadKiosk();
  clickService(dom);
  await flush();
  assert.equal(byId(dom, "skipBtn").classList.contains("hidden"), true);
});

test("back navigation returns to the previous slot", async () => {
  const dom = await loadKiosk();
  clickService(dom);
  await flush();
  fillViaTouch(dom, "Chikondi Phiri");
  await flush();
  assert.equal(byId(dom, "slotPrompt").textContent.includes("anabadwa"), true);  // now on child_dob

  byId(dom, "backBtn").dispatchEvent(new dom.window.Event("click", { bubbles: true }));
  await flush();
  assert.equal(byId(dom, "slotPrompt").textContent, "Dzina la mwana ndi ndani?",
    "must be back on child_name");
});

test("editing a field from the review screen jumps back to that slot", async () => {
  const dom = await loadKiosk();
  clickService(dom);
  await flush();
  for (const [val, isDate] of [
    ["Chikondi Phiri", false], ["2024-03-10", true], ["Somewhere", false],
    ["Grace Phiri", false],
  ]) {
    if (isDate) fillDate(dom, val); else fillViaTouch(dom, val);
    await flush();
  }
  byId(dom, "skipBtn").dispatchEvent(new dom.window.Event("click", { bubbles: true }));  // father_name
  await flush();
  fillViaTouch(dom, "Chilinde");
  await flush();
  fillViaTouch(dom, "Lilongwe");
  await flush();

  assert.equal(byId(dom, "screen-review").classList.contains("hidden"), false);

  dom.window.document.querySelector('[data-edit="child_name"]')
    .dispatchEvent(new dom.window.Event("click", { bubbles: true }));
  await flush();

  assert.equal(byId(dom, "screen-slot").classList.contains("hidden"), false);
  assert.equal(byId(dom, "slotPrompt").textContent, "Dzina la mwana ndi ndani?");
});

// --- REAL backend submission, REAL database verification ------------------------

test("submitting the review creates a REAL application in the REAL database", async () => {
  const dom = await loadKiosk();
  clickService(dom);
  await flush();
  for (const [val, isDate] of [
    ["Chikondi Phiri", false], ["2024-03-10", true], ["Somewhere", false],
    ["Grace Phiri", false],
  ]) {
    if (isDate) fillDate(dom, val); else fillViaTouch(dom, val);
    await flush();
  }
  byId(dom, "skipBtn").dispatchEvent(new dom.window.Event("click", { bubbles: true }));
  await flush();
  fillViaTouch(dom, "Chilinde");
  await flush();
  fillViaTouch(dom, "Lilongwe");
  await flush();

  await dom.window.submitApplication();

  assert.equal(byId(dom, "screen-done").classList.contains("hidden"), false,
    "must reach the completion screen after real submission succeeds");
  const refText = byId(dom, "refNumber").textContent;
  assert.match(refText, /^BR-\d{6}$/);

  // Check the REAL database, not the DOM.
  const dbRow = await pool.query(
    "SELECT * FROM applications WHERE reference_number = $1", [refText]
  );
  assert.equal(dbRow.rows.length, 1, "the application must actually exist in Postgres");
  assert.equal(dbRow.rows[0].service_id, "BIRTH_REGISTRATION");
  assert.equal(dbRow.rows[0].payload.child_name, "Chikondi Phiri");
  assert.equal(dbRow.rows[0].payload.district, "Lilongwe");
  assert.equal(dbRow.rows[0].status, "pending_verification");
  assert.equal("father_name" in dbRow.rows[0].payload, false,
    "a skipped optional field must not appear in the stored payload at all");

  // And the kiosk row was auto-provisioned - same real backend guarantee
  // proven in api.test.js, now exercised through the actual demo UI.
  const kioskRow = await pool.query("SELECT id FROM kiosks WHERE id = $1", ["kiosk-demo-browser"]);
  assert.equal(kioskRow.rows.length, 1);
});

test("the disclaimer on the completion screen states this is not an issued document", async () => {
  const dom = await loadKiosk();
  clickService(dom);
  await flush();
  for (const [val, isDate] of [
    ["Test Child", false], ["2024-01-01", true], ["Somewhere", false], ["Test Mother", false],
  ]) {
    if (isDate) fillDate(dom, val); else fillViaTouch(dom, val);
    await flush();
  }
  byId(dom, "skipBtn").dispatchEvent(new dom.window.Event("click", { bubbles: true }));
  await flush();
  fillViaTouch(dom, "Village");
  await flush();
  fillViaTouch(dom, "Blantyre");
  await flush();
  byId(dom, "confirmBtn").dispatchEvent(new dom.window.Event("click", { bubbles: true }));
  await flush(500);

  const disclaimerText = dom.window.document.querySelector(".disclaimer").textContent;
  assert.match(disclaimerText, /not an issued document/);
});
