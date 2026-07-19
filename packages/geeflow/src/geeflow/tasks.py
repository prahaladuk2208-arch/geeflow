"""Earth Engine export-task inspection."""

from __future__ import annotations

import ee


def list_tasks(limit: int = 10) -> list[dict]:
    """Recent export tasks, newest first: id, description, state, error (if any)."""
    statuses = ee.data.getTaskList()[:limit]
    return [
        {
            "id": t.get("id"),
            "description": t.get("description"),
            "state": t.get("state"),
            "task_type": t.get("task_type"),
            "error_message": t.get("error_message"),
        }
        for t in statuses
    ]


def task_status(task_id: str) -> dict:
    """Status of one task by id."""
    statuses = ee.data.getTaskStatus(task_id)
    if not statuses:
        raise ValueError(f"no task with id {task_id!r}")
    t = statuses[0]
    return {
        "id": t.get("id"),
        "description": t.get("description"),
        "state": t.get("state"),
        "error_message": t.get("error_message"),
    }
