# MTHANDIZI — Bill of Materials (one kiosk unit)

All prices researched September 2026. **Confidence varies by line item, and
this is marked honestly rather than presented as uniformly precise** — tablet
pricing is sourced from a Malawi-specific retail listing site; mini-PC and
accessory pricing is sourced from general wholesale listings and should be
treated as an estimate pending local sourcing, not a quote.

Exchange rate used throughout: **1 USD ≈ 1,735 MWK** (mid-2026 average,
relatively stable across the year per Trading Economics / CurrencyBeacon
data). Actual rates fluctuate; treat all MWK figures as indicative.

| Item | Est. cost (USD) | Est. cost (MWK) | Confidence | Notes |
|---|---:|---:|---|---|
| Android tablet (10", budget) | $106–118 | 184,500–205,000 | **High** — Malawi retail listing, Jul 2026 | Galaxy Tab A9 2023 or equivalent; this is the citizen-facing device |
| Mini-PC (Intel N100-class, 8GB RAM, 256GB SSD) | $115–260 | 200,000–451,000 | **Low-medium** — wholesale/bulk listings, not localised | The speech sidecar (Section 2.3) — needs no more than modest CPU; the real ASR benchmark in this project ran acceptably on comparable hardware |
| Kiosk stand / enclosure | $40–80 | 69,000–139,000 | **Estimate only** — no sourcing done | Simple welded-metal or wood stand; highly variable by local fabrication cost |
| UPS / battery backup (for the mini-PC) | $30–60 | 52,000–104,000 | **Estimate only** | Sized to bridge short outages, not run the kiosk indefinitely off-grid |
| Optional: small thermal printer (for the PDF summary) | $40–90 | 69,000–156,000 | **Estimate only** | Not required — a QR code alone is sufficient for verification; a printout is a convenience |
| Cabling, mounting hardware, misc. | $15–30 | 26,000–52,000 | **Estimate only** | |
| **Total (without printer)** | **≈ $306–548** | **≈ 531,000–951,000** | | |
| **Total (with printer)** | **≈ $346–638** | **≈ 600,000–1,107,000** | | |

## What is NOT priced above, and why

- **Solar power.** Given Malawi's grid-reliability context, a solar +
  battery setup is a reasonable enhancement for many kiosk locations, but
  sizing depends entirely on local conditions (panel wattage, battery
  capacity, hours of expected outage) that weren't researched with enough
  confidence to put a number on. Flagged as a real, worthwhile next
  question rather than an invented figure.
- **Staff time, installation, or maintenance costs.** Genuinely out of
  scope for a hardware BOM and highly context-dependent.
- **Network connectivity costs.** The kiosk's speech pipeline runs entirely
  offline (see `ONE_PAGER.md`); the only network dependency is periodic sync
  to the backend, which could reasonably use existing site connectivity
  (many hospitals/NRB offices already have some connection) rather than a
  dedicated line.

## Why a mini-PC sidecar rather than trying to run everything on the tablet

This is not a cost-cutting compromise — the real Chichewa ASR model used in
this project is ~2.4GB and genuinely does not fit comfortably inside an
Android APK. A local sidecar (the mini-PC) talking to the tablet over a
private local network is the same architecture pattern used by ATMs and
airport check-in kiosks, and was a deliberate design decision, not something
discovered as a limitation late — see `BUILD_LOG.md`, Phase 0.

## Confidence honesty, stated plainly

The tablet price is the one figure in this document backed by a real,
dated, Malawi-specific retail source. Everything else is a reasonable
estimate that should be replaced with actual supplier quotes before this
number is used in any budget planning — flagged here rather than presented
with false precision.
