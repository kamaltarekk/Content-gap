import { useState } from "react";
import { apiGet, apiPost } from "../api/client";

interface Job {
  job_id?: string;
  id?: string;
  status: string;
  progress_percent?: number;
  current_stage?: string | null;
}
interface JobEvent {
  id: number;
  event_type: string;
  stage: string | null;
  progress_percent: number | null;
}

// Minimal job progress view: enqueue a demo job and poll its status/events. Real job types
// (parse_source, classify_content, run_*_diagnosis, render_report…) reuse this surface.
export default function Jobs() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [events, setEvents] = useState<JobEvent[]>([]);
  const [err, setErr] = useState<string | null>(null);

  async function enqueue() {
    setErr(null);
    try {
      const r = await apiPost<{ job_id: string }>("/api/v1/jobs", {
        job_type: "demo",
        input_manifest: { stages: ["load", "process", "persist"] },
      });
      setJobId(r.job_id);
      await refresh(r.job_id);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "failed");
    }
  }
  async function refresh(id: string) {
    setJob(await apiGet<Job>(`/api/v1/jobs/${id}`));
    setEvents(await apiGet<JobEvent[]>(`/api/v1/jobs/${id}/events`));
  }

  return (
    <section dir="auto" style={{ fontFamily: "system-ui", maxWidth: 720, margin: "2rem auto", padding: "0 1rem" }}>
      <h2>Jobs — المهام</h2>
      <button onClick={enqueue}>Enqueue demo job</button>{" "}
      {jobId && <button onClick={() => refresh(jobId)}>Refresh</button>}
      {err && <p style={{ color: "crimson" }}>{err}</p>}
      {job && (
        <div>
          <p>status: <strong>{job.status}</strong> · progress: {job.progress_percent ?? 0}% · stage: {job.current_stage ?? "—"}</p>
          <div style={{ background: "#eee", height: 8, borderRadius: 4 }}>
            <div style={{ background: "#3a7", height: 8, borderRadius: 4, width: `${job.progress_percent ?? 0}%` }} />
          </div>
          <ul>
            {events.map((e) => (
              <li key={e.id}>{e.event_type}{e.stage ? ` · ${e.stage}` : ""}{e.progress_percent != null ? ` · ${e.progress_percent}%` : ""}</li>
            ))}
          </ul>
          <p style={{ color: "#666" }}>Note: with the inline dispatcher the job runs in-process; with Celery it runs in the worker and continues after the browser closes.</p>
        </div>
      )}
    </section>
  );
}
