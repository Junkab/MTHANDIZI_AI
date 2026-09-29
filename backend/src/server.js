import { app } from "./app.js";
import { config } from "./config.js";
import { migrate } from "./migrate.js";

async function main() {
  await migrate();  // ensure schema is current before accepting traffic
  app.listen(config.port, () => {
    console.log(`MTHANDIZI backend listening on http://localhost:${config.port}`);
  });
}

main().catch((err) => {
  console.error("[server] failed to start:", err);
  process.exit(1);
});
