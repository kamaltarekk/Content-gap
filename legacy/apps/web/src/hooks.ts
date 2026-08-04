import { useQuery } from "@tanstack/react-query";
import { api } from "./api";
import type { Cohort } from "./types";

export function useCohorts(projectId: string) {
  return useQuery({
    queryKey: ["cohorts", projectId],
    queryFn: () => api.getCohorts(projectId),
  });
}

/** Build a cohortId -> name lookup from a cohort list. */
export function cohortNameMap(cohorts: Cohort[] | undefined): Map<string, string> {
  const map = new Map<string, string>();
  for (const c of cohorts ?? []) {
    map.set(c.id, c.name);
  }
  return map;
}
