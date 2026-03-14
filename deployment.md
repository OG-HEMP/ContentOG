# ContentOG Deployment Rules

This document defines the rules for deploying changes to the ContentOG ecosystem.

## 1. Scope Definitions

### Scope: API / Backend
Includes changes to:
- `api/` (Endpoints and server logic)
- `agents/` (Orchestration logic)
- `skills/` (Service wrappers)
- `crawler/` (Web scraping logic)
- `clustering/` (Topic detection)
- `config/` (Settings and credentials)
- `database/` (Schema and migrations)
- `strategy/` (Content insight generation)
- `embeddings/` (Vector generation)
- `analysis/` (Data processing)

### Scope: UI / Frontend
Includes changes strictly within:
- `ui/` (Next.js components, styles, hooks, and pages)

### Scope: CORE
Includes changes to shared infrastructure or deployment configurations:
- `Dockerfile` (Main backend container)
- `ui/Dockerfile` (UI container)
- `cloudbuild.yaml` (Build pipeline)
- `scripts/cloud_deploy.sh` (Deployment script)
- `requirements.txt` / `package.json` (Dependencies)
- `.env.example` (Config structure)

---

## 2. Deployment Rules

### Rule 1: Selective Rollouts
To minimize downtime and save costs, follow these rollout patterns:
- **UI-Only Changes**: Deploy only the UI service using `--ui`.
- **API/Logic-Only Changes**: Deploy only the API service using `--api`.
- **Core/Shared Changes**: Deploy the full stack using `--all`.

### Rule 2: Validation Requirements
Before any production deployment:
1. **Sync Environments**: Ensure `.env` variables match the production environment.
2. **Connectivity Check**: Run `python scripts/bootstrap_project.py` to verify database status.
3. **Pipeline Dry-Run**: Run `python scripts/run_pipeline.py` with a small limit to ensure no logic regressions.
4. **Next.js Hydration & Build Safety**: Verify that any page using **dynamic Client Hooks** (e.g., `useSearchParams`, `usePathname`, `useRouter`) or **browser-only APIs**:
    - Includes `'use client'` Directive at the top.
    - Is wrapped in a `<Suspense>` boundary to allow static pre-rendering of the layout.
    - Does not access `window` or `document` during the initial server-side render.

### Rule 3: Post-Deployment Verification
- Check Cloud Run logs for startup errors.
- Verify the specific feature changed in the production URL.
- If API changed, ensure any active Worker jobs are running the new logic.

---

## 3. Workflow Examples

**Scenario: Updating a React Component**
```bash
./scripts/cloud_deploy.sh --ui
```

**Scenario: Fixing a bug in a Topic Clustering agent**
```bash
./scripts/cloud_deploy.sh --api
```

**Scenario: Adding a new Python dependency**
```bash
./scripts/cloud_deploy.sh --all
```
