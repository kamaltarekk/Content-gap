import { Link } from "react-router-dom";
import type { Gap } from "../types";
import { RANKING_COMPONENT_KEYS } from "../types";
import { Badge, humanize } from "./ui";

export function RankingBreakdown({ gap }: { gap: Gap }) {
  const comp = gap.rankingComponentsJson;
  return (
    <div className="rank-grid">
      {RANKING_COMPONENT_KEYS.map((key) => {
        const value = comp[key] ?? 0;
        const pct = Math.max(0, Math.min(5, value)) * 20;
        return (
          <div className="rank-row" key={key}>
            <span className="rank-label">{humanize(key)}</span>
            <span className="rank-track">
              <span className="rank-fill" style={{ width: `${pct}%` }} />
            </span>
            <span className="rank-value">{value}</span>
          </div>
        );
      })}
      <div className="rank-row" style={{ marginTop: 6 }}>
        <span className="rank-label" style={{ fontWeight: 700 }}>
          Weighted total
        </span>
        <span className="rank-track">
          <span
            className="rank-fill"
            style={{
              width: `${Math.max(0, Math.min(90, gap.priorityScore)) / 0.9}%`,
              background: "var(--green)",
            }}
          />
        </span>
        <span className="rank-value" style={{ fontWeight: 700 }}>
          {gap.priorityScore}/90
        </span>
      </div>
      <p className="field-hint" style={{ marginTop: 8 }}>
        {gap.rankingReason}
      </p>
    </div>
  );
}

export function GapCard({
  gap,
  cohortName,
}: {
  gap: Gap;
  cohortName?: string;
}) {
  return (
    <div className="card">
      <div className="meta-row">
        <Badge variant={gap.priorityLabel}>
          {gap.priorityLabel.replace(/_/g, " ")}
        </Badge>
        <Badge variant={gap.evidenceStatus}>
          {gap.evidenceStatus.replace(/_/g, " ")}
        </Badge>
        <span className="tag">{gap.gapType}</span>
        <span className="tag">{gap.journeyStage}</span>
        <span className="muted">score {gap.priorityScore}</span>
      </div>
      <h3 style={{ margin: "6px 0" }}>
        <Link to={`/gaps/${gap.id}`}>{gap.title}</Link>
      </h3>
      <div className="meta-row">
        <span>Cohort: {cohortName ?? gap.cohortId}</span>
      </div>
      <p className="muted" style={{ margin: "6px 0 0" }}>
        {gap.customerNeed}
      </p>
      <details className="rank-details">
        <summary>Ranking breakdown (10 components)</summary>
        <RankingBreakdown gap={gap} />
      </details>
      <div className="btn-row" style={{ marginTop: 12 }}>
        <Link to={`/gaps/${gap.id}`}>
          <button className="secondary small">View evidence</button>
        </Link>
        <Link to={`/evaluate?gapId=${gap.id}`}>
          <button className="secondary small">Evaluate</button>
        </Link>
      </div>
    </div>
  );
}
