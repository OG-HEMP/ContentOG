# PROJECT_RULES.md

## Purpose

This file defines the architectural rules and guardrails for the ContentOG
system. All automated agents, IDE tools, and contributors must follow these
rules when modifying or generating code.

The goal is to preserve system stability and prevent architecture drift.

---

# 1. Architecture Source of Truth

The system architecture is defined by the following files:

requirements.md skills.md agents.md workflow.md antigravity_bootstrap.md
repo_import.md repo_mapping.md

These files must be treated as the authoritative specifications for the system.

No code generation or refactoring may violate these specifications.

---

# 2. Directory Policy

All generated files must reside in approved directories.

Allowed directories:

config/ database/ agents/ skills/ workflows/ crawler/ embeddings/ clustering/
analysis/ strategy/ scripts/ visualization/ data/ repos/

Files must not be generated outside these directories except for the approved
root files.

---

# 3. Root Directory Restrictions

Only the following files are allowed in the project root:

requirements.md skills.md agents.md workflow.md antigravity_bootstrap.md
repo_import.md repo_mapping.md PROJECT_RULES.md deployment.md .env.example task.md

No additional code files may be created in the root directory.

---

# 4. Agent Structure

Agent modules must follow this directory structure:

agents/`<agent_name>`{=html}/`<agent_name>`{=html}.py

Each agent must implement a run() function.

Agents must only call functionality through skills.

Agents must never directly call external repositories.

---

# 5. Skill Structure

Skill modules must follow this directory structure:

skills/`<skill_name>`{=html}/`<skill_name>`{=html}.py

Skills act as wrappers around external repositories.

Skills expose clean functions used by agents.

Skills must not depend on agents.

---

# 6. Dependency Direction

Dependencies must follow this order:

agents → skills → repos

Forbidden dependency directions:

skills → agents repos → agents repos → workflows

This prevents circular dependencies.

---

# 7. Repository Integrity

External repositories are stored in:

repos/

Repositories include:

Firecrawl sentence-transformers HDBSCAN spaCy CrewAI NetworkX

Rules:

Repositories must remain unmodified. All interactions with repositories must
happen through skill wrapper modules.

---

# 8. Database Schema Policy

Database schema must be defined only in:

database/schema.sql

Tables defined in the schema include:

articles keywords paa_questions topics article_topics pillar_strategies
cluster_articles

Future schema updates must be added through:

database/migrations/

Direct schema changes elsewhere are not allowed.

---

# 9. Workflow Execution

Workflow orchestration must be implemented in:

scripts/run_pipeline.py

Execution order must follow:

SERP discovery PAA extraction crawl pages generate embeddings cluster articles
topic reasoning strategy generation

No alternative pipeline runners should be created.

---

# 10. Entry Points

The system must have only two entry scripts:

scripts/bootstrap_project.py scripts/run_pipeline.py

bootstrap_project.py initializes the database and environment.

run_pipeline.py executes the workflow.

---

# 11. Configuration

All operational configuration must live in:

config/settings.yaml

Examples include:

crawl limits SERP result count embedding model name schedule intervals

Configuration must not be hardcoded in agents or skills.

---

# 12. Idempotency Rules

Agents must prevent duplicate data creation.

Before inserting records, agents must check for existing entries.

Examples:

existing URL existing PAA question existing topic

Pipelines must be safe to rerun.

---

# 13. Repository Imports

Repositories must be imported using the instructions in:

repo_import.md

Mapping between system skills and repositories must follow:

repo_mapping.md

No additional repositories may be introduced without updating the mapping file.

---

# 14. Testing Requirements

Before committing structural changes:

1. Verify database connection using bootstrap_project.py.
2. Run a dry-run of run_pipeline.py.
3. Ensure all agents load without import errors.

---

# 15. Prohibited Actions

The following actions are not allowed:

introducing new architectural layers changing table names moving agent or skill
modules outside their directories modifying external repository code adding
random scripts in the project root

---

# 16. Modification Protocol

Any change to architecture must first update:

requirements.md skills.md agents.md workflow.md

Code must then be regenerated or updated accordingly.

---

# 17. Goal

These rules ensure:

• stable scaffolding • predictable agent orchestration • maintainable
architecture • compatibility with Antigravity workflows

All system changes must respect these constraints.
