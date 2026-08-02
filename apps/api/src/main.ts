import { loadConfig } from "@cgi/shared";
import { createQueue } from "./queue.js";
import { buildServer } from "./server.js";

async function main() {
  const config = loadConfig();
  const queue = await createQueue();
  const app = await buildServer(queue);
  await app.listen({ host: config.api.host, port: config.api.port });
  app.log.info(`API listening on http://${config.api.host}:${config.api.port} (docs at /docs json at /openapi.json)`);

  const shutdown = async () => {
    await app.close();
    await queue.stop();
    process.exit(0);
  };
  process.on("SIGINT", shutdown);
  process.on("SIGTERM", shutdown);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
