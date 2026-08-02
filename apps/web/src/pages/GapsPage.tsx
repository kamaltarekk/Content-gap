import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { getActiveProjectId } from "../project";
import { JOURNEY_STAGES } from "../types";
import type { JourneyStage } from "../types";
import { cohortNameMap, useCohorts } from "../hooks";
import { GapCard } from "../components/GapCard";
import { ErrorNote, Spinner } from "../components/ui";

export function GapsPage() {
  const projectId = getActiveProjectId() ?? "";
  const [cohortId, setCohortId] = useState<string>("");
  const [journeyStage, setJourneyStage] = useState<string>("");

  const cohortsQuery = useCohorts(projectId);
  const names = cohortNameMap(cohortsQuery.data);

  const gapsQuery = useQuery({
    queryKey: ["gaps", projectId, cohortId, journeyStage],
    queryFn: () =>
      api.getGaps(projectId, {
        cohortId: cohortId || undefined,
        journeyStage: (journeyStage || undefined) as JourneyStage | undefined,
      }),
  });

  const topGaps = (gapsQuery.data ?? []).slice(0, 10);

  return (
    <div>
      <h1>Top content gaps</h1>
      <p className="subtitle">
        Ranked by priority score. Showing up to 10. Analysis runs automatically
        on ingestion — there is no manual run button.
      </p>

      <div className="filters">
        <div className="filter-field">
          <label htmlFor="cohort-filter">Cohort</label>
          <select
            id="cohort-filter"
            value={cohortId}
            onChange={(e) => setCohortId(e.target.value)}
          >
            <option value="">All cohorts</option>
            {(cohortsQuery.data ?? []).map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>
        <div className="filter-field">
          <label htmlFor="stage-filter">Journey stage</label>
          <select
            id="stage-filter"
            value={journeyStage}
            onChange={(e) => setJourneyStage(e.target.value)}
          >
            <option value="">All stages</option>
            {JOURNEY_STAGES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
      </div>

      {gapsQuery.isLoading && <Spinner />}
      {gapsQuery.isError && <ErrorNote error={gapsQuery.error} />}
      {gapsQuery.isSuccess && topGaps.length === 0 && (
        <div className="callout callout-info">
          No published gaps yet. Once sources are ingested, analysis runs
          automatically and gaps will appear here.
        </div>
      )}
      {topGaps.map((gap) => (
        <GapCard key={gap.id} gap={gap} cohortName={names.get(gap.cohortId)} />
      ))}
    </div>
  );
}
