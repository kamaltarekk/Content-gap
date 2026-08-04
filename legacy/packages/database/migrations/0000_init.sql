-- Content Gap Intelligence v0 — initial schema. Idempotent where practical.
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS projects (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name              text NOT NULL,
  primary_domain    text NOT NULL,
  default_language  text NOT NULL DEFAULT 'en',
  status            text NOT NULL DEFAULT 'ACTIVE',
  refresh_schedule  jsonb NOT NULL DEFAULT '{"dayOfWeek":1,"hourUtc":6}'::jsonb,
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS project_tokens (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id    uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  token_hash    text NOT NULL UNIQUE,
  label         text NOT NULL,
  last_used_at  timestamptz,
  expires_at    timestamptz,
  created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS business_briefs (
  id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id            uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  version               integer NOT NULL DEFAULT 1,
  structured_data_json  jsonb NOT NULL,
  markdown_notes        text NOT NULL DEFAULT '',
  is_active             boolean NOT NULL DEFAULT true,
  created_at            timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS offers (
  id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id            uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  name                  text NOT NULL,
  mechanism             text NOT NULL DEFAULT '',
  desired_action        text NOT NULL DEFAULT '',
  approved_claims_json  jsonb NOT NULL DEFAULT '[]'::jsonb,
  prohibited_claims_json jsonb NOT NULL DEFAULT '[]'::jsonb,
  proof_json            jsonb NOT NULL DEFAULT '[]'::jsonb,
  constraints_json      jsonb NOT NULL DEFAULT '[]'::jsonb,
  created_at            timestamptz NOT NULL DEFAULT now(),
  updated_at            timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cohorts (
  id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id            uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  name                  text NOT NULL,
  role_identity         text NOT NULL DEFAULT '',
  commercial_situation  text NOT NULL DEFAULT '',
  trigger               text NOT NULL DEFAULT '',
  active_problem        text NOT NULL DEFAULT '',
  current_workflow      text NOT NULL DEFAULT '',
  current_belief        text NOT NULL DEFAULT '',
  desired_outcome       text NOT NULL DEFAULT '',
  objections_json       jsonb NOT NULL DEFAULT '[]'::jsonb,
  decision_criteria_json jsonb NOT NULL DEFAULT '[]'::jsonb,
  priority              integer NOT NULL DEFAULT 3,
  offer_fit             text NOT NULL DEFAULT '',
  exclusion_criteria_json jsonb NOT NULL DEFAULT '[]'::jsonb,
  exact_language_json   jsonb NOT NULL DEFAULT '[]'::jsonb,
  created_at            timestamptz NOT NULL DEFAULT now(),
  updated_at            timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sources (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id        uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  owner_type        text NOT NULL,
  competitor_slot   integer,
  source_type       text NOT NULL,
  name              text NOT NULL,
  canonical_url     text,
  crawl_method      text NOT NULL DEFAULT 'HTTP',
  refresh_enabled   boolean NOT NULL DEFAULT true,
  refresh_interval  text NOT NULL DEFAULT 'WEEKLY',
  last_success_at   timestamptz,
  last_failure_at   timestamptz,
  status            text NOT NULL DEFAULT 'PENDING',
  error_message     text,
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS source_snapshots (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id           uuid NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
  content_hash        text NOT NULL,
  raw_content         text NOT NULL,
  normalized_content  text NOT NULL,
  metadata_json       jsonb NOT NULL DEFAULT '{}'::jsonb,
  captured_at         timestamptz NOT NULL DEFAULT now(),
  is_current          boolean NOT NULL DEFAULT true
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_snapshot_source_hash ON source_snapshots(source_id, content_hash);

CREATE TABLE IF NOT EXISTS content_units (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id          uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  source_snapshot_id  uuid NOT NULL REFERENCES source_snapshots(id) ON DELETE CASCADE,
  title               text NOT NULL DEFAULT '',
  body                text NOT NULL,
  language            text NOT NULL DEFAULT 'unknown',
  published_at        date,
  asset_type          text NOT NULL DEFAULT 'UNKNOWN',
  platform            text,
  url                 text,
  metadata_json       jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at          timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chunks (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  content_unit_id   uuid NOT NULL REFERENCES content_units(id) ON DELETE CASCADE,
  chunk_index       integer NOT NULL,
  text              text NOT NULL,
  start_offset      integer NOT NULL,
  end_offset        integer NOT NULL,
  embedding         vector(384),
  token_count       integer NOT NULL DEFAULT 0,
  created_at        timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_chunks_unit ON chunks(content_unit_id);

CREATE TABLE IF NOT EXISTS extracted_signals (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id          uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  content_unit_id     uuid NOT NULL REFERENCES content_units(id) ON DELETE CASCADE,
  chunk_id            uuid REFERENCES chunks(id) ON DELETE SET NULL,
  signal_type         text NOT NULL,
  normalized_label    text NOT NULL,
  raw_text            text NOT NULL,
  structured_data_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  cohort_id           uuid REFERENCES cohorts(id) ON DELETE SET NULL,
  journey_stage       text NOT NULL DEFAULT 'UNKNOWN',
  evidence_weight     integer NOT NULL DEFAULT 1,
  created_at          timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS decision_needs (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id        uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  cohort_id         uuid NOT NULL REFERENCES cohorts(id) ON DELETE CASCADE,
  journey_stage     text NOT NULL,
  need_type         text NOT NULL,
  normalized_need   text NOT NULL,
  description       text NOT NULL DEFAULT '',
  evidence_json     jsonb NOT NULL DEFAULT '[]'::jsonb,
  created_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS coverage_cells (
  id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id            uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  cohort_id             uuid NOT NULL REFERENCES cohorts(id) ON DELETE CASCADE,
  journey_stage         text NOT NULL,
  need_type             text NOT NULL,
  normalized_need       text NOT NULL,
  coverage_status       text NOT NULL,
  coverage_strength     integer NOT NULL DEFAULT 0,
  supporting_asset_count integer NOT NULL DEFAULT 0,
  effective_asset_count integer NOT NULL DEFAULT 0,
  evidence_json         jsonb NOT NULL DEFAULT '[]'::jsonb,
  updated_at            timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS gap_candidates (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id        uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  run_id            uuid,
  cohort_id         uuid REFERENCES cohorts(id) ON DELETE SET NULL,
  journey_stage     text NOT NULL,
  gap_type          text NOT NULL,
  title             text NOT NULL,
  candidate_data_json jsonb NOT NULL,
  generation_reason text NOT NULL DEFAULT '',
  status            text NOT NULL DEFAULT 'CANDIDATE',
  rejection_reason  text,
  priority_score    integer NOT NULL DEFAULT 0,
  priority_label    text NOT NULL DEFAULT 'P5_REJECT',
  is_shadow_sample  boolean NOT NULL DEFAULT false,
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS gaps (
  id                        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id                uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  gap_candidate_id          uuid REFERENCES gap_candidates(id) ON DELETE SET NULL,
  run_id                    uuid,
  cohort_id                 uuid REFERENCES cohorts(id) ON DELETE SET NULL,
  journey_stage             text NOT NULL,
  gap_type                  text NOT NULL,
  title                     text NOT NULL,
  customer_need             text NOT NULL DEFAULT '',
  current_coverage_summary  text NOT NULL DEFAULT '',
  missing_decision_support  jsonb NOT NULL DEFAULT '[]'::jsonb,
  commercial_consequence    text NOT NULL DEFAULT '',
  recommended_content_role  text NOT NULL DEFAULT 'VALUE',
  recommended_asset_type    text NOT NULL DEFAULT 'ARTICLE',
  suggested_touchpoint      text NOT NULL DEFAULT '',
  evidence_status           text NOT NULL DEFAULT 'HYPOTHESIS',
  evidence_status_rule      text NOT NULL DEFAULT '',
  priority_label            text NOT NULL DEFAULT 'P4_MONITOR',
  priority_score            integer NOT NULL DEFAULT 0,
  ranking_components_json    jsonb NOT NULL DEFAULT '{}'::jsonb,
  ranking_reason            text NOT NULL DEFAULT '',
  status                    text NOT NULL DEFAULT 'PUBLISHED',
  created_at                timestamptz NOT NULL DEFAULT now(),
  updated_at                timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS gap_evidence (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  gap_id              uuid NOT NULL REFERENCES gaps(id) ON DELETE CASCADE,
  source_id           uuid REFERENCES sources(id) ON DELETE SET NULL,
  source_snapshot_id  uuid REFERENCES source_snapshots(id) ON DELETE SET NULL,
  content_unit_id     uuid REFERENCES content_units(id) ON DELETE SET NULL,
  chunk_id            uuid REFERENCES chunks(id) ON DELETE SET NULL,
  evidence_role       text NOT NULL,
  exact_quote         text NOT NULL,
  quote_start_offset  integer NOT NULL,
  quote_end_offset    integer NOT NULL,
  created_at          timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS evaluations (
  id                          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  gap_id                      uuid REFERENCES gaps(id) ON DELETE CASCADE,
  gap_candidate_id            uuid REFERENCES gap_candidates(id) ON DELETE CASCADE,
  evaluator_name              text NOT NULL,
  validity_rating             integer NOT NULL,
  commercial_relevance_rating integer NOT NULL,
  novelty_rating              integer NOT NULL,
  evidence_quality_rating     integer NOT NULL,
  actionability_rating        integer NOT NULL,
  accepted_into_plan          boolean NOT NULL DEFAULT false,
  marked_missed_valid_gap     boolean NOT NULL DEFAULT false,
  notes                       text NOT NULL DEFAULT '',
  created_at                  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS outcomes (
  id                        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  gap_id                    uuid NOT NULL REFERENCES gaps(id) ON DELETE CASCADE,
  addressed                 boolean NOT NULL DEFAULT false,
  content_asset_url         text,
  publication_date          date,
  entered_content_plan      boolean NOT NULL DEFAULT false,
  qualified_conversations_before integer,
  qualified_conversations_after  integer,
  conversion_observations   text,
  objection_frequency_before integer,
  objection_frequency_after  integer,
  qualitative_outcome       text,
  outcome_notes             text,
  created_at                timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS analysis_runs (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id        uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  trigger_type      text NOT NULL,
  status            text NOT NULL DEFAULT 'QUEUED',
  pipeline_version  text NOT NULL,
  started_at        timestamptz,
  completed_at      timestamptz,
  error_summary     text,
  stage_log_json    jsonb NOT NULL DEFAULT '[]'::jsonb,
  input_counts_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  output_counts_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  usage_json        jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS usage_events (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id        uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  run_id            uuid REFERENCES analysis_runs(id) ON DELETE SET NULL,
  provider          text NOT NULL,
  model             text NOT NULL,
  operation         text NOT NULL,
  input_tokens      integer NOT NULL DEFAULT 0,
  output_tokens     integer NOT NULL DEFAULT 0,
  estimated_cost    numeric(12,6) NOT NULL DEFAULT 0,
  created_at        timestamptz NOT NULL DEFAULT now()
);
