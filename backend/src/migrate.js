// MTHANDIZI Backend — migration runner. Deliberately simple: reads .sql
// files from src/migrations/ in filename order, tracks what's already been
// applied in a schema_migrations table, runs anything new. No external
// migration framework — this is small enough not to need one, and it's one
// less dependency that could fail to install.

import { readdirSync, readFileSync } from "fs";
import { fileURLToPath, pathToFileURL } from "url";
import path from "path";
import { pool } from "./db.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const migrationsDir = path.join(__dirname, "migrations");

async function ensureMigrationsTable() {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS schema_migrations (
      filename    TEXT PRIMARY KEY,
      applied_at  TIMESTAMPTZ NOT NULL DEFAULT now()
    )
  `);
}

async function alreadyApplied() {
  const result = await pool.query("SELECT filename FROM schema_migrations");
  return new Set(result.rows.map((r) => r.filename));
}

export async function migrate() {
  await ensureMigrationsTable();
  const applied = await alreadyApplied();

  const files = readdirSync(migrationsDir)
    .filter((f) => f.endsWith(".sql"))
    .sort();

  let ranCount = 0;
  for (const file of files) {
    if (applied.has(file)) continue;
    const sql = readFileSync(path.join(migrationsDir, file), "utf-8");
    console.log(`[migrate] applying ${file}`);
    await pool.query(sql);
    await pool.query("INSERT INTO schema_migrations (filename) VALUES ($1)", [file]);
    ranCount++;
  }

  if (ranCount === 0) {
    console.log("[migrate] nothing to do, schema up to date");
  } else {
    console.log(`[migrate] applied ${ranCount} migration(s)`);
  }
  return ranCount;
}

// Allow running directly: `node src/migrate.js`
//
// BUG FOUND ON WINDOWS (2026-09-24, real operator machine): the original
// check here was `import.meta.url === `file://${process.argv[1]}``, a
// hand-built string comparison. On Windows this NEVER matches -
// process.argv[1] is a Windows path like "C:\...\migrate.js" (backslashes,
// no scheme), while import.meta.url is a proper file URL like
// "file:///C:/.../migrate.js" (forward slashes, three slashes after
// "file:"). The naive concatenation produces "file://C:\...\migrate.js",
// which is not equal to the real URL - so the guard was always false on
// Windows, and `node src/migrate.js` silently did NOTHING: no output, no
// error, migration never ran. This worked fine on Linux (where the
// authoring/testing happened) purely because Linux paths already use
// forward slashes, masking the bug entirely until a real Windows run
// exposed it. Fixed using Node's own `pathToFileURL()`, the documented
// correct way to do this comparison cross-platform.
if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  migrate()
    .then(() => process.exit(0))
    .catch((err) => {
      console.error("[migrate] FAILED:", err);
      process.exit(1);
    });
}
