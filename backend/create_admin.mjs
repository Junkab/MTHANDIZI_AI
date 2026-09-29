import { createAdminUser } from "./src/services/authService.js";
import { pool } from "./src/db.js";

const user = await createAdminUser("officer1", "correcthorsebattery");
console.log("created admin:", user.username);
await pool.end();
