import json
import logging
import os
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

from google.cloud import pubsub_v1
from config.config import settings
from database.db_client import db_client

logger = logging.getLogger(__name__)

class Orchestrator:
    def __init__(self):
        self.project_id = settings.gcp_project_id
        self.topic_id = os.getenv("CONTENTOG_PUBSUB_TOPIC", "contentog-tasks")
        self.db = db_client
        logger.info("Orchestrator initialized for GCP Project: %s (Topic: %s)", self.project_id, self.topic_id)

    def __repr__(self) -> str:
        return f"<Orchestrator(project_id='{self.project_id}', topic='{self.topic_id}')>"

    def create_run(self, mode: str, keyword_count: int, target_domain: Optional[str] = None) -> str:
        """Create a new run record in the database."""
        run_id = str(uuid.uuid4())
        try:
            metadata = {"target_domain": target_domain} if target_domain else {}
            self.db._execute(
                """
                INSERT INTO runs (id, mode, keyword_count, status, started_at, target_domain, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (run_id, mode, keyword_count, "running", datetime.utcnow().isoformat(), target_domain, json.dumps(metadata))
            )
            logger.info("Created run %s for mode %s (Target Domain: %s)", run_id, mode, target_domain)
            return run_id
        except Exception as exc:
            logger.error("Failed to create run record: %s", exc)
            return run_id

    def publish_tasks(self, run_id: str, keywords: List[str]):
        """Publish keyword tasks to Pub/Sub and track them in the database."""
        if not self.project_id:
            logger.warning("GCP_PROJECT_ID not set. Skipping Pub/Sub publishing.")
            return

        publisher = pubsub_v1.PublisherClient()
        topic_path = publisher.topic_path(self.project_id, self.topic_id)
        
        for keyword in keywords:
            task_id = str(uuid.uuid4())
            data = {
                "run_id": run_id,
                "task_id": task_id,
                "keyword": keyword
            }
            
            # Publish to Pub/Sub
            try:
                future = publisher.publish(topic_path, json.dumps(data).encode("utf-8"))
                future.result() # Verify publish
                
                # Log to database
                self.db._execute(
                    """
                    INSERT INTO keyword_tasks (id, run_id, keyword, status)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (task_id, run_id, keyword, "pending")
                )
            except Exception as exc:
                logger.error("Failed to publish or log task for keyword %s: %s", keyword, exc)

    def update_task(self, task_id: str, status: str, message: Optional[str] = None):
        """Update a specific task's status and message."""
        try:
            self.db.update_task_status(task_id, status, message)
            logger.info("Updated task %s to %s (%s)", task_id, status, message or "no message")
        except Exception as exc:
            logger.error("Failed to update task %s: %s", task_id, exc)

    def delete_run(self, run_id: str):
        """Delete a run and all its associated data."""
        try:
            self.db.delete_run(run_id)
            logger.info("Deleted run %s and associated tasks", run_id)
        except Exception as exc:
            logger.error("Failed to delete run %s: %s", run_id, exc)

    def complete_run(self, run_id: str, status: str = "completed", error: Optional[str] = None):
        """Mark a run as completed."""
        try:
            self.db._execute(
                """
                UPDATE runs
                SET status = %s, completed_at = %s, error_summary = %s
                WHERE id = %s
                """,
                (status, datetime.utcnow().isoformat(), error, run_id)
            )
        except Exception as exc:
            logger.error("Failed to update run status: %s", exc)
