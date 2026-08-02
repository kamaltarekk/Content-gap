import { useState } from "react";
import type { ReactNode } from "react";
import { useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api";
import { getActiveProjectId } from "../project";
import type { EvaluationBody } from "../types";
import { cohortNameMap, useCohorts } from "../hooks";
import { EvaluationForm } from "../components/EvaluationForm";
import { CalibrationSummary } from "../components/CalibrationSummary";
import { Badge, ErrorNote, Spinner } from "../components/ui";

function GapEvaluationRow({
  gapId,
  title,
  meta,
}: {
  gapId: string;
  title: string;
  meta: ReactNode;
}) {
  const queryClient = useQueryClient();
  const projectId = getActiveProjectId() ?? "";
  const [done, setDone] = useState(false);
  const mutation = useMutation({
    mutationFn: (body: EvaluationBody) => api.createGapEvaluation(gapId, body),
    onSuccess: () => {
      setDone(true);
      void queryClient.invalidateQueries({
        queryKey: ["evaluations", projectId],
      });
    },
  });

  return (
    <div className="card">
      <div className="meta-row">{meta}</div>
      <h3 style={{ margin: "4px 0 8px" }}>{title}</h3>
      {mutation.isError && <ErrorNote error={mutation.error} />}
      <EvaluationForm
        onSubmit={(b) => mutation.mutate(b)}
        isPending={mutation.isPending}
        isDone={done}
      />
    </div>
  );
}

export function EvaluatePage() {
  const projectId = getActiveProjectId() ?? "";
  const [searchParams] = useSearchParams();
  const focusGapId = searchParams.get("gapId");
  const cohortsQuery = useCohorts(projectId);
  const names = cohortNameMap(cohortsQuery.data);

  const gapsQuery = useQuery({
    queryKey: ["gaps", projectId, "", ""],
    queryFn: () => api.getGaps(projectId),
  });
  const evalQuery = useQuery({
    queryKey: ["evaluations", projectId],
    queryFn: () => api.getEvaluations(projectId),
  });

  const gaps = gapsQuery.data ?? [];
  const ordered = focusGapId
    ? [...gaps].sort((a, b) =>
        a.id === focusGapId ? -1 : b.id === focusGapId ? 1 : 0,
      )
    : gaps;

  return (
    <div>
      <h1>Evaluation mode</h1>
      <p className="subtitle">
        Rate each published gap on five dimensions (1–5), mark whether you would
        accept it into the plan, and add notes.
      </p>

      {evalQuery.isLoading && <Spinner label="Loading calibration…" />}
      {evalQuery.isError && <ErrorNote error={evalQuery.error} />}
      {evalQuery.data && (
        <CalibrationSummary calibration={evalQuery.data.calibration} />
      )}

      <h2>Published gaps</h2>
      {gapsQuery.isLoading && <Spinner />}
      {gapsQuery.isError && <ErrorNote error={gapsQuery.error} />}
      {gapsQuery.isSuccess && ordered.length === 0 && (
        <div className="callout callout-info">No published gaps to evaluate.</div>
      )}
      {ordered.map((gap) => (
        <GapEvaluationRow
          key={gap.id}
          gapId={gap.id}
          title={gap.title}
          meta={
            <>
              <Badge variant={gap.priorityLabel}>
                {gap.priorityLabel.replace(/_/g, " ")}
              </Badge>
              <Badge variant={gap.evidenceStatus}>
                {gap.evidenceStatus.replace(/_/g, " ")}
              </Badge>
              <span className="tag">{gap.gapType}</span>
              <span className="tag">{gap.journeyStage}</span>
              <span className="muted">
                {names.get(gap.cohortId) ?? gap.cohortId}
              </span>
            </>
          }
        />
      ))}
    </div>
  );
}
