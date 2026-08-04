import { useState } from "react";
import type { ReactNode } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { getActiveProjectId } from "../project";
import type { EvaluationBody } from "../types";
import { cohortNameMap, useCohorts } from "../hooks";
import { EvaluationForm } from "../components/EvaluationForm";
import { ErrorNote, Spinner } from "../components/ui";

function ShadowRow({
  candidateId,
  title,
  meta,
}: {
  candidateId: string;
  title: string;
  meta: ReactNode;
}) {
  const [done, setDone] = useState(false);
  const mutation = useMutation({
    mutationFn: (body: EvaluationBody) =>
      api.createCandidateEvaluation(candidateId, body),
    onSuccess: () => setDone(true),
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
        showMissedValidGap
      />
    </div>
  );
}

export function ShadowPage() {
  const projectId = getActiveProjectId() ?? "";
  const cohortsQuery = useCohorts(projectId);
  const names = cohortNameMap(cohortsQuery.data);

  const shadowQuery = useQuery({
    queryKey: ["shadow", projectId],
    queryFn: () => api.getShadowSample(projectId),
  });

  return (
    <div>
      <h1>Shadow sample</h1>
      <p className="subtitle">
        A blind sample of rejected candidates. Original rank is hidden. Evaluate
        each on its own merits and flag any that should not have been rejected.
      </p>

      {shadowQuery.isLoading && <Spinner />}
      {shadowQuery.isError && <ErrorNote error={shadowQuery.error} />}
      {shadowQuery.isSuccess && shadowQuery.data.length === 0 && (
        <div className="callout callout-info">
          No shadow candidates available.
        </div>
      )}
      {(shadowQuery.data ?? []).map((cand) => (
        <ShadowRow
          key={cand.id}
          candidateId={cand.id}
          title={cand.title}
          meta={
            <>
              <span className="tag">{cand.gapType}</span>
              <span className="tag">{cand.journeyStage}</span>
              <span className="muted">
                {names.get(cand.cohortId) ?? cand.cohortId}
              </span>
              <span className="badge badge-neutral">
                rejected: {cand.rejectionReason}
              </span>
            </>
          }
        />
      ))}
    </div>
  );
}
