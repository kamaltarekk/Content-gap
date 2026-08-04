import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { getActiveProjectId } from "../project";
import { JOURNEY_STAGES } from "../types";
import type { CoverageMatrixCell, JourneyStage } from "../types";
import { cohortNameMap, useCohorts } from "../hooks";
import { ErrorNote, Spinner } from "../components/ui";

interface Selected {
  cohortId: string;
  stage: JourneyStage;
}

export function CoveragePage() {
  const projectId = getActiveProjectId() ?? "";
  const cohortsQuery = useCohorts(projectId);
  const names = cohortNameMap(cohortsQuery.data);
  const [selected, setSelected] = useState<Selected | null>(null);

  const coverageQuery = useQuery({
    queryKey: ["coverage", projectId],
    queryFn: () => api.getCoverage(projectId),
  });

  if (coverageQuery.isLoading) return <Spinner />;
  if (coverageQuery.isError) return <ErrorNote error={coverageQuery.error} />;
  const data = coverageQuery.data;
  if (!data) return null;

  // Distinct cohort ids present in the matrix (fall back to cohort list order).
  const cohortIds = Array.from(
    new Set([
      ...(cohortsQuery.data ?? []).map((c) => c.id),
      ...data.matrix.map((m) => m.cohortId),
    ]),
  );

  const lookup = new Map<string, CoverageMatrixCell>();
  for (const m of data.matrix) {
    lookup.set(`${m.cohortId}|${m.journeyStage}`, m);
  }

  const selectedNeeds = selected
    ? data.cells.filter(
        (c) =>
          c.cohortId === selected.cohortId &&
          c.journeyStage === selected.stage,
      )
    : [];

  return (
    <div>
      <h1>Coverage matrix</h1>
      <p className="subtitle">
        Cohort × journey stage. Each cell shows required / strong /
        weak-or-partial / gaps / evidence-gaps / oversaturated. Click a cell for
        the underlying needs.
      </p>

      <div className="table-wrap">
        <table className="matrix">
          <thead>
            <tr>
              <th>Cohort</th>
              {JOURNEY_STAGES.map((s) => (
                <th key={s}>{s}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {cohortIds.map((cid) => (
              <tr key={cid}>
                <th style={{ textAlign: "left" }}>{names.get(cid) ?? cid}</th>
                {JOURNEY_STAGES.map((stage) => {
                  const cell = lookup.get(`${cid}|${stage}`);
                  const isSel =
                    selected?.cohortId === cid && selected?.stage === stage;
                  return (
                    <td
                      key={stage}
                      className="cell"
                      onClick={() => setSelected({ cohortId: cid, stage })}
                      style={
                        isSel
                          ? { outline: "2px solid var(--accent)" }
                          : undefined
                      }
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          setSelected({ cohortId: cid, stage });
                        }
                      }}
                    >
                      {cell ? (
                        <div className="cell-line">
                          <div>req {cell.requiredNeeds}</div>
                          <div className="cell-strong">
                            strong {cell.strong}
                          </div>
                          <div>weak {cell.weakOrPartial}</div>
                          <div className="cell-gaps">gaps {cell.gaps}</div>
                          <div>ev-gap {cell.evidenceGaps}</div>
                          <div>over {cell.oversaturated}</div>
                        </div>
                      ) : (
                        <span className="muted">—</span>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selected && (
        <div className="card" style={{ marginTop: 20 }}>
          <h2>
            Needs — {names.get(selected.cohortId) ?? selected.cohortId} ·{" "}
            {selected.stage}
          </h2>
          {selectedNeeds.length === 0 && (
            <p className="muted">No needs recorded for this cell.</p>
          )}
          {selectedNeeds.length > 0 && (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Need</th>
                    <th>Type</th>
                    <th>Coverage status</th>
                    <th>Supporting assets</th>
                  </tr>
                </thead>
                <tbody>
                  {selectedNeeds.map((n, i) => (
                    <tr key={`${n.normalizedNeed}-${i}`}>
                      <td>{n.normalizedNeed}</td>
                      <td>{n.needType}</td>
                      <td>{n.coverageStatus}</td>
                      <td>{n.supportingAssetCount}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
