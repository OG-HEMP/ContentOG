import requests
import sys
import os
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from config.config import settings
from database.db_client import db_client

def test_retry():
    # 1. Find or create a failed task
    tasks = db_client.query("SELECT id, retry_count FROM keyword_tasks WHERE status = 'failed' LIMIT 1")
    if not tasks:
        print("No failed tasks found. Creating a dummy one...")
        # Create a dummy run if needed
        runs = db_client.query("SELECT id FROM runs LIMIT 1")
        if not runs:
            print("No runs found either. Please run the pipeline first.")
            return
        run_id = runs[0]['id']
        task_id = "test-retry-uuid"
        db_client._execute(
            "INSERT INTO keyword_tasks (id, run_id, keyword, status, retry_count) VALUES (%s, %s, %s, %s, %s) ON CONFLICT (id) DO UPDATE SET status = 'failed'",
            (task_id, run_id, "test_retry_kw", "failed", 0)
        )
        task_id = "test-retry-uuid"
        initial_retry_count = 0
    else:
        task_id = tasks[0]['id']
        initial_retry_count = tasks[0]['retry_count'] or 0

    print(f"Testing retry for task {task_id} (Initial retry_count: {initial_retry_count})")

    # 2. Trigger retry via API (Localhost if running, or use direct logic if not)
    # Since I don't know if the API is running locally or deployed, I'll test the DB increment logic directly 
    # and maybe try a curl if I can find the URL.
    
    # Actually, I can just call the endpoint if it's running. 
    # Let's assume the API might not be running in the background for this test, 
    # but I'll check if I can hit health.
    
    api_url = "http://localhost:8000" # Default
    try:
        resp = requests.get(f"{api_url}/health", timeout=2)
        if resp.status_code == 200:
            print(f"API is running at {api_url}. Sending POST request...")
            retry_resp = requests.post(f"{api_url}/tasks/{task_id}/retry")
            print(f"API Response: {retry_resp.json()}")
        else:
            print("API health check failed. Testing DB logic directly.")
            db_client.increment_task_retry_count(task_id)
    except Exception as e:
        print(f"Could not connect to API: {e}. Testing DB logic directly.")
        db_client.increment_task_retry_count(task_id)

    # 3. Verify increment
    updated_tasks = db_client.query("SELECT retry_count FROM keyword_tasks WHERE id = %s", (task_id,))
    new_retry_count = updated_tasks[0]['retry_count']
    
    if new_retry_count == initial_retry_count + 1:
        print(f"SUCCESS: retry_count incremented to {new_retry_count}")
    else:
        print(f"FAILURE: retry_count is {new_retry_count}, expected {initial_retry_count + 1}")

if __name__ == "__main__":
    test_retry()
