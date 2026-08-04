import { Fragment, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { getActiveProjectId } from "../project";
import type { Run } from "../types";
import { ErrorNote, Spinner } from "../components/ui";
import { formatDate, formatUsd } from "../utils";

function publishedGaps(run: Run): number | string {
  const v = run.outputCountsJson?.publishedGaps;
  return typeof v === "number" ? v : "—";
}

export function RunsPage() {
  const projectId = getActiveProjectId() ?? "";
  const [expanded, setExpanded] = useState<string | null>(null);

  const runsQuery = useQuery({
    queryKey: ["runs", projectId],
    queryFn: () => api.getRuns(projectId),
  });

  if (runsQuery.isLoading) return <Spinner />;
  if (runsQuery.isError) return <ErrorNote error={runsQuery.error} />;
  const runs = runsQuery.data ?? [];

  return (
    <div>
      <h1>Analysis runs</h1>
      <p className="subtitle">
        Runs trigger automatically on ingestion. Expand a row to inspect the
        stage log.
      </p>

      {runs.length === 0 && (
        <div className="callout callout-info">No runs recorded yet.</div>
      )}

      {runs.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Trigger</th>
                <th>Status</th>
                <th>Started</th>
                <th>Completed</th>
                <th>Published gaps</th>
                <th>Est. cost</th>
                <th>Ignored injections</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => {
                const isOpen = expanded === run.id;
                return (
                  <Fragment key={run.id}>
                    <tr>
                      <td>{run.triggerType}</td>
                      <td>{run.status}</td>
                      <td>{formatDate(run.startedAt)}</td>
                      <td>{formatDate(run.completedAt)}</td>
                      <td>{publishedGaps(run)}</td>
                      <td>{formatUsd(run.usageJson?.estimatedCostUsd)}</td>
                      <td>{run.usageJson?.ignoredInjectionAttempts ?? 0}</td>
                      <td>
                        <button
                          className="secondary small"
                          onClick={() =>
                            setExpanded(isOpen ? null : run.id)
                          }
                          aria-expanded={isOpen}
                        >
                          {isOpen ? "Hide" : "Stages"}
                        </button>
                      </td>
                    </tr>
                    {isOpen && (
                      <tr>
                        <td colSpan={8}>
                          {run.errorSummary && (
                            <div className="callout callout-danger">
                              {run.errorSummary}
                            </div>
                          )}
                          <div className="field-hint">
                            pipeline version: {run.pipelineVersion ?? "—"}
                          </div>
                          <pre className="log">
                            {JSON.stringify(run.stageLogJson ?? {}, null, 2)}
                          </pre>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
