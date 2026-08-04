# Phase 3 — Evidence System — COMPLETE ✅

## Deliverables
- **Sources**: manual text, file upload (PDF/DOCX/TXT/MD), and CSV preview + import
  (`app/api/sources.py`). URL source creation deferred to Phase 4 (crawling is a background job).
- **Immutable source snapshots** with raw SHA-256, normalized-text SHA-256, object keys, parser
  name/version, extraction quality, status, warnings, metadata, unique `(source_id, snapshot_number)`
  and `(source_id, raw_sha256)`.
- **Parsers** (`app/parsers/`): TXT/Markdown, CSV (UTF-8 + UTF-8-BOM, Arabic headers), PDF
  (embedded-text-first via pypdf; image-only/empty pages surfaced, **no OCR, no silent empty
  success**), DOCX (python-docx). Extraction quality ∈ complete/partial/low_quality/unreadable +
  warnings.
- **Content-piece extraction**: one piece per document; one piece per CSV row (multi-record).
- **Verbatim evidence spans**: a full-text span per piece with real offsets + `source_location`
  linking back to the snapshot (`created_by_origin=deterministic`).
- **Object storage** (`app/clients/storage.py`): `Storage` protocol with a local-filesystem
  backend (dev/tests) and a MinIO/S3 backend (canonical). Readiness check now uses it.
- **Text utilities** (`app/core/text.py`): normalization (NFKC + whitespace collapse + BOM/bidi
  strip) kept **separate** from the byte-for-byte original; content hashing; language detection.
- **Duplicate grouping**: normalized-content hash groups exact + whitespace-only reposts; both
  originals retained, one canonical, `duplicate_group_id` shared; `/duplicates` endpoint.
- **Content & evidence API**: list/get content, list evidence, `evidence/{id}/source-context`
  (surrounding text + snapshot/source, scoped to the piece); `/sources`, `/sources/{id}`.
- **Migration `0003`**: sources, source_snapshots, content_pieces (+ hash/entity indexes),
  evidence_spans (+ offset CHECK).
- **Content inventory UI** (`frontend/src/pages/Content.tsx`): list pieces → open evidence span →
  trace to the exact source snapshot.

## Tests run (offline, local Postgres :5433, local file storage)
```
backend:  uv run pytest -q            → 33 passed  (Phase 0–2 carried + Phase 3 below)
          - CSV with 20 rows → 1 source, 1 snapshot, 20 content pieces
          - Arabic UTF-8-BOM CSV with Arabic headers → mapped import, verbatim Arabic
          - partial PDF (text + blank page) → extraction_quality=partial + image_only warning
          - image-only PDF → unreadable, NOT complete, 0 fabricated pieces
          - unsupported MIME → 422 UNSUPPORTED_FILE_TYPE; manual text >10k chars → 422
          - exact + near (whitespace) duplicates grouped; both originals accessible; one canonical
          - source→evidence trace: piece → evidence span → source-context → exact snapshot;
            original_text and normalized_text are separate
          - migration upgrade/downgrade now spans 0001–0003
backend:  ruff check + format         → All checks passed
frontend: typecheck / build           → clean; production build succeeds
```

## Acceptance gate — PASS
- ✅ Open a content piece → view an evidence span → navigate to the exact source snapshot and
  location (verified via API and the Content UI).
- ✅ Original and normalized text are stored and returned **separately**; the verbatim quote is
  preserved (Arabic never rewritten).

## Deviations (recorded)
- Small files are parsed **inline** in the request in Phase 3; Phase 4 moves parsing/crawling to
  Celery jobs (spec §6.5). Object storage `put` is synchronous (fine for the local backend; the
  MinIO path also moves under jobs in Phase 4).
- URL source creation + limited website collection land in Phase 4 alongside the job system.

## Next
Phase 4 — Job System: Celery workers, persistent job + events model, progress UI, cancellation,
retry policy (safe-retry vs timeout), dead-letter view, idempotency keys. Gate: parsing/long tasks
continue after the browser closes, report accurate progress, and never duplicate paid/mutating work.
