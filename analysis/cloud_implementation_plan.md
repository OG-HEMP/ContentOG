# Cloud Implementation Plan (Client Rollout)

This plan turns the current script-based ContentOG pipeline into a production-grade cloud service.

## 1) Recommended service stack (opinionated)

### Primary recommendation: **Google Cloud + Supabase**
Use this as the default implementation path.

- **Database**: keep **Supabase Postgres + pgvector** (already aligned with current env setup).
- **Compute**: **Cloud Run Jobs** for pipeline execution (`scripts/run_worker.py`).
- **Scheduling**: **Cloud Scheduler** to trigger Cloud Run Job runs.
- **Queueing / fan-out**: **Pub/Sub** for per-keyword or per-job dispatch.
- **Secrets**: **Google Secret Manager** (inject at runtime into Cloud Run Jobs).
- **Observability**: **Cloud Logging + Error Reporting + Cloud Monitoring**.
- **Artifact/storage**: **Cloud Storage** for optional run artifacts and exports.
- **CI/CD**: **GitHub Actions** for test/build/deploy gates.

Why this fits current codebase:
- Worker entrypoint already exists and can be containerized directly.
- Scheduling intervals are already defined in config and can map to Scheduler jobs.
- Preflight/bootstrap scripts can be promoted to controlled cloud jobs.

### Secondary options (if client constraints require)
- **AWS**: ECS Fargate + EventBridge Scheduler + SQS + Secrets Manager + CloudWatch.
- **Azure**: Container Apps Jobs + Azure Scheduler equivalent + Service Bus + Key Vault + App Insights.
- **Render/Railway** (fastest MVP): Cron Jobs + managed services, but weaker enterprise controls than GCP/AWS.

---

## 2) Target cloud architecture (v1)

- `scheduler-industry` (monthly) -> trigger `contentog-worker` job with mode `industry`.
- `scheduler-competitor` (weekly) -> trigger `contentog-worker` job with mode `competitor`.
- `scheduler-site` (weekly) -> trigger `contentog-worker` job with mode `site`.
- `contentog-worker`:
  - Reads secrets and runtime config.
  - Runs preflight checks (lightweight mode for production runs).
  - Loads seed keywords and submits per-keyword tasks to Pub/Sub (optional in v1).
- `contentog-keyword-worker` (optional v1.1):
  - Consumes Pub/Sub message.
  - Runs pipeline for one keyword.
  - Writes outputs to Supabase.
- Monitoring and alerts:
  - Alerts on failed job runs, elevated error rate, and provider failures.

---

## 3) Implementation phases (bulletproof rollout)

## Phase 0 — Production readiness decisions (1-2 days)
- Confirm cloud provider (default GCP).
- Define environment separation: `dev`, `staging`, `prod`.
- Confirm SLOs:
  - Job success rate target (e.g., >= 99%).
  - Max end-to-end latency per keyword.
  - Max tolerated data staleness.
- Define budget guardrails (monthly cap, per-run cap).

**Exit criteria**
- Signed architecture decision record (ADR).
- Named service owners and on-call contacts.

## Phase 1 — Containerize and harden runtime (2-3 days)
- Add Dockerfile for worker runtime.
- Add startup modes:
  - `preflight`
  - `bootstrap`
  - `worker`
  - `single-keyword`
- Standardize structured JSON logs.
- Add timeout controls and max-retry policy per provider call.

**Exit criteria**
- Container runs locally and in staging job runner.
- All entrypoint modes documented and tested.

## Phase 2 — Secrets and config management (1-2 days)
- Move all sensitive env vars to Secret Manager.
- Keep non-sensitive config in environment or config file.
- Enforce startup validation of required secrets per mode.

**Exit criteria**
- No plaintext production secrets in repo or CI vars.
- Secret rotation runbook completed.

## Phase 3 — Scheduled execution (2 days)
- Create three Cloud Scheduler jobs mapped to intervals.
- Map scheduler payload -> run mode and keyword set.
- Add idempotency run key: `run_id = <mode>-<yyyy-mm-dd>`.

**Exit criteria**
- Schedulers trigger jobs successfully in staging.
- Duplicate schedule triggers do not create duplicate records.

## Phase 4 — Scale-out orchestration (3-5 days)
- Introduce Pub/Sub queue for keyword-level tasks.
- Limit concurrency to provider quotas (SerpApi/OpenAI/crawl).
- Add dead-letter topic and retry policy.

**Exit criteria**
- Parallel keyword processing enabled.
- Poison messages land in DLQ with replay workflow.

## Phase 5 — Observability and alerting (2-3 days)
- Add correlation IDs: `run_id`, `keyword`, `agent`.
- Emit metrics:
  - `pipeline_runs_total`
  - `pipeline_failures_total`
  - `keyword_duration_seconds`
  - `provider_error_total{provider=*}`
- Configure alerts:
  - Job failure > 0 in 15m.
  - Error rate > threshold.
  - Missing expected scheduled run.

**Exit criteria**
- Dashboard exists for run health and throughput.
- Alert routing tested end-to-end.

## Phase 6 — Security and compliance controls (2-4 days)
- Enforce least-privilege IAM for jobs and scheduler.
- Restrict network egress if required by client policy.
- Add audit logs for secret access and deployments.
- Define data retention and deletion policy for crawled content.

**Exit criteria**
- Security checklist approved by client.
- Access model documented.

## Phase 7 — CI/CD and release safety (2-3 days)
- Build pipeline:
  - lint/type/unit tests
  - container build
  - deploy to staging
  - smoke run
  - manual approval for prod
- Add rollback command and previous-image pinning.

**Exit criteria**
- One-click rollback tested.
- Production deploy runbook approved.

---

## 4) Required product/engineering changes in app code

- Introduce runtime mode selector in worker script.
- Add run metadata table (or run columns) to track:
  - `run_id`, `mode`, `status`, `started_at`, `ended_at`, `error_summary`.
- Ensure strict idempotency keys for:
  - keyword discovery events
  - article URL inserts
  - topic/strategy generation snapshots
- Add export endpoint/job for downstream consumption (CSV/JSON in storage).
- Add health-check command that does not execute expensive external calls.

---

## 5) Risk register and mitigations

- **Provider rate limits** (SerpApi/OpenAI):
  - Mitigation: token bucket + bounded concurrency + exponential backoff.
- **Crawler variability / blocked domains**:
  - Mitigation: fallback crawler provider + per-domain retry caps.
- **Duplicate schedules/retries**:
  - Mitigation: run-level idempotency keys and upsert-only writes.
- **Cost overrun**:
  - Mitigation: hard keyword caps per run + budget alerts + daily spend checks.
- **Silent data quality drift**:
  - Mitigation: data quality checks (minimum article/content thresholds per run).

---

## 6) Service recommendation summary (what to pick now)

Pick **GCP Cloud Run Jobs + Cloud Scheduler + Pub/Sub + Secret Manager**, keep **Supabase Postgres**.

This gives:
- Fastest path from current scripts to production jobs.
- Strong operational controls and observability.
- Clean future path to scale keyword workloads horizontally.

---

## 7) 30-day delivery plan

- **Week 1**: Phase 0-1 (decisions, containerization, mode hardening).
- **Week 2**: Phase 2-3 (secrets + scheduled production-like runs in staging).
- **Week 3**: Phase 4-5 (queue orchestration + dashboards/alerts).
- **Week 4**: Phase 6-7 (security hardening + CI/CD + production go-live).

**Go-live gate (must pass all):**
- 7 consecutive scheduled staging runs with no critical failures.
- Alert tests successful.
- Rollback test successful.
- Client sign-off on security and cost controls.
