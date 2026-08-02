import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { getActiveProjectId } from "../project";
import { cohortNameMap, useCohorts } from "../hooks";
import { RankingBreakdown } from "../components/GapCard";
import { Badge, BulletList, ErrorNote, Spinner } from "../components/ui";

export function GapDetailPage() {
  const { gapId } = useParams<{ gapId: string }>();
  const projectId = getActiveProjectId() ?? "";
  const cohortsQuery = useCohorts(projectId);
  const names = cohortNameMap(cohortsQuery.data);

  const gapQuery = useQuery({
    queryKey: ["gap", gapId],
    queryFn: () => api.getGap(gapId ?? ""),
    enabled: Boolean(gapId),
  });

  if (gapQuery.isLoading) return <Spinner />;
  if (gapQuery.isError) return <ErrorNote error={gapQuery.error} />;
  const gap = gapQuery.data;
  if (!gap) return <ErrorNote error={new Error("Gap not found")} />;

  return (
    <div>
      <p>
        <Link to="/">← Back to gaps</Link>
      </p>
      <div className="meta-row">
        <Badge variant={gap.priorityLabel}>
          {gap.priorityLabel.replace(/_/g, " ")}
        </Badge>
        <Badge variant={gap.evidenceStatus}>
          {gap.evidenceStatus.replace(/_/g, " ")}
        </Badge>
        <span className="tag">{gap.gapType}</span>
        <span className="tag">{gap.journeyStage}</span>
      </div>
      <h1>{gap.title}</h1>
      <p className="subtitle">
        Cohort: {names.get(gap.cohortId) ?? gap.cohortId} · Score{" "}
        {gap.priorityScore}/90
      </p>

      <div className="card">
        <h3>Customer need</h3>
        <p>{gap.customerNeed}</p>
        <h3 style={{ marginTop: 12 }}>Current coverage</h3>
        <p className="muted">{gap.currentCoverageSummary}</p>
      </div>

      <div className="card">
        <h3>Missing decision support</h3>
        <BulletList items={gap.missingDecisionSupport} />
        <h3 style={{ marginTop: 12 }}>Commercial consequence</h3>
        <p>{gap.commercialConsequence}</p>
      </div>

      <div className="card">
        <h3>Recommendation</h3>
        <div className="meta-row">
          <span className="tag">Role: {gap.recommendedContentRole}</span>
          <span className="tag">Asset: {gap.recommendedAssetType}</span>
          <span className="tag">Touchpoint: {gap.suggestedTouchpoint}</span>
        </div>
      </div>

      <div className="card">
        <h3>Evidence quotes</h3>
        {gap.evidence.length === 0 && (
          <p className="muted">
            No exact-quote evidence attached (evidence status:{" "}
            {gap.evidenceStatus}).
          </p>
        )}
        {gap.evidence.map((ev, i) => (
          <div className="source-list-item" key={`${ev.chunkId}-${i}`}>
            <div>
              <span className="tag">{ev.evidenceRole}</span>
              <blockquote
                style={{
                  margin: "6px 0 0",
                  borderLeft: "3px solid var(--border)",
                  paddingLeft: 10,
                }}
              >
                “{ev.exactQuote}”
              </blockquote>
              <span className="field-hint mono">
                source {ev.sourceId.slice(0, 8)} · offset {ev.quoteStartOffset}–
                {ev.quoteEndOffset}
              </span>
            </div>
          </div>
        ))}
      </div>

      <div className="card">
        <h3>Priority ranking</h3>
        <p className="field-hint">{gap.evidenceStatusRule}</p>
        <RankingBreakdown gap={gap} />
      </div>

      <div className="btn-row">
        <Link to={`/evaluate?gapId=${gap.id}`}>
          <button>Open evaluation form</button>
        </Link>
      </div>
    </div>
  );
}
