// MTHANDIZI Backend — config
//
// Single env-loading point, same rule as every other project in this repo
// (speech-lab/lab/config.py, speech-service/app/config.py): the build
// prompt's own quality bar calls out "environment config loaded scattered
// per-file" as a real failure class to avoid, so this is the only file that
// touches process.env / dotenv directly.

import dotenv from "dotenv";
dotenv.config();

function required(name, fallback) {
  const value = process.env[name] ?? fallback;
  if (value === undefined) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}

export const config = {
  port: parseInt(process.env.PORT ?? "3000", 10),
  db: {
    host: process.env.DB_HOST ?? "localhost",
    port: parseInt(process.env.DB_PORT ?? "5432", 10),
    database: process.env.DB_NAME ?? "mthandizi",
    user: process.env.DB_USER ?? "mthandizi",
    password: process.env.DB_PASSWORD ?? "devpassword",
  },
  jwtSecret: required("JWT_SECRET", "dev-only-secret-change-in-production"),
  jwtExpiresIn: process.env.JWT_EXPIRES_IN ?? "8h",
  bcryptRounds: parseInt(process.env.BCRYPT_ROUNDS ?? "10", 10),
  speechServiceUrl: process.env.MTHANDIZI_SPEECH_SERVICE_URL ?? "http://localhost:8090",
};
