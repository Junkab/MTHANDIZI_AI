import { createAdminUser } from "./src/services/authService.js";
import { pool } from "./src/db.js";

const user = await createAdminUser("dube", "1111");
console.log("created admin:", user.username);
await pool.end();
