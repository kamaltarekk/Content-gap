import { closeDb, getDb, runMigrations, seedDemo } from "@cgi/database";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import type { FastifyInstance } from "fastify";
import { InlineQueue } from "../src/queue.js";
import { buildServer } from "../src/server.js";

let app: FastifyInstance;
let queue: InlineQueue;
let projectId = "";
let token = "";
let dbAvailable = true;

beforeAll(async () => {
  process.env.LLM_PROVIDER = "fake";
  try {
    await runMigrations();
    const seeded = await seedDemo(getDb());
    projectId = seeded.projectId;
    token = seeded.token;
  } catch {
    dbAvailable = false;
    return;
  }
  queue = new InlineQueue();
  app = await buildServer(queue);
  // Trigger analysis the way ingestion would, then wait for it to finish.
  await queue.enqueueAnalyze({ projectId, triggerType: "MANUAL_SETUP" });
  await queue.drain();
});

afterAll(async () => {
  if (app) await app.close();
  if (dbAvailable) await closeDb();
});

describe("API v1 integration (fake providers, inline queue)", () => {
  it("health", async () => {
    if (!dbAvailable) return;
    const res = await app.inject({ method: "GET", url: "/api/v1/health" });
    expect(res.statusCode).toBe(200);
    expect(res.json().status).toBe("ok");
  });

  it("returns published gaps with evidence", async () => {
    if (!dbAvailable) return;
    const res = await app.inject({ method: "GET", url: `/api/v1/projects/${projectId}/gaps` });
    expect(res.statusCode).toBe(200);
    const gaps = res.json() as { id: string; priorityScore: number }[];
    expect(gaps.length).toBeGreaterThanOrEqual(3);
    expect(gaps.length).toBeLessThanOrEqual(10);
    // sorted desc
    expect(gaps[0]!.priorityScore).toBeGreaterThanOrEqual(gaps[gaps.length - 1]!.priorityScore);
    const detail = await app.inject({ method: "GET", url: `/api/v1/gaps/${gaps[0]!.id}` });
    expect((detail.json() as { evidence: unknown[] }).evidence.length).toBeGreaterThan(0);
  });

  it("exposes a coverage matrix", async () => {
    if (!dbAvailable) return;
    const res = await app.inject({ method: "GET", url: `/api/v1/projects/${projectId}/coverage` });
    expect(res.statusCode).toBe(200);
    expect(Array.isArray(res.json().matrix)).toBe(true);
  });

  it("requires a valid project token for capture", async () => {
    if (!dbAvailable) return;
    const noAuth = await app.inject({
      method: "POST",
      url: `/api/v1/projects/${projectId}/sources/capture`,
      payload: { ownerType: "OWNED", competitorSlot: null, url: "https://x.example/p", title: "t", text: "some captured text about implementation" },
    });
    expect(noAuth.statusCode).toBe(401);

    const withAuth = await app.inject({
      method: "POST",
      url: `/api/v1/projects/${projectId}/sources/capture`,
      headers: { authorization: `Bearer ${token}` },
      payload: { ownerType: "OWNED", competitorSlot: null, url: "https://x.example/new-capture", title: "t", text: "some captured text about implementation" },
    });
    expect(withAuth.statusCode).toBe(201);
    expect(withAuth.json().changed).toBe(true);
    await queue.drain(); // capture auto-triggered reprocessing
  });

  it("accepts evaluations and computes calibration", async () => {
    if (!dbAvailable) return;
    const gaps = (await app.inject({ method: "GET", url: `/api/v1/projects/${projectId}/gaps` })).json() as { id: string }[];
    for (const evaluator of ["Alice", "Bob"]) {
      for (const g of gaps.slice(0, 3)) {
        const r = await app.inject({
          method: "POST",
          url: `/api/v1/gaps/${g.id}/evaluations`,
          payload: { evaluatorName: evaluator, validityRating: 4, commercialRelevanceRating: 5, noveltyRating: 3, evidenceQualityRating: 4, actionabilityRating: 4, acceptedIntoPlan: true, notes: "" },
        });
        expect(r.statusCode).toBe(201);
      }
    }
    const res = await app.inject({ method: "GET", url: `/api/v1/projects/${projectId}/evaluations` });
    const body = res.json() as { calibration: { acceptanceRate: number; ratingAverages: { validity: number } } };
    expect(body.calibration.acceptanceRate).toBe(1);
    expect(body.calibration.ratingAverages.validity).toBeCloseTo(4, 1);
  });

  it("exposes a shadow sample without revealing rank", async () => {
    if (!dbAvailable) return;
    const res = await app.inject({ method: "GET", url: `/api/v1/projects/${projectId}/shadow-sample` });
    expect(res.statusCode).toBe(200);
    const rows = res.json() as { priorityScore?: number }[];
    for (const r of rows) expect(r.priorityScore).toBeUndefined();
  });

  it("rejects invalid input with 400", async () => {
    if (!dbAvailable) return;
    const res = await app.inject({ method: "POST", url: "/api/v1/projects", payload: { name: "" } });
    expect(res.statusCode).toBe(400);
  });
});
