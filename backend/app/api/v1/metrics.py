"""
SentinelIQ Metrics & Evaluation API Router
"""
import os
import json
from fastapi import APIRouter
from backend.app.database.repository import repo
from backend.app.config import settings

router = APIRouter(prefix="/metrics", tags=["Metrics & Observability"])


@router.get("/overview")
def get_overview():
    """Retrieve database-backed operational metrics."""
    return repo.get_overview_metrics()


@router.get("/alerts")
def get_alert_metrics():
    """Distribution of alerts across severity bands and lifecycle statuses."""
    overview = repo.get_overview_metrics()
    return {
        "total_alerts": overview["total_alerts"],
        "critical_alerts": overview["critical_alerts"],
        "by_severity": overview["alerts_by_severity"],
        "by_status": overview["alerts_by_status"]
    }


@router.get("/cases")
def get_case_metrics():
    """Status distribution and workload metrics for investigation cases."""
    overview = repo.get_overview_metrics()
    return {
        "open_cases": overview["open_cases"],
        "by_status": overview["cases_by_status"]
    }


@router.get("/data-quality")
def get_data_quality_metrics():
    """Retrieve latest data quality & integrity validation summary."""
    val_file = os.path.join(settings.REPORTS_DIR, "validation_summary.json")
    if os.path.isfile(val_file):
        with open(val_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "status": "pending",
        "message": "Validation report not yet generated. Trigger validation run via API."
    }


@router.get("/evaluation/summary")
def get_evaluation_summary():
    """Retrieve detection quality performance metrics against isolated ground truth."""
    eval_file = os.path.join(settings.REPORTS_DIR, "evaluation_summary.json")
    if os.path.isfile(eval_file):
        with open(eval_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "status": "pending",
        "message": "Evaluation report not yet generated. Run generator or evaluation pipeline."
    }
