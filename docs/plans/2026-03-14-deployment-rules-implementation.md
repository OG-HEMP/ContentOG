# Deployment Rules and Selective Rollout Implementation Plan

> **For Antigravity:** REQUIRED SUB-SKILL: Load executing-plans to implement this plan task-by-task.

**Goal:** Centralize deployment rules in `deployment.md` and update `scripts/cloud_deploy.sh` to support selective service deployments.

**Architecture:** Create a rule-based deployment guide and enhance the bash script with flags to build and deploy only the changed components.

**Tech Stack:** Bash, Google Cloud SDK, Google Cloud Build, Markdown.

---

### Task 1: Create Centralized Deployment Rules

**Files:**
- Create: `deployment.md`
- Modify: `PROJECT_RULES.md:42-45`

**Step 1: Write `deployment.md`**
Define the scopes and rules for deployment.

**Step 2: Update `PROJECT_RULES.md`**
Add `deployment.md` to the allowed root files list.

**Step 3: Commit rules**

---

### Task 2: Update Cloud Build for Selective Builds

**Files:**
- Modify: `cloudbuild.yaml`

**Step 1: Make steps conditional**
Wrap build and push steps in bash logic that checks substitutions like `_API` and `_UI`.

**Step 2: Commit changes**

---

### Task 3: Enhance `scripts/cloud_deploy.sh`

**Files:**
- Modify: `scripts/cloud_deploy.sh`

**Step 1: Add argument parsing**
Add support for `--api`, `--ui`, and `--all` flags.

**Step 2: Implement conditional rollout logic**
Update the script to pass correct substitutions to `gcloud builds submit` and only call `gcloud run deploy` for the targeted services.

**Step 3: Add safety checks**
Add confirmation prompt and environment verification.

**Step 4: Commit changes**

---

### Task 4: Verification

**Step 1: Verify script syntax**
Run `bash -n scripts/cloud_deploy.sh`.

**Step 2: Verify help output / argument check**
Add a `--help` flag if missing and test it.
