import { writeFileSync } from "node:fs";
import { InlineQueue } from "../apps/api/src/queue.js";
import { buildServer } from "../apps/api/src/server.js";
import { closeDb } from "@cgi/database";

// Generates docs/openapi.json from the live Fastify route registrations.
async function main() {
  const app = await buildServer(new InlineQueue());
  await app.ready();
  const doc = app.swagger();
  writeFileSync(new URL("../docs/openapi.json", import.meta.url), JSON.stringify(doc, null, 2));
  await app.close();
  await closeDb();
  console.log("Wrote docs/openapi.json");
  process.exit(0);
}
main().catch((e) => {
  console.error(e);
  process.exit(1);
});
