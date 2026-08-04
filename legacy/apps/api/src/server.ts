import { getDb } from "@cgi/database";
import { loadConfig } from "@cgi/shared";
import cors from "@fastify/cors";
import swagger from "@fastify/swagger";
import Fastify, { type FastifyInstance } from "fastify";
import { ZodError } from "zod";
import type { Queue } from "./queue.js";
import { registerRoutes } from "./routes.js";

export async function buildServer(queue: Queue): Promise<FastifyInstance> {
  const config = loadConfig();
  const app = Fastify({ logger: { level: config.logLevel } });

  await app.register(cors, {
    origin: (origin, cb) => {
      if (!origin) return cb(null, true);
      const allowed = config.api.corsOrigins.some((o) => o === origin || (o.endsWith("*") && origin.startsWith(o.slice(0, -1))));
      cb(null, allowed);
    },
  });

  await app.register(swagger, {
    openapi: {
      info: { title: "Content Gap Intelligence API", version: "0.1.0", description: "v0 backend — evidence-verified content-gap detection." },
      servers: [{ url: `http://localhost:${config.api.port}` }],
    },
  });

  app.setErrorHandler((err, _req, reply) => {
    if (err instanceof ZodError) {
      return reply.code(400).send({ error: "validation_error", issues: err.issues });
    }
    app.log.error(err);
    return reply.code(500).send({ error: "internal_error", message: (err as Error).message });
  });

  await registerRoutes(app, getDb(), queue);

  // OpenAPI document (generated from registered routes) + a tiny docs page.
  app.get("/openapi.json", async () => app.swagger());
  app.get("/docs", async (_req, reply) => {
    reply.type("text/html").send(
      `<!doctype html><title>CGI API</title><body style="font-family:system-ui;padding:2rem"><h1>Content Gap Intelligence API</h1><p>OpenAPI: <a href="/openapi.json">/openapi.json</a></p></body>`,
    );
  });
  return app;
}
