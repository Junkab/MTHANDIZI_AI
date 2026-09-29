// MTHANDIZI Backend — auth service.

import bcrypt from "bcrypt";
import jwt from "jsonwebtoken";
import { pool } from "../db.js";
import { config } from "../config.js";

export async function createAdminUser(username, plainPassword) {
  const hash = await bcrypt.hash(plainPassword, config.bcryptRounds);
  const result = await pool.query(
    "INSERT INTO admin_users (username, password_hash) VALUES ($1, $2) RETURNING id, username, created_at",
    [username, hash]
  );
  return result.rows[0];
}

export async function verifyCredentials(username, plainPassword) {
  const result = await pool.query(
    "SELECT * FROM admin_users WHERE username = $1", [username]
  );
  const user = result.rows[0];
  if (!user) return null;
  const ok = await bcrypt.compare(plainPassword, user.password_hash);
  return ok ? user : null;
}

export function issueToken(user) {
  return jwt.sign(
    { sub: user.id, username: user.username },
    config.jwtSecret,
    { expiresIn: config.jwtExpiresIn }
  );
}

export function verifyToken(token) {
  return jwt.verify(token, config.jwtSecret);  // throws on invalid/expired
}
