// MTHANDIZI Backend — request validation via zod.

import { z } from "zod";

export const createApplicationSchema = z.object({
  serviceId: z.string().min(1),
  referenceNumber: z.string().min(1),
  kioskId: z.string().min(1),
  // A completed workflow-engine review list: slot id -> filled value.
  // Deliberately a free-form record, not a per-service-typed schema - the
  // whole point of Phase 3's engine is that services are config, not code,
  // and this backend has no business knowing what fields BIRTH_REGISTRATION
  // has versus IMMIGRATION. Structural validation of slot VALUES already
  // happened in the workflow engine before this request was ever sent.
  payload: z.record(z.string(), z.string()),
  idempotencyKey: z.string().min(1),
});

export const verifyApplicationSchema = z.object({
  status: z.enum(["verified", "rejected"]),
});

export const loginSchema = z.object({
  username: z.string().min(1),
  password: z.string().min(1),
});

export const listApplicationsQuerySchema = z.object({
  status: z.enum(["pending_verification", "verified", "rejected"]).optional(),
  serviceId: z.string().optional(),
  limit: z.coerce.number().int().positive().max(200).default(50),
  offset: z.coerce.number().int().nonnegative().default(0),
});
