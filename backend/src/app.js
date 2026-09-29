// MTHANDIZI Backend — Express app assembly.
//
// Kept separate from server.js deliberately: tests import THIS file and use
// supertest against it directly, without ever binding a real network port.
// server.js is the only file that calls app.listen().

import express from "express";
import path from "path";
import { fileURLToPath } from "url";
import applicationsRouter from "./routes/applications.js";
import authRouter from "./routes/auth.js";
import { config } from "./config.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export const app = express();

app.use(express.json());

app.get("/health", (req, res) => {
  res.json({ status: "ok", service: "mthandizi-backend" });
});

app.use("/api/applications", applicationsRouter);
app.use("/api/auth", authRouter);

app.get("/kiosk-config.js", (req, res) => {
  res.type("application/javascript");
  res.setHeader("Cache-Control", "no-store");
  res.send(`window.MTHANDIZI_CONFIG = ${JSON.stringify({ speechServiceUrl: config.speechServiceUrl })};`);
});

// The admin dashboard (Phase 13). Served same-origin from this backend
// deliberately, so its fetch() calls to /api/* need no CORS configuration
// at all - a separate static host would need it, this doesn't.
app.use("/admin", express.static(path.join(__dirname, "../public")));

// The browser kiosk demo (competition materials work). Served the same
// way - same-origin to the backend so its application-submission calls
// need no CORS, while its calls to speech-service (a different origin,
// different port) use the CORS speech-service already has enabled. See
// competition/DEMO_SCRIPT.md and backend/public/kiosk/index.html's own
// header comment for exactly what's real vs simplified in this demo.
app.use(
  "/kiosk",
  express.static(path.join(__dirname, "../public/kiosk"), {
    etag: false,
    setHeaders: (res) => {
      res.setHeader("Cache-Control", "no-store, no-cache, must-revalidate, proxy-revalidate");
      res.setHeader("Pragma", "no-cache");
      res.setHeader("Expires", "0");
    },
  }),
);

// 404 for anything unmatched
app.use((req, res) => {
  res.status(404).json({ error: `No route for ${req.method} ${req.path}` });
});

// Centralised error handler - every controller's next(err) lands here.
// eslint-disable-next-line no-unused-vars
app.use((err, req, res, next) => {
  console.error("[error]", err);
  res.status(500).json({ error: "Internal server error" });
});
