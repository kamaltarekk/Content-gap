export * as schema from "./schema.js";
export * from "./schema.js";
export { getDb, getPool, closeDb, type Db } from "./client.js";
export { runMigrations } from "./migrate.js";
export { seedDemo } from "./seed.js";

/** pgvector wants a bracketed string like "[0.1,0.2,...]". */
export function toVectorLiteral(vec: number[]): string {
  return `[${vec.join(",")}]`;
}
