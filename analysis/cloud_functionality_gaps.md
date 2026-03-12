# Cloud Functionality Gaps (Non-UI)

This document summarizes functional gaps for cloud readiness based on the current repository implementation.

## 1) No cloud runtime/deployment packaging
- The repo defines Python dependencies and runtime version, but does not include deployment manifests (for example Dockerfile, Procfile, or IaC), so cloud runtime provisioning is not yet codified.

## 2) No hosted API/service layer
- Current entrypoints are worker/pipeline scripts; there is no API server layer for triggering runs, querying results, or exposing health endpoints.

## 3) Scheduling is documented, not implemented as cloud scheduler config
- Intervals are defined in config and workflow docs, but there is no cloud scheduler binding/crontab configuration in-repo.

## 4) Pipeline is synchronous and keyword-loop based
- Pipeline runs sequentially over keywords in one process.
- There is no queue/worker orchestration for scalable parallel processing.

## 5) Worker is fixed-sample by default
- Worker defaults to 3 seed keywords and reads from local seed file, which is useful for smoke runs but not full production discovery breadth.

## 6) No robust operational controls
- No explicit dead-letter/retry queue policy, checkpointing, or resumable job state is implemented for long-running cloud jobs.

## 7) Observability is basic
- Logging is configured, but there is no structured telemetry/metrics/tracing export integration for cloud observability stacks.

## 8) Security and multi-tenant controls are not yet surfaced
- Environment key checks exist, but there is no authn/authz service boundary, tenant separation model, or secrets manager integration codified in application logic.

## 9) Data export/reporting interfaces are missing
- The system writes strategy outputs to DB, but does not yet expose a functional output API/report endpoint for downstream consumers.

## 10) CI/CD and release automation are absent
- Repository lacks CI pipeline definitions for test/deploy gates and automated cloud rollout.
