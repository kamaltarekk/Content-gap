// Backend response shapes used by the side panel. These mirror the @cgi/api routes.

export interface Gap {
  id: string;
  gapType: string;
  title: string;
  cohortId: string | null;
  journeyStage: string;
  evidenceStatus: string;
  priorityLabel: string;
  priorityScore: number;
  rankingReason: string;
}

export interface Source {
  id: string;
  name: string;
  ownerType: string;
  status: string;
}

export interface SourcesResponse {
  pending: Source[];
  processed: Source[];
  failed: Source[];
  needsAttention: Source[];
  all: Source[];
}

export type OwnerType = "OWNED" | "COMPETITOR" | "VOC";

export interface OwnerOption {
  label: string;
  ownerType: OwnerType;
  competitorSlot: 1 | 2 | 3 | null;
}

export const OWNER_OPTIONS: OwnerOption[] = [
  { label: "Owned", ownerType: "OWNED", competitorSlot: null },
  { label: "Competitor 1", ownerType: "COMPETITOR", competitorSlot: 1 },
  { label: "Competitor 2", ownerType: "COMPETITOR", competitorSlot: 2 },
  { label: "Competitor 3", ownerType: "COMPETITOR", competitorSlot: 3 },
  { label: "Voice of Customer", ownerType: "VOC", competitorSlot: null },
];
