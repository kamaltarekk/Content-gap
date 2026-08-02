import { defineConfig } from "drizzle-kit";

// Authoritative DDL lives in migrations/*.sql (applied by src/migrate.ts). This config
// enables `drizzle-kit` introspection/generation against the same schema if desired.
export default defineConfig({
  schema: "./src/schema.ts",
  out: "./migrations",
  dialect: "postgresql",
  dbCredentials: {
    url: process.env.DATABASE_URL ?? "postgres://cgi:cgi@localhost:5433/cgi",
  },
});
