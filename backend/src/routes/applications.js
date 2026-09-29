import { Router } from "express";
import * as controller from "../controllers/applicationsController.js";
import { requireAdmin } from "../middleware/auth.js";

const router = Router();

// Kiosk-facing: creating/syncing a completed application is NOT admin-gated.
// A kiosk in the field authenticates by physical possession + network access
// to the sidecar, not by JWT - see API_CONTRACT.md for why this boundary is
// where it is, not "everything requires a token."
router.post("/", controller.create);

// Admin-only: viewing and verifying applications.
router.get("/", requireAdmin, controller.list);
router.get("/stats", requireAdmin, controller.stats);
router.get("/:id", requireAdmin, controller.getOne);
router.patch("/:id/verify", requireAdmin, controller.verify);

export default router;
