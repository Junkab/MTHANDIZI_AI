import { loginSchema } from "../validators/schemas.js";
import * as authService from "../services/authService.js";

export async function login(req, res, next) {
  try {
    const parsed = loginSchema.safeParse(req.body);
    if (!parsed.success) {
      return res.status(400).json({ error: "Invalid request body", details: parsed.error.issues });
    }
    const user = await authService.verifyCredentials(parsed.data.username, parsed.data.password);
    if (!user) return res.status(401).json({ error: "Invalid username or password" });
    const token = authService.issueToken(user);
    res.json({ token, expiresIn: process.env.JWT_EXPIRES_IN ?? "8h" });
  } catch (err) {
    next(err);
  }
}
