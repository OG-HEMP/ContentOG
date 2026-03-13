# Deployment Rules and Selective Rollout Design

**Date:** 2026-03-14
**Status:** Approved

## Purpose
To centralize deployment rules and optimize the Cloud Run deployment process by allowing selective updates (API-only, UI-only, or Full) to reduce build times and avoid unnecessary service restarts.

## Proposed Changes

### 1. `deployment.md` (Root)
Create a new file `deployment.md` in the project root to define:
- **Scope Definitions**:
    - `API`: Code in `api/`, `agents/`, `skills/`, `crawler/`, `clustering/`, `config/`, `database/`, `strategy/`, `embeddings/`, `analysis/`.
    - `UI`: Code strictly in `ui/`.
    - `CORE`: Root files like `Dockerfile`, `requirements.txt`, `cloudbuild.yaml`, `.env.example`.
- **Deployment Rules**:
    - Pure UI changes must only redeploy the UI service.
    - API/Logic changes must redeploy the API service and optionally trigger worker jobs.
    - CORE changes require a full rebuild and redeploy of both services.
- **Pre-deployment Checklist**:
    - Ensure `.env` is updated and synced.
    - Verify database connectivity (`scripts/bootstrap_project.py`).
    - Run dry-run pipeline (`scripts/run_pipeline.py`).

### 2. `scripts/cloud_deploy.sh` Enhancements
Update the existing script to support the following:
- **Argument Parsing**: Support `--api`, `--ui`, and `--all` (default).
- **Conditional Build**: Use the build configuration to target specific service images.
- **Cleanup Phase**: Maintain the `cleanup_resources` function for efficiency.
- **User Confirmation**: Display the selected deployment scope and wait for a 5-second confirmation or prompt.

### 3. `PROJECT_RULES.md` Integration
- Add `deployment.md` to Section 3 (Root Directory Restrictions).
- Reference `deployment.md` as the operational source of truth.

## Success Criteria
- Deployment of a UI change takes significantly less time.
- No accidental full-stack redeploys when only one component changed.
- Clear documentation for future maintenance.
