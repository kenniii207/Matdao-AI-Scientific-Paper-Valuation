# PRD — MatDAO Evaluation Pipeline Improvements (v2.1)

## 1) Context

MatDAO upload/evaluation flow now supports:
- PDF/ocr extraction
- multi-source enrichment (OpenAlex, Semantic Scholar, SerpAPI Scholar)
- LLM synthesis + 9-dimension scoring with integrity gate

Recent user feedback highlighted:
- occasional generic insights across different papers
- need for lower resource usage on Render
- need for stronger observability and controlled rollouts

This PRD defines the next execution plan and immediate implementation scope.

## 2) Product Goals

1. Increase paper-specific output quality (less generic insight/warnings).
2. Improve runtime stability under partial API failures.
3. Reduce repeated compute/API work via caching.
4. Keep default resource profile safe for Render (feature flags + conservative defaults).
5. Preserve governance integrity gate behavior (Dim9 gate remains unchanged).

## 3) Non-Goals

- No mandatory GPU requirement.
- No full rearchitecture of scoring engine.
- No override of integrity gate logic.
- No expensive always-on reranking at large scale by default.

## 4) Success Metrics

### Quality
- Drop in repeated generic insight rate across recent evaluations.
- Increase in evidence-grounded outputs (insight/warnings traceable to snippets + curated candidates).

### Reliability
- Reduced enrichment hard-fail rate.
- Graceful fallback behavior under API timeout/error scenarios.

### Performance/Cost
- Lower p95 latency for repeated/similar papers due to cache hits.
- Stable memory/CPU usage under concurrent uploads.

### Operability
- Per-stage timing visibility for extract, enrich, local_prefilter, and llm stages.
- Source health counters visible in processed metadata/logs.

## 5) Constraints

- Must support Render backend resource constraints.
- Heavy retrieval/reranking must be feature-flagged off by default.
- Must maintain auditability (`origin_snippet` and rationale trails).

## 6) Rollout Principles

1. Ship behind feature flags where cost risk exists.
2. Start with conservative defaults.
3. Capture telemetry before widening.
4. Keep deterministic fallback paths.

---

## 7) Immediate Priority Scope (Now)

Execute:
- **Phase A** (Observability + Guardrails)
- **Phase C (1,3)** (Cache external responses + cache curated top-k)
- **Phase B (2)** (Deduplicate similar candidates)

### 7.1 Phase A — Observability + Guardrails

#### A1. Structured stage timing
Capture and persist timing for:
- extraction stage
- enrichment stage
- local prefilter/rerank stage (if enabled)
- llm evaluation stage

#### A2. Source health counters
Track source-level health for enrichment calls:
- per source success/error counters
- include in enrichment metadata for downstream debugging

#### A3. Generic output detector
Detect likely-generic LLM outputs:
- repeated/boilerplate patterns
- attach quality signal metadata for monitoring and review

#### A4. Hard timeout budget
Add total budget for enrich+llm evaluation path:
- timeout must not crash pipeline
- fallback to partial metadata and neutral/default scoring behavior
- preserve explicit status/error context for operators

### 7.2 Phase C — Caching (items 1 and 3)

#### C1. External response cache
TTL cache keyed by DOI/query/source for:
- OpenAlex DOI lookup
- Semantic Scholar DOI lookup
- theme search results

#### C3. Curated top-k cache
Cache final local curated candidates keyed by paper/query fingerprint:
- reused across repeated runs
- avoids repeated embedding/rerank compute

### 7.3 Phase B — Retrieval quality (item 2)

#### B2. Candidate deduplication
Deduplicate semantically similar results from multiple sources:
- normalize title/text keys
- keep best-ranked/source-diverse candidate set

---

## 8) Functional Requirements

1. Feature flags must control local prefilter/reranker behavior.
2. Cache TTL and bounds must be configurable.
3. Enrichment metadata must include:
   - source errors
   - source health snapshot
   - cache hit/miss signals
   - local retrieval summary when enabled
4. Evaluation metadata must include:
   - stage timings
   - timeout markers
   - generic-output quality signal

## 9) Technical Requirements

- In-memory TTL cache (lightweight, no external cache dependency).
- Thread-safe access for async paths.
- No blocking heavy model load when feature flags disabled.
- Model loading done lazily for local retrieval phase.

## 10) Testing Requirements

Add/extend tests for:
- candidate dedup logic
- embedding prefilter ordering
- reranker reorder behavior
- cache hit behavior for curated candidates
- graceful behavior when no candidates available
- full backend test suite pass (`pytest backend/tests/ -v`)

## 11) Operational Review Checklist

Before release:
1. Verify defaults keep heavy features off.
2. Verify timeout fallback path still returns scoring result safely.
3. Verify no regression in integrity gate tests.
4. Validate stage timings/health fields are present in processed metadata.
5. Confirm test suite passes.

## 12) Future Backlog (Post-Now)

- Phase D robustness pass (schema repair, calibration consistency checks).
- Human-in-the-loop queue for low-confidence evaluations.
- Persisted/shared cache backend if volume warrants (Redis/DB).
- Ranking quality calibration dataset for domain-specific reranker selection.

## 13) Owner + Execution

Owner: Backend pipeline team  
Execution mode: phased, flags-first, metrics-informed rollout  
Commit policy: atomic commits with `feat:/fix:/test:/docs:/chore:` prefixes
