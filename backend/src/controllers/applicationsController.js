// MTHANDIZI Backend — applications controller. Thin: validate, call the
// service, shape the response. No business logic lives here.

import {
  createApplicationSchema,
  verifyApplicationSchema,
  listApplicationsQuerySchema,
} from "../validators/schemas.js";
import * as applicationsService from "../services/applicationsService.js";

export async function create(req, res, next) {
  try {
    const parsed = createApplicationSchema.safeParse(req.body);
    if (!parsed.success) {
      return res.status(400).json({ error: "Invalid request body", details: parsed.error.issues });
    }
    const { application, wasAlreadySynced } = await applicationsService.createApplication(parsed.data);
    res.status(wasAlreadySynced ? 200 : 201).json({ application, wasAlreadySynced });
  } catch (err) {
    if (err.code === "23505") {  // Postgres unique_violation
      return res.status(409).json({ error: "referenceNumber already exists for a different application" });
    }
    next(err);
  }
}

export async function list(req, res, next) {
  try {
    const parsed = listApplicationsQuerySchema.safeParse(req.query);
    if (!parsed.success) {
      return res.status(400).json({ error: "Invalid query parameters", details: parsed.error.issues });
    }
    const applications = await applicationsService.listApplications(parsed.data);
    res.json({ applications, count: applications.length });
  } catch (err) {
    next(err);
  }
}

export async function getOne(req, res, next) {
  try {
    const application = await applicationsService.getApplicationById(req.params.id);
    if (!application) return res.status(404).json({ error: "Not found" });
    res.json({ application });
  } catch (err) {
    next(err);
  }
}

export async function verify(req, res, next) {
  try {
    const parsed = verifyApplicationSchema.safeParse(req.body);
    if (!parsed.success) {
      return res.status(400).json({ error: "Invalid request body", details: parsed.error.issues });
    }
    const application = await applicationsService.verifyApplication(
      req.params.id, parsed.data.status, req.admin.sub
    );
    if (!application) return res.status(404).json({ error: "Not found" });
    res.json({ application });
  } catch (err) {
    next(err);
  }
}

export async function stats(req, res, next) {
  try {
    const rows = await applicationsService.statsSummary();
    res.json({ stats: rows });
  } catch (err) {
    next(err);
  }
}
