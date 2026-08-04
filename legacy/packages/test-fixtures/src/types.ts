import type { BusinessBrief, Cohort, Offer, OwnerType, ProjectCreate, VocRow } from "@cgi/shared";

export interface DemoAsset {
  ownerType: OwnerType;
  competitorSlot: number | null;
  name: string;
  url: string;
  title: string;
  text: string;
  publishedAt?: string; // ISO date, used to plant an OUTDATED asset
}

export interface DemoDataset {
  project: ProjectCreate;
  brief: BusinessBrief;
  offer: Offer;
  cohorts: Cohort[];
  ownedAssets: DemoAsset[];
  vocRows: VocRow[];
  competitorAssets: DemoAsset[];
}
