import { loadConfig } from "@cgi/shared";
import { pino } from "pino";

export const logger = pino({
  level: loadConfig().logLevel,
  base: undefined,
});

export type StageLogEntry = {
  stage: string;
  pipelineVersion: string;
  status: "ok" | "failed";
  inputCount: number;
  outputCount: number;
  ms: number;
  error?: string;
  note?: string;
};
