// MTHANDIZI Backend — auth middleware.
//
// Which endpoints are gated by this vs. left open is documented explicitly
// in API_CONTRACT.md, not left implicit — the build prompt's Section 11
// requires exactly this: "Document explicitly which endpoints are gated and
// which are not, and why."

import { verifyToken } from "../services/authService.js";

export function requireAdmin(req, res, next) {
  const header = req.headers.authorization;
  if (!header || !header.startsWith("Bearer ")) {
    return res.status(401).json({ error: "Missing or malformed Authorization header" });
  }
  const token = header.slice("Bearer ".length);
  try {
    req.admin = verifyToken(token);
    next();
  } catch (err) {
    return res.status(401).json({ error: "Invalid or expired token" });
  }
}
