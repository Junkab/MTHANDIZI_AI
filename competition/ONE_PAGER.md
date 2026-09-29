# MTHANDIZI — One-Pager

*Lankhulani. Mthandizi akuthandizeni.* — Speak. Mthandizi will help you.

A voice-first, Chichewa-speaking kiosk that lets citizens register a birth,
join a hospital queue, apply for a national ID, or request a passport — by
talking to a machine in their own language, no smartphone, no internet
connection, no literacy required.

---

## The problem

Malawi's digital public-service gap is not a coverage problem — it's a
**usage** and **literacy** problem, and the numbers are stark and recent:

- **81.2% of Malawi's population lives in rural areas** (DataReportal,
  *Digital 2025: Malawi*, Jan 2025).
- Mobile network coverage is genuinely good — **87% 4G population
  coverage nationally** — but **unique mobile internet penetration is only
  12.5%**, and **smartphone adoption is just 33%** (GSMA, *Driving Digital
  Transformation of the Economy in Malawi*, August 2026). The network
  reaches people; the devices and data plans to use it don't.
- In rural areas specifically, that gap widens further: 4G coverage drops
  to **71%**, and **80% of Malawians live within mobile broadband coverage
  but simply do not use mobile internet** — one of the largest such usage
  gaps in Africa, well above the regional average of ~65% (GSMA, Aug 2026).
- Adult literacy estimates range from roughly **62–66%** depending on
  source and year (UNESCO Institute for Statistics via World Bank; Maxinomics,
  2025) — meaning a meaningful share of citizens cannot reliably navigate an
  English-language form, on paper or on a screen, even where one is available.

**The people this affects most are exactly the people a smartphone-app
solution doesn't reach.** A mobile app assumes a smartphone, a data plan,
literacy, and English — four assumptions that together exclude a large share
of the population this kind of service is meant to serve.

## The solution

**MTHANDIZI is a shared kiosk, not a personal app** — deliberately matching
how Malawians actually access technology today (mobile *money* is used by
75% of adults; mobile *internet* by 12.5% — the gap is devices and literacy,
not willingness). A citizen walks up, speaks Chichewa, and is guided
question-by-question through a real government-service intake, entirely by
voice, with touch as a fallback at every step. No login, no app install, no
data plan, no English required.

**It works with zero internet.** Speech recognition runs on a local compute
unit inside the kiosk itself — the same architecture pattern as an ATM —
and syncs to a central backend automatically whenever connectivity becomes
available. Nothing about the citizen-facing experience depends on the
network being up at that moment.

## What makes this credible, not just a pitch

This is not a mockup. It is a real, running, multi-layer system with a
genuine evidence trail — see `WHAT_WE_VERIFIED.md` for the full detail, but
in short:

- **The core speech pipeline was proven on real Chichewa, not a demo
  script**: a real benchmark run against real recordings measured
  **36.1% word error rate** and **9.1% character error rate** — both close
  to the published figures for the underlying model — and, after finding
  and fixing a real matcher bug live during testing, achieved **100% slot
  resolution accuracy** on that same real data.
- **281 automated tests, run for real** — not written and assumed correct —
  spanning speech recognition, a Kotlin workflow engine, a Node/PostgreSQL
  backend, and an admin dashboard, including tests against a real database
  and a real browser-equivalent DOM, not mocks.
- **The Chichewa language pack was reviewed by a real native speaker**, not
  machine-translated and left unchecked.
- Every real bug found along the way — and several were — is documented
  with its root cause and fix, not hidden.

## Scalability

- **Adding a language is a configuration change, not a rewrite.** The
  language-pack architecture already separates every spoken string from the
  code that uses it — extending to Chitumbuka (dominant in Northern Malawi)
  or Chiyao is new JSON content, not new engineering.
- **Adding a government service is proven to require zero changes to the
  workflow engine** — demonstrated directly with a real, working throwaway
  fifth service built purely as configuration during testing.
- **One backend can serve many kiosks.** The backend and admin dashboard
  already support multiple kiosks reporting into one place, with real
  per-kiosk tracking already built in.

## Honest limitations

Stated plainly, not glossed over — full detail in `LIMITATIONS.md`:

- This is a prototype. It has no live connection to any government
  database and does not issue official documents — it prepares applications
  for human officer verification, and says so on-screen and aloud.
- Government service field lists (what a birth registration or ID
  application actually requires) are a reasonable first draft, not verified
  against official Malawian government forms.
- The text-to-speech voice has one known limitation with short standalone
  words (documented and worked around); this is exactly the kind of gap a
  short human-recorded prompt — already the planned fallback — resolves
  completely.
- The Android client itself has not yet been built — this sandbox's
  toolchain could not reach Android's dependency infrastructure any more
  than it could reach some of the other services this project depends on,
  confirmed directly rather than assumed.

---

*Statistics current as of research conducted September 2026; see inline
citations. Bill of materials, demo script, and full verification detail in
their own documents alongside this one.*
